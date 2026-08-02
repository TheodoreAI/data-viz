import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

CARD_WIDTH = 1200
CARD_HEIGHT = 630
BACKGROUND = '#f3e9d2'
INK = '#3f3326'
GRIDLINE = '#d8c9a3'
BLUE = '#2f6690'
GOLD = '#b8935a'

FONT_DIR = Path(__file__).parent / 'static' / 'fonts'
REGULAR_FONT_PATH = FONT_DIR / 'PTSerif-Regular.ttf'
BOLD_FONT_PATH = FONT_DIR / 'PTSerif-Bold.ttf'

FETCH_TIMEOUT = 4
FETCH_HEADERS = {'User-Agent': 'data-viz-app/1.0 (mateoej12@gmail.com)'}


def _font(path, size):
    return ImageFont.truetype(str(path), size)


def _wrap_text(draw, text, font, max_width, max_lines):
    words = text.split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            current = ''
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    consumed_words = sum(len(line.split()) for line in lines)
    if consumed_words < len(words) and lines:
        last = lines[-1]
        while draw.textlength(last + '…', font=font) > max_width and len(last) > 1:
            last = last[:-1].rstrip()
        lines[-1] = last + '…'
    return lines


def _fetch_image(url):
    if not url:
        return None
    try:
        response = requests.get(url, headers=FETCH_HEADERS, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert('RGBA')
    except Exception:
        return None


def _fit_cover(img, target_w, target_h):
    """Scale + crop img to exactly fill target_w x target_h (like CSS object-fit: cover)."""
    src_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_height = target_h
        new_width = round(new_height * src_ratio)
    else:
        new_width = target_w
        new_height = round(new_width / src_ratio)
    resized = img.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - target_w) // 2
    top = (new_height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _avatar_png_url(avatar_url):
    # The app's avatars are DiceBear SVGs; ask for the PNG variant instead
    # since Pillow can't decode SVG.
    return avatar_url.replace('/svg?', '/png?') + '&size=128'


def render_post_card(post):
    """post is the dict shape returned by Post.to_dict()."""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(img)

    shared_item = post.get('sharedItem')
    thumb_url = post.get('imageUrl') or (shared_item and shared_item.get('imageUrl'))
    has_thumb = bool(thumb_url)
    thumb_w = 340
    text_right_edge = (CARD_WIDTH - thumb_w - 40) if has_thumb else (CARD_WIDTH - 60)

    wordmark_font = _font(BOLD_FONT_PATH, 26)
    draw.text((60, 50), 'DATA VIZ', font=wordmark_font, fill=BLUE)
    draw.line((60, 94, text_right_edge, 94), fill=GRIDLINE, width=2)

    avatar_size = 64
    avatar_x, avatar_y = 60, 130
    avatar_img = _fetch_image(_avatar_png_url(post['author']['avatarUrl']))
    if avatar_img:
        avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        img.paste(avatar_img, (avatar_x, avatar_y), mask)

    name_font = _font(BOLD_FONT_PATH, 32)
    author_name = post['author']['displayName'] or post['author']['username']
    draw.text((avatar_x + avatar_size + 20, avatar_y + 14), author_name, font=name_font, fill=INK)

    body_font = _font(REGULAR_FONT_PATH, 40)
    body_lines = _wrap_text(draw, post['body'], body_font, text_right_edge - 60, max_lines=5)
    body_y = avatar_y + avatar_size + 50
    line_height = 54
    for i, line in enumerate(body_lines):
        draw.text((60, body_y + i * line_height), line, font=body_font, fill=INK)

    if has_thumb:
        thumb_img = _fetch_image(thumb_url)
        if thumb_img:
            fitted = _fit_cover(thumb_img.convert('RGB'), thumb_w, CARD_HEIGHT)
            img.paste(fitted, (CARD_WIDTH - thumb_w, 0))
            draw.line((CARD_WIDTH - thumb_w, 0, CARD_WIDTH - thumb_w, CARD_HEIGHT), fill=GOLD, width=4)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
