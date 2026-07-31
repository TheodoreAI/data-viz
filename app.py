import random
import re
from datetime import date, timedelta
from urllib.parse import quote

import requests
from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request

from vite import vite_asset_tags

WIKIPEDIA_RANDOM_SUMMARY_URL = 'https://en.wikipedia.org/api/rest_v1/page/random/summary'
WIKIPEDIA_SUMMARY_URL = 'https://en.wikipedia.org/api/rest_v1/page/summary/{title}'
WIKIPEDIA_ACTION_API_URL = 'https://en.wikipedia.org/w/api.php'
WIKIPEDIA_TOP_VIEWED_URL = (
    'https://wikimedia.org/api/rest_v1/metrics/pageviews/top/'
    'en.wikipedia/all-access/{year}/{month}/{day}'
)
WIKIPEDIA_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
EXCLUDED_TITLES = {'Main_Page', 'Special:Search'}
BUBBLE_COUNT = 12

WIKIDATA_SPARQL_URL = 'https://query.wikidata.org/sparql'
ART_FEED_PAGE_SIZE = 20
ART_FEED_QUERY = """
SELECT ?painting ?paintingLabel ?artistLabel ?movementLabel
       (SAMPLE(?birth) AS ?birthAgg)
       (SAMPLE(?death) AS ?deathAgg)
       (SAMPLE(?inception) AS ?inceptionAgg)
       (SAMPLE(?image) AS ?imageAgg) WHERE {{
  ?painting wdt:P31 wd:Q3305213;
            wdt:P170 ?artist;
            wdt:P18 ?image;
            wdt:P135 ?movement;
            wdt:P571 ?inception.
  OPTIONAL {{ ?artist wdt:P569 ?birth. }}
  OPTIONAL {{ ?artist wdt:P570 ?death. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?painting ?paintingLabel ?artistLabel ?movementLabel
ORDER BY ?inceptionAgg
LIMIT {limit} OFFSET {offset}
"""

TOPIC_CATEGORIES = {
    'art': 'Category:Art',
    'physics': 'Category:Physics',
    'computer-science': 'Category:Computer science',
    'history': 'Category:History',
}
_topic_category_pool_cache = {}

app = Flask(__name__)
app.jinja_env.globals['vite_asset'] = lambda entry: vite_asset_tags(entry, app.debug, request.host)


def fetch_category_members(category, member_type):
    response = requests.get(WIKIPEDIA_ACTION_API_URL, headers=WIKIPEDIA_HEADERS, params={
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': category,
        'cmtype': member_type,
        'cmnamespace': 0 if member_type == 'page' else None,
        'cmlimit': 500,
        'format': 'json',
    })
    response.raise_for_status()
    return response.json()['query']['categorymembers']


def get_topic_category_pool(topic):
    root_category = TOPIC_CATEGORIES[topic]
    if topic not in _topic_category_pool_cache:
        subcats = fetch_category_members(root_category, 'subcat')
        _topic_category_pool_cache[topic] = [root_category] + [c['title'] for c in subcats]
    return _topic_category_pool_cache[topic]


def fetch_random_article(topic=None):
    if topic not in TOPIC_CATEGORIES:
        response = requests.get(WIKIPEDIA_RANDOM_SUMMARY_URL, headers=WIKIPEDIA_HEADERS)
        response.raise_for_status()
        return response.json()

    pool = list(get_topic_category_pool(topic))
    random.shuffle(pool)
    for category in pool:
        members = fetch_category_members(category, 'page')
        if members:
            title = random.choice(members)['title']
            summary_response = requests.get(
                WIKIPEDIA_SUMMARY_URL.format(title=quote(title.replace(' ', '_'))),
                headers=WIKIPEDIA_HEADERS,
            )
            if summary_response.ok:
                return summary_response.json()

    # No category in the pool yielded an article; fall back to unrestricted random.
    response = requests.get(WIKIPEDIA_RANDOM_SUMMARY_URL, headers=WIKIPEDIA_HEADERS)
    response.raise_for_status()
    return response.json()


YEAR_PATTERN = re.compile(r'^(-?\d+)-\d{2}-\d{2}')


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


QID_PATTERN = re.compile(r'^Q\d+$')


def label_or_none(value):
    if not value or value.startswith('http://www.wikidata.org/') or QID_PATTERN.match(value):
        return None
    return value


def fetch_art_feed_page(offset, limit=ART_FEED_PAGE_SIZE):
    query = ART_FEED_QUERY.format(limit=limit, offset=offset)
    response = requests.get(
        WIKIDATA_SPARQL_URL,
        headers={**WIKIPEDIA_HEADERS, 'Accept': 'application/sparql-results+json'},
        params={'query': query},
    )
    response.raise_for_status()
    bindings = response.json()['results']['bindings']

    paintings = []
    for row in bindings:
        image = row.get('imageAgg', {}).get('value')
        if not image:
            continue
        paintings.append({
            'title': label_or_none(row.get('paintingLabel', {}).get('value')) or 'Untitled',
            'artist': label_or_none(row.get('artistLabel', {}).get('value')) or 'Unknown artist',
            'birthYear': extract_year(row.get('birthAgg', {}).get('value')),
            'deathYear': extract_year(row.get('deathAgg', {}).get('value')),
            'movement': label_or_none(row.get('movementLabel', {}).get('value')) or 'Unknown movement',
            'year': extract_year(row.get('inceptionAgg', {}).get('value')),
            'image': commons_thumbnail_url(image),
        })
    return paintings


@app.route('/')
def hello_world():
    article = fetch_random_article()
    return render_template('home.html', article=article, topics=TOPIC_CATEGORIES)


@app.route('/api/random-article')
def api_random_article():
    topic = request.args.get('topic') or None
    return jsonify(fetch_random_article(topic))


@app.route('/art')
def art():
    paintings = fetch_art_feed_page(offset=0)
    return render_template('art.html', paintings=paintings)


@app.route('/api/art-feed')
def api_art_feed():
    offset = request.args.get('offset', 0, type=int)
    return jsonify(fetch_art_feed_page(offset=offset))


@app.route('/bubbles')
def bubbles():
    yesterday = date.today() - timedelta(days=1)
    top_url = WIKIPEDIA_TOP_VIEWED_URL.format(
        year=yesterday.year, month=f'{yesterday.month:02d}', day=f'{yesterday.day:02d}'
    )
    response = requests.get(top_url, headers=WIKIPEDIA_HEADERS)
    response.raise_for_status()
    top_articles = response.json()['items'][0]['articles']

    articles = []
    for entry in top_articles:
        title = entry['article']
        if title in EXCLUDED_TITLES or title.startswith('Special:'):
            continue
        summary_response = requests.get(
            WIKIPEDIA_SUMMARY_URL.format(title=title), headers=WIKIPEDIA_HEADERS
        )
        if not summary_response.ok:
            continue
        summary = summary_response.json()
        articles.append({
            'title': summary.get('title', title.replace('_', ' ')),
            'views': entry['views'],
            'extract_length': len(summary.get('extract', '')),
            'url': summary.get('content_urls', {}).get('desktop', {}).get('page', '#'),
        })
        if len(articles) == BUBBLE_COUNT:
            break

    return render_template('bubbles.html', articles=articles, date=yesterday.isoformat())


if __name__ == '__main__':
    app.run(debug=True, port=8081, host='0.0.0.0')