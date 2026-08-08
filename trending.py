import time
from html import unescape

import requests

HN_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
REDDIT_HEADERS = {'User-Agent': 'data-viz-app/1.0 (by /u/mateoej12)'}
STACKOVERFLOW_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}

HN_ALGOLIA_URL = 'https://hn.algolia.com/api/v1/search'
REDDIT_URL = 'https://www.reddit.com/r/all/top.json'
STACKOVERFLOW_URL = 'https://api.stackexchange.com/2.3/questions'

ITEM_COUNT = 12


def fetch_hacker_news():
    """Top current Hacker News stories, ranked by points, from Algolia's HN search API."""
    response = requests.get(HN_ALGOLIA_URL, headers=HN_HEADERS, params={
        'tags': 'story',
        'numericFilters': 'created_at_i>' + str(int(time.time()) - 60 * 60 * 24),
    })
    response.raise_for_status()
    hits = response.json()['hits']
    hits.sort(key=lambda h: h.get('points') or 0, reverse=True)

    now = time.time()
    items = []
    for hit in hits[:ITEM_COUNT]:
        title = hit.get('title')
        if not title:
            continue
        items.append({
            'title': title,
            'score': hit.get('points') or 0,
            'comments': hit.get('num_comments') or 0,
            'age_hours': round((now - hit['created_at_i']) / 3600, 1),
            'url': hit.get('url') or f'https://news.ycombinator.com/item?id={hit["objectID"]}',
        })
    return items


def fetch_reddit():
    """Top current posts across r/all, from Reddit's public JSON listing (no auth required)."""
    response = requests.get(REDDIT_URL, headers=REDDIT_HEADERS, params={
        't': 'day',
        'limit': ITEM_COUNT,
    })
    response.raise_for_status()
    children = response.json()['data']['children']

    now = time.time()
    items = []
    for child in children[:ITEM_COUNT]:
        post = child['data']
        items.append({
            'title': post['title'],
            'score': post.get('score') or 0,
            'comments': post.get('num_comments') or 0,
            'age_hours': round((now - post['created_utc']) / 3600, 1),
            'url': f'https://reddit.com{post["permalink"]}',
        })
    return items


def fetch_stackoverflow():
    """Top questions from the last day on Stack Overflow, ranked by score."""
    response = requests.get(STACKOVERFLOW_URL, headers=STACKOVERFLOW_HEADERS, params={
        'order': 'desc',
        'sort': 'votes',
        'site': 'stackoverflow',
        'fromdate': int(time.time()) - 60 * 60 * 24 * 3,
        'pagesize': ITEM_COUNT,
    })
    response.raise_for_status()
    questions = response.json()['items']

    now = time.time()
    items = []
    for q in questions[:ITEM_COUNT]:
        items.append({
            'title': unescape(q['title']),
            'score': q.get('score') or 0,
            'comments': q.get('answer_count') or 0,
            'age_hours': round((now - q['creation_date']) / 3600, 1),
            'url': q['link'],
        })
    return items


SOURCES = {
    'hackernews': fetch_hacker_news,
    'reddit': fetch_reddit,
    'stackoverflow': fetch_stackoverflow,
}
