import os
import random
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask_jwt_extended import JWTManager
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import set_access_cookies
from flask_jwt_extended import unset_jwt_cookies
from flask_jwt_extended import verify_jwt_in_request
from flask_migrate import Migrate

from auth import authenticate_user
from auth import change_password
from auth import delete_account
from auth import register_user
from auth import update_bio
from models import User
from models import db
from vite import vite_asset_tags
from wikidata import fetch_art_feed_page
from wikidata import fetch_art_movements

load_dotenv()

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
GRAPH_LINKS_LIMIT = 5

TOPIC_CATEGORIES = {
    'art': 'Category:Art',
    'physics': 'Category:Physics',
    'computer-science': 'Category:Computer science',
    'history': 'Category:History',
}
_topic_category_pool_cache = {}

app = Flask(__name__)
app.jinja_env.globals['vite_asset'] = lambda entry: vite_asset_tags(entry, app.debug, request.host)

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data-viz.db')
if DATABASE_URL.startswith('postgres://'):
    # Render's connection strings use the legacy 'postgres://' scheme, which
    # SQLAlchemy 1.4+ no longer accepts.
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Remember to clean this up before deploying
# to production;
# this is just for development convenience.
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    JWT_SECRET_KEY = 'dev-only-insecure-secret-change-me-before-deploying-anywhere-real'
    print(
        'WARNING: JWT_SECRET_KEY is not set; using an insecure '
        'development default. Set JWT_SECRET_KEY in production.'
    )
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = not app.debug
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


@app.context_processor
def inject_current_user():
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            current_user = db.session.get(User, int(identity))
    except Exception:
        current_user = None
    return {'current_user': current_user}


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


def fetch_article_links(title, limit=GRAPH_LINKS_LIMIT):
    response = requests.get(WIKIPEDIA_ACTION_API_URL, headers=WIKIPEDIA_HEADERS, params={
        'action': 'query',
        'prop': 'links',
        'titles': title,
        'plnamespace': 0,
        'pllimit': 500,
        'format': 'json',
    })
    response.raise_for_status()
    pages = response.json()['query']['pages']
    page = next(iter(pages.values()), {})
    links = [link['title'] for link in page.get('links', [])]
    random.shuffle(links)
    return links[:limit]


@app.route('/')
def hello_world():
    article = fetch_random_article()
    return render_template('home.html', article=article, topics=TOPIC_CATEGORIES)


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/profile')
def profile_page():
    return render_template('profile.html')


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user, errors = register_user(username, email, password)
    if errors:
        return jsonify({'errors': errors}), 400

    access_token = create_access_token(identity=str(user.id))
    response = jsonify({'user': user.to_dict()})
    set_access_cookies(response, access_token)
    return response, 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get('identifier') or '').strip()
    password = data.get('password') or ''

    user = authenticate_user(identifier, password)
    if not user:
        return jsonify({'errors': {'form': 'Incorrect username/email or password.'}}), 401

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    response = jsonify({'user': user.to_dict()})
    set_access_cookies(response, access_token)
    return response


@app.route('/api/logout', methods=['POST'])
def api_logout():
    response = jsonify({'ok': True})
    unset_jwt_cookies(response)
    return response


@app.route('/api/profile', methods=['GET', 'PATCH'])
@jwt_required()
def api_profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        errors = update_bio(user, (data.get('bio') or '').strip())
        if errors:
            return jsonify({'errors': errors}), 400

    return jsonify(user.to_dict())


@app.route('/api/profile/password', methods=['POST'])
@jwt_required()
def api_change_password():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(silent=True) or {}
    errors = change_password(
        user,
        data.get('currentPassword') or '',
        data.get('newPassword') or '',
    )
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'ok': True})


@app.route('/api/account', methods=['DELETE'])
@jwt_required()
def api_delete_account():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json(silent=True) or {}
    errors = delete_account(user, data.get('password') or '')
    if errors:
        return jsonify({'errors': errors}), 400

    response = jsonify({'ok': True})
    unset_jwt_cookies(response)
    return response


@app.route('/api/random-article')
def api_random_article():
    topic = request.args.get('topic') or None
    return jsonify(fetch_random_article(topic))


@app.route('/art')
def art():
    movements = fetch_art_movements()
    paintings = fetch_art_feed_page(offset=0)
    return render_template('art.html', paintings=paintings, movements=movements)


@app.route('/api/art-feed')
def api_art_feed():
    offset = request.args.get('offset', 0, type=int)
    movement = request.args.get('movement') or None
    return jsonify(fetch_art_feed_page(offset=offset, movement=movement))


@app.route('/api/art-movements')
def api_art_movements():
    return jsonify(fetch_art_movements())


@app.route('/graph')
def graph():
    article = fetch_random_article()
    title = article['title']
    links = fetch_article_links(title)
    return render_template('graph.html', title=title, links=links, topics=TOPIC_CATEGORIES)


@app.route('/api/article-links')
def api_article_links():
    title = request.args.get('title', '')
    return jsonify({'title': title, 'links': fetch_article_links(title)})


@app.route('/api/article-search')
def api_article_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    response = requests.get(WIKIPEDIA_ACTION_API_URL, headers=WIKIPEDIA_HEADERS, params={
        'action': 'opensearch',
        'search': query,
        'limit': 8,
        'namespace': 0,
        'format': 'json',
    })
    response.raise_for_status()
    titles = response.json()[1]
    return jsonify(titles)


@app.route('/api/article-summary')
def api_article_summary():
    title = request.args.get('title', '')
    response = requests.get(
        WIKIPEDIA_SUMMARY_URL.format(title=quote(title.replace(' ', '_'))),
        headers=WIKIPEDIA_HEADERS,
    )
    if not response.ok:
        return jsonify({'title': title, 'extract': '', 'thumbnail': None})
    summary = response.json()
    return jsonify({
        'title': summary.get('title', title),
        'extract': summary.get('extract', ''),
        'thumbnail': summary.get('thumbnail', {}).get('source'),
    })


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