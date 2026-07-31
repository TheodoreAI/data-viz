from datetime import date, timedelta

import requests
from flask import Flask
from flask import render_template

from vite import vite_asset_tags

WIKIPEDIA_RANDOM_SUMMARY_URL = 'https://en.wikipedia.org/api/rest_v1/page/random/summary'
WIKIPEDIA_SUMMARY_URL = 'https://en.wikipedia.org/api/rest_v1/page/summary/{title}'
WIKIPEDIA_TOP_VIEWED_URL = (
    'https://wikimedia.org/api/rest_v1/metrics/pageviews/top/'
    'en.wikipedia/all-access/{year}/{month}/{day}'
)
WIKIPEDIA_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
EXCLUDED_TITLES = {'Main_Page', 'Special:Search'}
BUBBLE_COUNT = 12

app = Flask(__name__)
app.jinja_env.globals['vite_asset'] = lambda entry: vite_asset_tags(entry, app.debug)

@app.route('/')
def hello_world():
    response = requests.get(WIKIPEDIA_RANDOM_SUMMARY_URL, headers=WIKIPEDIA_HEADERS)
    response.raise_for_status()
    article = response.json()
    return render_template('home.html', person='Luna', article=article)


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
    app.run(debug=True, port=8081)