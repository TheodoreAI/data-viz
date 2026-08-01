import random
import re
from functools import lru_cache

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
    query = ART_MOVEMENTS_QUERY.format(min_count=MIN_MOVEMENT_PAINTINGS, limit=MAX_MOVEMENTS)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    movements = []
    for row in bindings:
        movement_id = row['movement']['value'].rsplit('/', 1)[-1]
        label = label_or_none(row.get('movementLabel', {}).get('value')) or movement_id
        movements.append({'id': movement_id, 'label': label})
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
    movement_clause = f'wd:{movement_id}' if movement_id and QID_PATTERN.match(movement_id) else '?movement'
    query = ART_POOL_QUERY.format(movement_clause=movement_clause, limit=ART_POOL_SIZE)
    response = requests.get(WIKIDATA_SPARQL_URL, headers=WIKIDATA_HEADERS, params={'query': query})
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    paintings = [p for p in (parse_painting_row(row) for row in bindings) if p]
    random.shuffle(paintings)
    return paintings


def fetch_art_feed_page(offset, limit=ART_FEED_PAGE_SIZE, movement=None):
    pool = fetch_art_pool(movement)
    return pool[offset:offset + limit]
