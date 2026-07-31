import json
from pathlib import Path
from markupsafe import Markup

VITE_DEV_PORT = 8080
MANIFEST_PATH = Path(__file__).parent / 'static' / 'dist' / '.vite' / 'manifest.json'


def vite_asset_tags(entry_name, dev_mode, request_host=None):
    if dev_mode:
        hostname = (request_host or 'localhost').split(':')[0]
        dev_server = f'http://{hostname}:{VITE_DEV_PORT}'
        return Markup(
            f'<script type="module" src="{dev_server}/@vite/client"></script>\n'
            f'<script type="module" src="{dev_server}/src/entries/{entry_name}.js"></script>'
        )

    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = manifest[f'src/entries/{entry_name}.js']

    tags = [f'<script type="module" src="/static/dist/{entry["file"]}"></script>']
    for css_file in entry.get('css', []):
        tags.append(f'<link rel="stylesheet" href="/static/dist/{css_file}">')
    return Markup('\n'.join(tags))