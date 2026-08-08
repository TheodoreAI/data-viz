import time
from datetime import datetime
from html import unescape

import requests

HN_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
REDDIT_HEADERS = {'User-Agent': 'data-viz-app/1.0 (by /u/mateoej12)'}
STACKOVERFLOW_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
DEVTO_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
LOBSTERS_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}

HN_ALGOLIA_URL = 'https://hn.algolia.com/api/v1/search'
REDDIT_URL = 'https://www.reddit.com/r/all/top.json'
STACKOVERFLOW_URL = 'https://api.stackexchange.com/2.3/questions'
DEVTO_URL = 'https://dev.to/api/articles'
LOBSTERS_URL = 'https://lobste.rs/hottest.json'

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


def fetch_devto():
    """Top current articles from Dev.to, ranked by reactions."""
    response = requests.get(DEVTO_URL, headers=DEVTO_HEADERS, params={
        'top': 1,
        'per_page': ITEM_COUNT,
    })
    response.raise_for_status()
    articles = response.json()

    now = time.time()
    items = []
    for article in articles[:ITEM_COUNT]:
        published = datetime.fromisoformat(article['published_timestamp'].replace('Z', '+00:00'))
        items.append({
            'title': article['title'],
            'score': article.get('positive_reactions_count') or 0,
            'comments': article.get('comments_count') or 0,
            'age_hours': round((now - published.timestamp()) / 3600, 1),
            'url': article['url'],
        })
    return items


def fetch_lobsters():
    """Current front-page stories from Lobsters, ranked by score."""
    response = requests.get(LOBSTERS_URL, headers=LOBSTERS_HEADERS)
    response.raise_for_status()
    stories = response.json()

    now = time.time()
    items = []
    for story in stories[:ITEM_COUNT]:
        created = datetime.fromisoformat(story['created_at'])
        items.append({
            'title': story['title'],
            'score': story.get('score') or 0,
            'comments': story.get('comment_count') or 0,
            'age_hours': round((now - created.timestamp()) / 3600, 1),
            'url': story.get('url') or story['comments_url'],
        })
    return items


# These are free third-party APIs with their own rate limits (Reddit
# already 403s intermittently) — an in-process TTL cache means a burst of
# page loads doesn't fan out to five upstream requests per visitor.
CACHE_TTL_SECONDS = 5 * 60
_cache = {}


def _cached(source, fetch):
    def wrapped():
        cached = _cache.get(source)
        if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        items = fetch()
        _cache[source] = (time.time(), items)
        return items
    return wrapped


SOURCES = {
    source: _cached(source, fetch)
    for source, fetch in {
        'hackernews': fetch_hacker_news,
        'reddit': fetch_reddit,
        'stackoverflow': fetch_stackoverflow,
        'devto': fetch_devto,
        'lobsters': fetch_lobsters,
    }.items()
}
