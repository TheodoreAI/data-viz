import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import requests

WIKIDATA_SPARQL_URL = 'https://query.wikidata.org/sparql'
WIKIDATA_HEADERS = {
    'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)',
    'Accept': 'application/sparql-results+json',
}

FILM_FEED_PAGE_SIZE = 20
FILM_POOL_SIZE = 100
MIN_GENRE_FILMS = 15
MAX_GENRES = 20

# These SPARQL queries take several seconds to ~10s each. lru_cache alone only
# helps within a single running process, so every restart/redeploy/new worker
# pays that cost again. This on-disk cache survives across all of those —
# only the very first request after the TTL expires is ever slow.
CACHE_DIR = Path(__file__).parent / '.wikidata_cache'
CACHE_TTL_SECONDS = 24 * 60 * 60


def _cache_path(key):
    return CACHE_DIR / f'{key}.json'


def _read_disk_cache(key):
    path = _cache_path(key)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > CACHE_TTL_SECONDS:
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_disk_cache(key, data):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        _cache_path(key).write_text(json.dumps(data))
    except OSError:
        pass

ART_MOVEMENTS_QUERY = """
SELECT ?movement ?movementLabel (COUNT(DISTINCT ?painting) AS ?count) WHERE {{
  ?painting wdt:P31 wd:Q3305213;
            wdt:P170 ?artist;
            wdt:P18 ?image;
            wdt:P135 ?movement;
            wdt:P571 ?inception.
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?movement ?movementLabel
HAVING (COUNT(DISTINCT ?painting) >= {min_count})
ORDER BY DESC(?count)
LIMIT {limit}
"""

FILM_GENRES_QUERY = """
SELECT ?genre ?genreLabel (COUNT(DISTINCT ?film) AS ?count) WHERE {{
  ?film wdt:P31 wd:Q11424;
        wdt:P136 ?genre;
        wdt:P18 ?image;
        wdt:P577 ?publicationDate.
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?genre ?genreLabel
HAVING (COUNT(DISTINCT ?film) >= {min_count})
ORDER BY DESC(?count)
LIMIT {limit}
"""

FILM_POOL_QUERY = """
SELECT ?film ?filmLabel ?directorLabel ?genre ?genreLabel
       (SAMPLE(?birth) AS ?birthAgg)
       (SAMPLE(?death) AS ?deathAgg)
       (SAMPLE(?publicationDate) AS ?publicationDateAgg)
       (SAMPLE(?image) AS ?imageAgg) WHERE {{
  ?film wdt:P31 wd:Q11424;
        wdt:P57 ?director;
        wdt:P136 {genre_clause};
        wdt:P18 ?image;
        wdt:P577 ?publicationDate.
  OPTIONAL {{ ?director wdt:P569 ?birth. }}
  OPTIONAL {{ ?director wdt:P570 ?death. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?film ?filmLabel ?directorLabel ?genre ?genreLabel
LIMIT {limit}
"""

YEAR_PATTERN = re.compile(r'^(-?\d+)-\d{2}-\d{2}')
QID_PATTERN = re.compile(r'^Q\d+$')


def extract_year(iso_date):
    if not iso_date:
        return None
    match = YEAR_PATTERN.match(iso_date)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def commons_thumbnail_url(file_path_url):
    return file_path_url.replace('http://', 'https://') + '?width=600'


# Special:FilePath is a convenience redirect (two hops: Special:FilePath ->
# Special:Redirect/file -> the actual upload.wikimedia.org CDN URL) that
# Wikidata's P18 values point at. Resolving it costs a couple hundred ms per
# image, so doing that resolution here — once per film, when the disk cache
# is (re)built — means every real page load links straight to the CDN and
# skips both redirects, instead of every visitor's browser paying that cost
# for every poster on every visit.
def _resolve_thumbnail_url(thumbnail_url):
    try:
        response = requests.head(
            thumbnail_url, headers=WIKIDATA_HEADERS, allow_redirects=True, timeout=10,
        )
        return response.url
    except requests.RequestException:
        return thumbnail_url


def _resolve_thumbnail_urls(films):
    with ThreadPoolExecutor(max_workers=16) as executor:
        resolved = list(executor.map(lambda f: _resolve_thumbnail_url(f['image']), films))
    for film, url in zip(films, resolved):
        film['image'] = url
    return films


def label_or_none(value):
    if not value or value.startswith('http://www.wikidata.org/') or QID_PATTERN.match(value):
        return None
    return value


@lru_cache(maxsize=1)
def fetch_film_genres():
    cached = _read_disk_cache('film_genres')
    if cached is not None:
        return cached

    query = FILM_GENRES_QUERY.format(min_count=MIN_GENRE_FILMS, limit=MAX_GENRES)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    genres = []
    for row in bindings:
        genre_id = row['genre']['value'].rsplit('/', 1)[-1]
        label = label_or_none(row.get('genreLabel', {}).get('value')) or genre_id
        genres.append({'id': genre_id, 'label': label})

    _write_disk_cache('film_genres', genres)
    return genres


def parse_film_row(row):
    image = row.get('imageAgg', {}).get('value')
    if not image:
        return None
    return {
        'title': label_or_none(row.get('filmLabel', {}).get('value')) or 'Untitled',
        'director': label_or_none(row.get('directorLabel', {}).get('value')) or 'Unknown director',
        'birthYear': extract_year(row.get('birthAgg', {}).get('value')),
        'deathYear': extract_year(row.get('deathAgg', {}).get('value')),
        'genre': label_or_none(row.get('genreLabel', {}).get('value')) or 'Unknown genre',
        'year': extract_year(row.get('publicationDateAgg', {}).get('value')),
        'image': commons_thumbnail_url(image),
    }


@lru_cache(maxsize=64)
def fetch_film_pool(genre_id=None):
    cache_key = f'film_pool_{genre_id or "all"}'
    cached = _read_disk_cache(cache_key)
    if cached is not None:
        return cached

    genre_clause = f'wd:{genre_id}' if genre_id and QID_PATTERN.match(genre_id) else '?genre'
    query = FILM_POOL_QUERY.format(genre_clause=genre_clause, limit=FILM_POOL_SIZE)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    films = [p for p in (parse_film_row(row) for row in bindings) if p]
    random.shuffle(films)
    films = _resolve_thumbnail_urls(films)

    _write_disk_cache(cache_key, films)
    return films


def fetch_film_feed_page(offset, limit=FILM_FEED_PAGE_SIZE, genre=None):
    pool = fetch_film_pool(genre)
    return pool[offset:offset + limit]
