from datetime import datetime

import requests

CDX_URL = 'https://web.archive.org/cdx/search/cdx'
AVAILABLE_URL = 'https://archive.org/wayback/available'
REQUEST_TIMEOUT = 12
HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}


def _parse_timestamp(ts):
    return datetime.strptime(ts, '%Y%m%d%H%M%S')


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
            'date': _parse_timestamp(timestamp).strftime('%B %-d, %Y'),
            'year': year,
            'archiveUrl': f'https://web.archive.org/web/{timestamp}/{url}',
        })
    return snapshots


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
        'date': _parse_timestamp(snapshot['timestamp']).strftime('%B %-d, %Y'),
        'archiveUrl': snapshot['url'],
    }
