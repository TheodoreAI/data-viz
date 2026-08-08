import os
import random
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from flask import url_for
from flask_jwt_extended import JWTManager
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import set_access_cookies
from flask_jwt_extended import unset_jwt_cookies
from flask_jwt_extended import verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate

from auth import authenticate_user
from auth import change_password
from auth import delete_account
from auth import generate_reset_token
from auth import register_user
from auth import reset_password as apply_password_reset
from auth import update_bio
from auth import update_display_name
from auth import verify_reset_token
from email_utils import init_mail
from email_utils import send_password_reset_email
from models import User
from models import db
from og_image import render_post_card
from posts import create_post
from posts import delete_post
from posts import get_post
from posts import list_posts
from storage import upload_image
from saved_items import delete_saved_item
from saved_items import list_saved_items
from saved_items import save_item
from trending import SOURCES as TRENDING_SOURCES
from vite import vite_asset_tags

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

GENERATED_OG_DIR = os.path.join(app.root_path, 'static', 'generated_og')
os.makedirs(GENERATED_OG_DIR, exist_ok=True)

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
# app.debug is only set once app.run(debug=...) actually runs, which happens
# after this module-level config is read — so `not app.debug` here would
# always evaluate to True (Secure cookie) even in local dev. Safari, unlike
# Chrome/Firefox, refuses to store Secure cookies over plain HTTP even on
# localhost, so that bug silently broke login in Safari only. Use the
# RENDER env var (set in production) as the actual dev/prod signal instead.
IS_PRODUCTION = bool(os.environ.get('RENDER'))
app.config['JWT_COOKIE_SECURE'] = IS_PRODUCTION
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
# Without this, flask-jwt-extended issues the cookie with no Max-Age/Expires
# (a browser "session cookie"). iOS PWAs launched from the home screen often
# start a fresh WKWebView process per launch, which drops session cookies —
# users get logged out well before the token's actual 7-day expiry.
app.config['JWT_SESSION_COOKIE'] = False

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
mail_config = {
    'api_key': RESEND_API_KEY,
    'from_email': os.environ.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev'),
}

db.init_app(app)
migrate = Migrate(app, db)
init_mail(mail_config, configured=bool(RESEND_API_KEY))
jwt = JWTManager(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[])


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
    default_topic = 'computer-science'
    article = fetch_random_article(default_topic)
    return render_template(
        'home.html', article=article, topics=TOPIC_CATEGORIES, default_topic=default_topic
    )


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/profile')
def profile_page():
    return render_template('profile.html')


@app.route('/dashboard')
def dashboard_page():
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        identity = None
    if not identity:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html')


@app.route('/posts')
def posts_page():
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        identity = None
    if not identity:
        return redirect(url_for('login_page'))
    return render_template('posts.html')


@app.route('/posts/<int:post_id>')
def post_detail_page(post_id):
    post = get_post(post_id)
    if not post:
        return render_template('post_not_found.html'), 404

    post_dict = post.to_dict()
    post_dict['displayDate'] = post.created_at.strftime('%B %-d, %Y at %-I:%M %p') if post.created_at else ''
    author_name = post_dict['author']['displayName'] or post_dict['author']['username']
    body_excerpt = post_dict['body'] if len(post_dict['body']) <= 200 else post_dict['body'][:199] + '…'
    return render_template(
        'post_detail.html',
        post=post_dict,
        og_title=f'{author_name} on Data Viz',
        og_description=body_excerpt,
        og_image=url_for('api_post_og_image', post_id=post_id, _external=True),
    )


def _generated_og_path(post_id):
    return os.path.join(GENERATED_OG_DIR, f'{post_id}.png')


@app.route('/api/posts/<int:post_id>/og-image.png')
@limiter.limit('30 per minute')
def api_post_og_image(post_id):
    post = get_post(post_id)
    if not post:
        return jsonify({'error': 'Not found'}), 404

    cache_path = _generated_og_path(post_id)
    if not os.path.exists(cache_path):
        image_bytes = render_post_card(post.to_dict())
        with open(cache_path, 'wb') as f:
            f.write(image_bytes)

    response = send_file(cache_path, mimetype='image/png')
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@app.route('/reset-password')
def reset_password_page():
    return render_template('reset_password.html')


@app.route('/api/register', methods=['POST'])
@limiter.limit('10 per hour')
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
@limiter.limit('10 per minute')
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


@app.route('/api/forgot-password', methods=['POST'])
@limiter.limit('5 per hour')
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    user = User.query.filter_by(email=email).first()
    if user:
        token = generate_reset_token(app.config['JWT_SECRET_KEY'], user)
        reset_url = f"{request.host_url.rstrip('/')}/reset-password?token={token}"
        send_password_reset_email(user, reset_url)

    # Always the same response, whether or not that email is registered,
    # so this endpoint can't be used to discover which emails have accounts.
    return jsonify({'ok': True})


@app.route('/api/reset-password', methods=['POST'])
@limiter.limit('10 per hour')
def api_reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get('token') or ''
    new_password = data.get('newPassword') or ''

    user = verify_reset_token(app.config['JWT_SECRET_KEY'], token)
    if not user:
        return jsonify({'errors': {'form': 'This reset link is invalid or has expired.'}}), 400

    errors = apply_password_reset(user, new_password)
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'ok': True})


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
        if 'bio' in data:
            errors = update_bio(user, (data.get('bio') or '').strip())
            if errors:
                return jsonify({'errors': errors}), 400
        if 'displayName' in data:
            errors = update_display_name(user, (data.get('displayName') or '').strip())
            if errors:
                return jsonify({'errors': errors}), 400

    return jsonify(user.to_dict())


@app.route('/api/profile/password', methods=['POST'])
@jwt_required()
@limiter.limit('10 per hour')
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
@limiter.limit('10 per hour')
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


@app.route('/nodes')
def nodes():
    default_topic = 'computer-science'
    article = fetch_random_article(default_topic)
    title = article['title']
    links = fetch_article_links(title)
    return render_template(
        'graph.html', title=title, links=links, topics=TOPIC_CATEGORIES, default_topic=default_topic
    )


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


def fetch_top_viewed_titles(year, month, day, limit=10):
    """Lightweight version of the /bubbles fetch — just title/views/url, no
    per-article summary lookups, so it's fast enough for a dashboard widget."""
    top_url = WIKIPEDIA_TOP_VIEWED_URL.format(year=year, month=f'{month:02d}', day=day)
    response = requests.get(top_url, headers=WIKIPEDIA_HEADERS, timeout=10)
    response.raise_for_status()
    top_articles = response.json()['items'][0]['articles']

    articles = []
    for entry in top_articles:
        title = entry['article']
        if title in EXCLUDED_TITLES or title.startswith('Special:') or title.startswith('Wikipedia:'):
            continue
        articles.append({
            'title': title.replace('_', ' '),
            'views': entry['views'],
            'url': f'https://en.wikipedia.org/wiki/{quote(title)}',
        })
        if len(articles) == limit:
            break
    return articles


@app.route('/api/top-articles')
def api_top_articles():
    yesterday = date.today() - timedelta(days=1)
    year = request.args.get('year', default=yesterday.year, type=int)
    month = request.args.get('month', default=yesterday.month, type=int)
    day = request.args.get('day', type=int)  # omitted -> whole-month aggregate

    try:
        articles = fetch_top_viewed_titles(year, month, f'{day:02d}' if day else 'all-days')
    except requests.RequestException:
        return jsonify({'error': "Couldn't load article data for that period."}), 502

    return jsonify({'year': year, 'month': month, 'day': day, 'articles': articles})


@app.route('/api/stats')
def api_stats():
    return jsonify({
        'totalUsers': User.query.count(),
    })


@app.route('/api/saved-items', methods=['GET', 'POST'])
@jwt_required()
def api_saved_items():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        item, errors = save_item(
            user,
            item_type=data.get('itemType') or '',
            title=data.get('title') or '',
            subtitle=data.get('subtitle') or '',
            image_url=data.get('imageUrl') or '',
            source_url=data.get('sourceUrl') or '',
        )
        if errors:
            return jsonify({'errors': errors}), 400
        return jsonify(item.to_dict()), 201

    item_type = request.args.get('itemType') or None
    items = list_saved_items(user, item_type=item_type)
    return jsonify([item.to_dict() for item in items])


@app.route('/api/saved-items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def api_delete_saved_item(item_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if not delete_saved_item(user, item_id):
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'ok': True})


@app.route('/api/posts', methods=['GET', 'POST'])
@jwt_required()
def api_posts():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        post, errors = create_post(
            user,
            body=data.get('body') or '',
            saved_item_id=data.get('savedItemId'),
            image_url=data.get('imageUrl'),
        )
        if errors:
            return jsonify({'errors': errors}), 400
        return jsonify(post.to_dict()), 201

    before_id = request.args.get('beforeId', type=int)
    posts = list_posts(before_id=before_id)
    return jsonify([post.to_dict() for post in posts])


@app.route('/api/uploads', methods=['POST'])
@jwt_required()
@limiter.limit('20 per hour')
def api_upload_image():
    file_storage = request.files.get('file')
    if not file_storage:
        return jsonify({'errors': {'file': 'No file provided.'}}), 400

    url, errors = upload_image(file_storage, folder=f'posts/{get_jwt_identity()}')
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'url': url}), 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def api_delete_post(post_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if not delete_post(user, post_id):
        return jsonify({'error': 'Not found'}), 404

    cache_path = _generated_og_path(post_id)
    if os.path.exists(cache_path):
        os.remove(cache_path)

    return jsonify({'ok': True})


TOP_VIEWED_LOOKBACK_DAYS = 5


def fetch_latest_top_viewed_articles():
    """Wikimedia's pageviews pipeline can lag a day or more, so 'yesterday'
    sometimes 404s. Walk backwards until we find a published day.
    Returns (day, top_articles); raises the last error if none are found."""
    day = date.today() - timedelta(days=1)
    last_error = None
    for _ in range(TOP_VIEWED_LOOKBACK_DAYS):
        top_url = WIKIPEDIA_TOP_VIEWED_URL.format(
            year=day.year, month=f'{day.month:02d}', day=f'{day.day:02d}'
        )
        response = requests.get(top_url, headers=WIKIPEDIA_HEADERS)
        if response.status_code == 404:
            last_error = requests.exceptions.HTTPError(response=response)
            day -= timedelta(days=1)
            continue
        response.raise_for_status()
        return day, response.json()['items'][0]['articles']
    raise last_error


@app.route('/live-data')
def live_data():
    try:
        day, top_articles = fetch_latest_top_viewed_articles()
    except requests.RequestException:
        return render_template('bubbles.html', articles=None, date=None)

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

    return render_template('bubbles.html', articles=articles, date=day.isoformat())


@app.route('/api/trending/<source>')
@limiter.limit('30 per minute')
def api_trending(source):
    fetch = TRENDING_SOURCES.get(source)
    if not fetch:
        return jsonify({'error': 'Unknown source.'}), 404

    try:
        items = fetch()
    except requests.RequestException:
        return jsonify({'error': f"Couldn't reach {source} right now. Please try again."}), 502

    return jsonify({'source': source, 'items': items})


if __name__ == '__main__':
    app.run(debug=True, port=8081, host='0.0.0.0')