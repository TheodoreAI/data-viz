import os
import time
from datetime import datetime, timedelta
from html import unescape

import requests

HN_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
STACKOVERFLOW_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
DEVTO_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
LOBSTERS_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}
CARGO_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}

HN_ALGOLIA_URL = 'https://hn.algolia.com/api/v1/search'
STACKOVERFLOW_URL = 'https://api.stackexchange.com/2.3/questions'
DEVTO_URL = 'https://dev.to/api/articles'
LOBSTERS_URL = 'https://lobste.rs/hottest.json'
YOUTUBE_URL = 'https://www.googleapis.com/youtube/v3/videos'
NPM_DOWNLOADS_URL_POINT = 'https://api.npmjs.org/downloads/point/{range}/{package}'
NPM_REGISTRY_URL = 'https://registry.npmjs.org/{package}'
CARGO_URL = 'https://crates.io/api/v1/crates'

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

ITEM_COUNT = 12

# npm has no "trending" endpoint, so we track weekly download counts for a
# curated set of widely-used packages and rank them by that count.
NPM_PACKAGES = [
    'react', 'vue', 'svelte', 'next', 'vite', 'webpack', 'typescript',
    'eslint', 'tailwindcss', 'express', 'axios', 'lodash', 'zod', 'prisma',
    'jest', 'vitest', 'playwright', 'redux', 'graphql', 'electron',
]


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


def fetch_npm():
    """Weekly npm download counts for a curated set of popular packages, ranked by growth vs. the prior week."""
    today = datetime.utcnow().date()
    # npm download-range endpoints only accept full past weeks (Sun-Sat).
    last_week_end = today - timedelta(days=today.weekday() + 2)
    last_week_start = last_week_end - timedelta(days=6)
    prev_week_end = last_week_start - timedelta(days=1)
    prev_week_start = prev_week_end - timedelta(days=6)

    items = []
    for package in NPM_PACKAGES:
        downloads_resp = requests.get(
            NPM_DOWNLOADS_URL_POINT.format(
                range=f'{last_week_start.isoformat()}:{last_week_end.isoformat()}', package=package
            )
        )
        if not downloads_resp.ok:
            continue
        last_week = downloads_resp.json().get('downloads') or 0

        prev_resp = requests.get(
            NPM_DOWNLOADS_URL_POINT.format(
                range=f'{prev_week_start.isoformat()}:{prev_week_end.isoformat()}', package=package
            )
        )
        prev_week = prev_resp.json().get('downloads') if prev_resp.ok else None

        growth_pct = round((last_week - prev_week) / prev_week * 100, 1) if prev_week else 0

        registry_resp = requests.get(NPM_REGISTRY_URL.format(package=package) + '/latest')
        registry = registry_resp.json() if registry_resp.ok else {}

        items.append({
            'title': package,
            'description': registry.get('description') or '',
            'version': registry.get('version') or '',
            'downloads': last_week,
            'growth_pct': growth_pct,
            'url': f'https://www.npmjs.com/package/{package}',
        })

    items.sort(key=lambda i: i['downloads'], reverse=True)
    return items[:ITEM_COUNT]


def fetch_cargo():
    """Top Rust crates ranked by recent (90-day) download count, from the crates.io registry."""
    response = requests.get(CARGO_URL, headers=CARGO_HEADERS, params={
        'sort': 'recent-downloads',
        'per_page': ITEM_COUNT,
    })
    response.raise_for_status()
    crates = response.json()['crates']

    items = []
    for crate in crates[:ITEM_COUNT]:
        items.append({
            'title': crate['name'],
            'description': crate.get('description') or '',
            'version': crate.get('max_stable_version') or crate.get('newest_version') or '',
            'downloads': crate.get('recent_downloads') or 0,
            'total_downloads': crate.get('downloads') or 0,
            'url': f'https://crates.io/crates/{crate["name"]}',
        })
    return items


def fetch_youtube():
    """Current trending videos (US), from the YouTube Data API."""
    response = requests.get(YOUTUBE_URL, params={
        'chart': 'mostPopular',
        'regionCode': 'US',
        'maxResults': ITEM_COUNT,
        'part': 'snippet,statistics',
        'key': YOUTUBE_API_KEY,
    })
    response.raise_for_status()
    videos = response.json()['items']

    now = time.time()
    items = []
    for video in videos[:ITEM_COUNT]:
        snippet = video['snippet']
        stats = video.get('statistics', {})
        published = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
        items.append({
            'title': snippet['title'],
            'score': int(stats.get('viewCount') or 0),
            'comments': int(stats.get('commentCount') or 0),
            'age_hours': round((now - published.timestamp()) / 3600, 1),
            'url': f'https://www.youtube.com/watch?v={video["id"]}',
        })
    return items


# These are free third-party APIs with their own rate limits — an
# in-process TTL cache means a burst of page loads doesn't fan out to
# five upstream requests per visitor.
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
        'youtube': fetch_youtube,
        'stackoverflow': fetch_stackoverflow,
        'devto': fetch_devto,
        'lobsters': fetch_lobsters,
        'npm': fetch_npm,
        'cargo': fetch_cargo,
    }.items()
}
