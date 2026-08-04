import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests

CDX_URL = 'https://web.archive.org/cdx/search/cdx'
AVAILABLE_URL = 'https://archive.org/wayback/available'
REQUEST_TIMEOUT = 12
HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}


def _parse_timestamp(ts):
    return datetime.strptime(ts, '%Y%m%d%H%M%S')


def _format_date(dt):
    """dt.strftime('%B %-d, %Y') without relying on the non-portable %-d
    directive, which isn't supported by Python's C runtime on Windows."""
    return f'{dt.strftime("%B")} {dt.day}, {dt.strftime("%Y")}'


def fetch_snapshots(url, max_per_year=1, max_years=40):
    """Returns a list of {timestamp, date, archiveUrl} dicts, roughly one
    representative snapshot per year, newest first. Raises requests.RequestException
    on total failure — callers should catch and degrade gracefully."""
    response = requests.get(
        CDX_URL,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        params={
            'url': url,
            'output': 'json',
            'filter': 'statuscode:200',
            'limit': 20000,
        },
    )
    response.raise_for_status()
    rows = response.json()
    if len(rows) <= 1:
        return []

    by_year = {}
    for row in rows[1:]:  # first row is the column header
        timestamp = row[1]
        year = timestamp[:4]
        # Keep the first (earliest) capture we see per year — good enough
        # granularity for a "how did this look over time" browser.
        if year not in by_year:
            by_year[year] = timestamp

    snapshots = []
    for year, timestamp in sorted(by_year.items(), reverse=True)[:max_years]:
        snapshots.append({
            'timestamp': timestamp,
            'date': _format_date(_parse_timestamp(timestamp)),
            'year': year,
            'archiveUrl': f'https://web.archive.org/web/{timestamp}/{url}',
        })
    return snapshots


POPULAR_PAGE_SIZE = 4
POPULAR_SAMPLE_PAGES = 6
POPULAR_LIMIT = 12


def _extract_domain(url):
    domain = url.split('://', 1)[-1]
    domain = domain.split('/', 1)[0]
    return domain


def _grouping_key(original_url):
    """Collapses scheme/port/trailing-slash variants of the same page
    (https://x.com/, http://x.com/, http://x.com:80/) into one group,
    so the homepage doesn't fragment into several duplicate top entries."""
    no_query = original_url.split('?', 1)[0]
    no_scheme = re.sub(r'^https?://', '', no_query)
    no_port = re.sub(r':80$|:80(?=/)', '', no_scheme)
    return no_port.rstrip('/').lower()


def fetch_popular_pages(url, limit=POPULAR_LIMIT):
    """A bare domain (or any URL with no exact-match history) rarely has an
    exact-match capture — the CDX index is keyed by exact URL, and most of
    what's archived under a domain is deep content pages, not the homepage.

    matchType=domain finds those, but the index is sorted alphabetically by
    URL, so a single slice is badly skewed (numeric usernames, tracking
    params, etc. sort first). Instead, sample several pages spread evenly
    across the whole paginated index, then rank what we find by how many
    times each distinct page was recaptured over the years — a page that
    keeps getting recrawled is much more likely to be real content than a
    one-off. Raises requests.RequestException on total failure."""
    domain = _extract_domain(url)

    count_response = requests.get(
        CDX_URL,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        params={
            'url': domain,
            'matchType': 'domain',
            'output': 'json',
            'showNumPages': 'true',
            'pageSize': POPULAR_PAGE_SIZE,
        },
    )
    count_response.raise_for_status()
    total_pages = int(count_response.json()[1][0])
    if total_pages <= 0:
        return []

    sample_count = min(POPULAR_SAMPLE_PAGES, total_pages)
    page_indices = sorted({round(i * (total_pages - 1) / max(1, sample_count - 1)) for i in range(sample_count)})

    def fetch_page(page):
        try:
            response = requests.get(
                CDX_URL,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                params={
                    'url': domain,
                    'matchType': 'domain',
                    'output': 'json',
                    'pageSize': POPULAR_PAGE_SIZE,
                    'page': page,
                    'filter': ['statuscode:200', 'mimetype:text/html'],
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []  # one bad sample page shouldn't sink the whole search

    with ThreadPoolExecutor(max_workers=len(page_indices)) as executor:
        results = executor.map(fetch_page, page_indices)

    captures = {}  # grouping key -> {count, latest_timestamp, original}
    for rows in results:
        for row in rows[1:] if rows else []:
            timestamp, original = row[1], row[2]
            key = _grouping_key(original)
            entry = captures.setdefault(key, {'count': 0, 'timestamp': timestamp, 'original': original})
            entry['count'] += 1
            if timestamp > entry['timestamp']:
                entry['timestamp'] = timestamp
                entry['original'] = original

    ranked = sorted(captures.items(), key=lambda item: item[1]['count'], reverse=True)[:limit]

    pages = []
    for key, info in ranked:
        pages.append({
            'url': key,
            'captureCount': info['count'],
            'timestamp': info['timestamp'],
            'date': _format_date(_parse_timestamp(info['timestamp'])),
            'archiveUrl': f'https://web.archive.org/web/{info["timestamp"]}/{info["original"]}',
        })
    return pages


def fetch_closest_snapshot(url, date_str=None):
    """date_str is YYYYMMDD or None for the closest snapshot to today."""
    params = {'url': url}
    if date_str:
        params['timestamp'] = date_str
    response = requests.get(AVAILABLE_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT, params=params)
    response.raise_for_status()
    data = response.json()
    snapshot = data.get('archived_snapshots', {}).get('closest')
    if not snapshot or not snapshot.get('available'):
        return None
    return {
        'timestamp': snapshot['timestamp'],
        'date': _format_date(_parse_timestamp(snapshot['timestamp'])),
        'archiveUrl': snapshot['url'],
    }
