import json
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
from og_image import render_essay_card
from essays import create_essay
from essays import delete_essay
from essays import get_essay
from essays import list_essays
from storage import upload_image
from saved_items import delete_saved_item
from saved_items import list_saved_items
from saved_items import save_item
from trending import SOURCES as TRENDING_SOURCES
from uv_tracking import add_reading as add_uv_reading
from uv_tracking import end_session as end_uv_session
from uv_tracking import get_open_session as get_open_uv_session
from uv_tracking import get_session as get_uv_session
from uv_tracking import list_sessions as list_uv_sessions
from uv_tracking import start_session as start_uv_session
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

with open(os.path.join(app.root_path, 'package.json')) as _package_json_file:
    APP_VERSION = json.load(_package_json_file)['version']

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
    return {'current_user': current_user, 'is_dev': not IS_PRODUCTION, 'app_version': APP_VERSION}


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


def fetch_random_article(topic=None, exclude_titles=()):
    exclude = {t.lower() for t in exclude_titles}

    if topic not in TOPIC_CATEGORIES:
        for _ in range(5):
            response = requests.get(WIKIPEDIA_RANDOM_SUMMARY_URL, headers=WIKIPEDIA_HEADERS)
            response.raise_for_status()
            article = response.json()
            if article.get('title', '').lower() not in exclude:
                return article
        return article

    pool = list(get_topic_category_pool(topic))
    random.shuffle(pool)
    for category in pool:
        members = [m for m in fetch_category_members(category, 'page') if m['title'].lower() not in exclude]
        random.shuffle(members)
        for member in members:
            title = member['title']
            summary_response = requests.get(
                WIKIPEDIA_SUMMARY_URL.format(title=quote(title.replace(' ', '_'))),
                headers=WIKIPEDIA_HEADERS,
            )
            if summary_response.ok:
                return summary_response.json()

    # No category in the pool yielded an unseen article; fall back to unrestricted random.
    response = requests.get(WIKIPEDIA_RANDOM_SUMMARY_URL, headers=WIKIPEDIA_HEADERS)
    response.raise_for_status()
    return response.json()


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


def current_admin():
    """Returns the logged-in User if they're an admin, else None."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        return None
    if not identity:
        return None
    user = db.session.get(User, int(identity))
    return user if user and user.is_admin else None


@app.route('/admin')
def admin_page():
    if not current_admin():
        return redirect(url_for('login_page'))
    return render_template('admin.html')


@app.route('/posts')
def posts_page_redirect():
    return redirect(url_for('essays_page'), code=301)


@app.route('/posts/<int:essay_id>')
def post_detail_page_redirect(essay_id):
    return redirect(url_for('essay_detail_page', essay_id=essay_id), code=301)


@app.route('/essays')
def essays_page():
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
    except Exception:
        identity = None
    if not identity:
        return redirect(url_for('login_page'))
    return render_template('essays.html')


@app.route('/essays/<int:essay_id>')
def essay_detail_page(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        return render_template(
            'error.html', title='Essay not found', message="This essay doesn't exist or was deleted."
        ), 404

    essay_dict = essay.to_dict()
    essay_dict['displayDate'] = essay.created_at.strftime('%B %-d, %Y at %-I:%M %p') if essay.created_at else ''
    author_name = essay_dict['author']['displayName'] or essay_dict['author']['username']
    body_excerpt = essay_dict['body'] if len(essay_dict['body']) <= 200 else essay_dict['body'][:199] + '…'
    return render_template(
        'essay_detail.html',
        essay=essay_dict,
        og_title=f'{author_name} on Data Viz',
        og_description=body_excerpt,
        og_image=url_for('api_essay_og_image', essay_id=essay_id, _external=True),
    )


def _generated_og_path(essay_id):
    return os.path.join(GENERATED_OG_DIR, f'{essay_id}.png')


@app.route('/api/essays/<int:essay_id>/og-image.png')
@limiter.limit('30 per minute')
def api_essay_og_image(essay_id):
    essay = get_essay(essay_id)
    if not essay:
        return jsonify({'error': 'Not found'}), 404

    cache_path = _generated_og_path(essay_id)
    if not os.path.exists(cache_path):
        image_bytes = render_essay_card(essay.to_dict())
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


WIKIPEDIA_UNAVAILABLE_ERROR = "Couldn't reach Wikipedia right now. Please try again."


@app.route('/api/random-article')
def api_random_article():
    topic = request.args.get('topic') or None
    exclude_titles = [t for t in request.args.get('exclude', '').split('|') if t]
    try:
        return jsonify(fetch_random_article(topic, exclude_titles))
    except requests.RequestException:
        return jsonify({'error': WIKIPEDIA_UNAVAILABLE_ERROR}), 502


@app.route('/api/admin/users')
def api_admin_users():
    if not current_admin():
        return jsonify({'error': 'Not found'}), 404
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


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


@app.route('/api/essays', methods=['GET', 'POST'])
@jwt_required()
def api_essays():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        essay, errors = create_essay(
            user,
            body=data.get('body') or '',
            saved_item_id=data.get('savedItemId'),
            image_url=data.get('imageUrl'),
        )
        if errors:
            return jsonify({'errors': errors}), 400
        return jsonify(essay.to_dict()), 201

    before_id = request.args.get('beforeId', type=int)
    essays = list_essays(before_id=before_id)
    return jsonify([essay.to_dict() for essay in essays])


@app.route('/api/uploads', methods=['POST'])
@jwt_required()
@limiter.limit('20 per hour')
def api_upload_image():
    file_storage = request.files.get('file')
    if not file_storage:
        return jsonify({'errors': {'file': 'No file provided.'}}), 400

    url, errors = upload_image(file_storage, folder=f'essays/{get_jwt_identity()}')
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'url': url}), 201


@app.route('/api/essays/<int:essay_id>', methods=['DELETE'])
@jwt_required()
def api_delete_essay(essay_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if not delete_essay(user, essay_id):
        return jsonify({'error': 'Not found'}), 404

    cache_path = _generated_og_path(essay_id)
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


@app.route('/trending')
def trending_page():
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


@app.route('/uv-index')
def uv_index_page():
    return render_template('uv_index.html')


OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'


def parse_lat_lon(args):
    """Returns (lat, lon, error_response). error_response is None on success."""
    try:
        lat = float(args.get('lat', ''))
        lon = float(args.get('lon', ''))
    except ValueError:
        return None, None, (jsonify({'error': 'lat and lon are required numbers.'}), 400)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None, (
            jsonify({'error': 'lat must be between -90 and 90, lon between -180 and 180.'}), 400
        )
    return lat, lon, None


def fetch_current_uv(lat, lon, include_daily=False):
    """Raises requests.RequestException on failure."""
    params = {'latitude': lat, 'longitude': lon, 'current': 'uv_index', 'timezone': 'auto'}
    if include_daily:
        params['daily'] = 'uv_index_max'
        params['forecast_days'] = 7
    response = requests.get(OPEN_METEO_URL, params=params)
    response.raise_for_status()
    return response.json()


@app.route('/api/uv-index')
@limiter.limit('30 per minute')
def api_uv_index():
    lat, lon, error = parse_lat_lon(request.args)
    if error:
        return error

    try:
        data = fetch_current_uv(lat, lon, include_daily=True)
    except requests.RequestException:
        return jsonify({'error': "Couldn't reach the weather service right now. Please try again."}), 502

    current = data.get('current', {})
    daily = data.get('daily', {})
    return jsonify({
        'lat': data.get('latitude', lat),
        'lon': data.get('longitude', lon),
        'timezone': data.get('timezone'),
        'current': {
            'uvIndex': current.get('uv_index'),
            'time': current.get('time'),
        },
        'daily': [
            {'date': date_str, 'uvIndexMax': uv_max}
            for date_str, uv_max in zip(daily.get('time', []), daily.get('uv_index_max', []))
        ],
    })


@app.route('/api/uv-sessions', methods=['GET', 'POST'])
@jwt_required()
def api_uv_sessions():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'POST':
        session = start_uv_session(user)
        return jsonify(session.to_dict()), 201

    sessions = list_uv_sessions(user)
    return jsonify([s.to_dict() for s in sessions])


@app.route('/api/uv-sessions/<int:session_id>', methods=['GET'])
@jwt_required()
def api_uv_session_detail(session_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    session = get_uv_session(user, session_id)
    if not session:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(session.to_dict(include_readings=True))


@app.route('/api/uv-sessions/<int:session_id>/readings', methods=['POST'])
@jwt_required()
@limiter.limit('60 per minute')
def api_uv_session_add_reading(session_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    session = get_open_uv_session(user, session_id)
    if not session:
        return jsonify({'error': 'Session not found or already ended.'}), 404

    lat, lon, error = parse_lat_lon(request.get_json(silent=True) or {})
    if error:
        return error

    try:
        data = fetch_current_uv(lat, lon)
    except requests.RequestException:
        return jsonify({'error': "Couldn't reach the weather service right now. Please try again."}), 502

    uv_index = data.get('current', {}).get('uv_index')
    if uv_index is None:
        return jsonify({'error': "Couldn't get a UV reading for that location."}), 502

    reading = add_uv_reading(session, lat, lon, uv_index)
    return jsonify(reading.to_dict()), 201


@app.route('/api/uv-sessions/<int:session_id>/end', methods=['POST'])
@jwt_required()
def api_uv_session_end(session_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({'error': 'Not found'}), 404

    session = get_open_uv_session(user, session_id)
    if not session:
        return jsonify({'error': 'Session not found or already ended.'}), 404

    session = end_uv_session(session)
    return jsonify(session.to_dict())


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template(
        'error.html', title='Page not found', message="This page doesn't exist. Check the URL and try again."
    ), 404


@app.errorhandler(500)
def handle_server_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500
    return render_template(
        'error.html', title='Something went wrong', message='An unexpected error occurred. Please try again.'
    ), 500


if __name__ == '__main__':
    app.run(debug=True, port=8081, host='0.0.0.0')