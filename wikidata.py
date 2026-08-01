import json
import random
import re
import time
from functools import lru_cache
from pathlib import Path

import requests

WIKIDATA_SPARQL_URL = 'https://query.wikidata.org/sparql'
WIKIDATA_HEADERS = {
    'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)',
    'Accept': 'application/sparql-results+json',
}

ART_FEED_PAGE_SIZE = 20
ART_POOL_SIZE = 400
MIN_MOVEMENT_PAINTINGS = 15
MAX_MOVEMENTS = 20

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

ART_POOL_QUERY = """
SELECT ?painting ?paintingLabel ?artistLabel ?movementLabel
       (SAMPLE(?birth) AS ?birthAgg)
       (SAMPLE(?death) AS ?deathAgg)
       (SAMPLE(?inception) AS ?inceptionAgg)
       (SAMPLE(?image) AS ?imageAgg) WHERE {{
  ?painting wdt:P31 wd:Q3305213;
            wdt:P170 ?artist;
            wdt:P18 ?image;
            wdt:P135 {movement_clause};
            wdt:P571 ?inception.
  OPTIONAL {{ ?artist wdt:P569 ?birth. }}
  OPTIONAL {{ ?artist wdt:P570 ?death. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?painting ?paintingLabel ?artistLabel ?movementLabel
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


def label_or_none(value):
    if not value or value.startswith('http://www.wikidata.org/') or QID_PATTERN.match(value):
        return None
    return value


@lru_cache(maxsize=1)
def fetch_art_movements():
    cached = _read_disk_cache('art_movements')
    if cached is not None:
        return cached

    query = ART_MOVEMENTS_QUERY.format(min_count=MIN_MOVEMENT_PAINTINGS, limit=MAX_MOVEMENTS)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    movements = []
    for row in bindings:
        movement_id = row['movement']['value'].rsplit('/', 1)[-1]
        label = label_or_none(row.get('movementLabel', {}).get('value')) or movement_id
        movements.append({'id': movement_id, 'label': label})

    _write_disk_cache('art_movements', movements)
    return movements


def parse_painting_row(row):
    image = row.get('imageAgg', {}).get('value')
    if not image:
        return None
    return {
        'title': label_or_none(row.get('paintingLabel', {}).get('value')) or 'Untitled',
        'artist': label_or_none(row.get('artistLabel', {}).get('value')) or 'Unknown artist',
        'birthYear': extract_year(row.get('birthAgg', {}).get('value')),
        'deathYear': extract_year(row.get('deathAgg', {}).get('value')),
        'movement': label_or_none(row.get('movementLabel', {}).get('value')) or 'Unknown movement',
        'year': extract_year(row.get('inceptionAgg', {}).get('value')),
        'image': commons_thumbnail_url(image),
    }


@lru_cache(maxsize=64)
def fetch_art_pool(movement_id=None):
    cache_key = f'art_pool_{movement_id or "all"}'
    cached = _read_disk_cache(cache_key)
    if cached is not None:
        return cached

    movement_clause = f'wd:{movement_id}' if movement_id and QID_PATTERN.match(movement_id) else '?movement'
    query = ART_POOL_QUERY.format(movement_clause=movement_clause, limit=ART_POOL_SIZE)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    paintings = [p for p in (parse_painting_row(row) for row in bindings) if p]
    random.shuffle(paintings)

    _write_disk_cache(cache_key, paintings)
    return paintings


def fetch_art_feed_page(offset, limit=ART_FEED_PAGE_SIZE, movement=None):
    pool = fetch_art_pool(movement)
    return pool[offset:offset + limit]
