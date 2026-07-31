import json
from pathlib import Path
from markupsafe import Markup

VITE_DEV_SERVER = 'http://localhost:8080'
MANIFEST_PATH = Path(__file__).parent / 'static' / 'dist' / '.vite' / 'manifest.json'


def vite_asset_tags(entry_name, dev_mode):
    if dev_mode:
        return Markup(
            f'<script type="module" src="{VITE_DEV_SERVER}/@vite/client"></script>\n'
            f'<script type="module" src="{VITE_DEV_SERVER}/src/entries/{entry_name}.js"></script>'
        )

    manifest = json.loads(MANIFEST_PATH.read_text())
    entry = manifest[f'src/entries/{entry_name}.js']

    tags = [f'<script type="module" src="/static/dist/{entry["file"]}"></script>']
    for css_file in entry.get('css', []):
        tags.append(f'<link rel="stylesheet" href="/static/dist/{css_file}">')
    return Markup('\n'.join(tags))