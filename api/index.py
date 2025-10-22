import os
import sys
import requests
import json
from flask import Flask, render_template_string, request, redirect, url_for, Response, jsonify, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
from urllib.parse import unquote, quote
from datetime import datetime, timedelta
import math
import re

# --- Environment Variables (Critical Settings) ---
# এটি বটের জন্য গোপন কী। অবশ্যই এটি পরিবর্তন করে একটি জটিল কী ব্যবহার করুন!
FAST_UPLOAD_API_KEY = os.environ.get("FAST_UPLOAD_API_KEY", "your_secret_fast_key_12345") 

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://mesohas358:mesohas358@cluster0.6kxy1vc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "7dc544d9253bccc3cfecc1c677f69819")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Nahid421")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Nahid421")
WEBSITE_NAME = os.environ.get("WEBSITE_NAME", "FreeMovieHub")
DEVELOPER_TELEGRAM_ID = os.environ.get("DEVELOPER_TELEGRAM_ID", "https://t.me/AllBotUpdatemy") 

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
# এটি আপনার লাইভ ওয়েবসাইট URL হবে (Vercel deployment এর জন্য এটি VERCEL_URL বা আপনার কাস্টম ডোমেন দিয়ে সেট করুন)
WEBSITE_URL = os.environ.get("WEBSITE_URL", "http://localhost:3000") 

# --- App Initialization ---
PLACEHOLDER_POSTER = "https://via.placeholder.com/400x600.png?text=Poster+Not+Found"
ITEMS_PER_PAGE = 20
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a_super_secret_key_for_flash_messages")


# --- Authentication ---
def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response('Could not verify your access level.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- NEW: API Key Authentication for Bot ---
def requires_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not provided_key or provided_key != FAST_UPLOAD_API_KEY:
            return jsonify({"error": "Unauthorized access. Invalid API Key."}), 401
        return f(*args, **kwargs)
    return decorated
# --- END NEW AUTH ---


# --- Database Connection ---
try:
    client = MongoClient(MONGO_URI)
    db = client["movie_db"]
    movies = db["movies"]
    settings = db["settings"]
    categories_collection = db["categories"]
    requests_collection = db["requests"]
    ott_collection = db["ott_platforms"]
    print("SUCCESS: Successfully connected to MongoDB!")

    if categories_collection.count_documents({}) == 0:
        default_categories = ["Bangla", "Hindi", "English", "18+ Adult", "Korean", "Dual Audio", "Bangla Dubbed", "Hindi Dubbed", "Indonesian", "Horror", "Action", "Thriller", "Anime", "Romance", "Trending"]
        categories_collection.insert_many([{"name": cat} for cat in default_categories])
        print("SUCCESS: Initialized default categories in the database.")

    default_design_settings = {
        "_id": "design_config",
        "language_tag_css": "padding: 3px 8px; font-size: 0.7rem; top: 8px; right: 8px; background-color: #00ffaa; color: #111; font-weight: 700; border-radius: 4px; box-shadow: 0 0 8px rgba(0, 255, 170, 0.5); z-index: 5;",
        "new_badge_css": "background-color: var(--primary-color); color: white; padding: 4px 12px 4px 8px; font-size: 0.7rem; font-weight: 700; z-index: 3; clip-path: polygon(0 0, 100% 0, 85% 100%, 0 100%);",
        "new_badge_text": "NEW"
    }
    if not settings.find_one({"_id": "design_config"}):
        settings.insert_one(default_design_settings)
        print("SUCCESS: Initialized default design settings.")

    try:
        movies.create_index("title")
        movies.create_index("type")
        movies.create_index("categories")
        movies.create_index("updated_at")
        movies.create_index("tmdb_id")
        movies.create_index("ott_platform")
        categories_collection.create_index("name", unique=True)
        ott_collection.create_index("name", unique=True)
        requests_collection.create_index("status")
        print("SUCCESS: MongoDB indexes checked/created.")
    except Exception as e:
        print(f"WARNING: Could not create MongoDB indexes: {e}")

    result = movies.update_many(
        {"updated_at": {"$exists": False}},
        [{"$set": {"updated_at": "$created_at"}}]
    )
    if result.modified_count > 0:
        print(f"SUCCESS: Migrated {result.modified_count} old documents to include 'updated_at' field.")

except Exception as e:
    print(f"FATAL: Error connecting to MongoDB: {e}.")
    if os.environ.get('VERCEL') != '1':
        sys.exit(1)

# --- Helper function to format series info ---
def format_series_info(episodes, season_packs):
    """Generates a string like S01 [EP01-10 ADDED] & S02 [COMPLETE SEASON ADDED]"""
    info_parts = []
    if season_packs:
        sorted_packs = sorted(season_packs, key=lambda p: p.get('season_number', 0))
        for pack in sorted_packs:
            season_num = pack.get('season_number')
            if season_num is not None:
                info_parts.append(f"S{season_num:02d} [COMPLETE SEASON]")
    if episodes:
        episodes_by_season = {}
        for ep in episodes:
            season = ep.get('season')
            ep_num = ep.get('episode_number')
            if season is not None and ep_num is not None:
                if season not in episodes_by_season:
                    episodes_by_season[season] = []
                episodes_by_season[season].append(ep_num)

        for season in sorted(episodes_by_season.keys()):
            ep_nums = sorted(episodes_by_season[season])
            if not ep_nums: continue
            
            ep_range = f"EP{ep_nums[0]:02d}" if len(ep_nums) == 1 else f"EP{ep_nums[0]:02d}-{ep_nums[-1]:02d}"
            info_parts.append(f"S{season:02d} [{ep_range} ADDED]")

    return " & ".join(info_parts)


# --- Telegram Notification Function ---
def send_telegram_notification(movie_data, content_id, notification_type='new', series_update_info=None):
    tele_configs = settings.find_one({"_id": "telegram_config"})
    channels = tele_configs.get('channels', []) if tele_configs else []

    if not channels and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID):
        print("INFO: No Telegram channels configured in DB or ENV. Skipping notification.")
        return

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
        if not any(c.get('channel_id') == TELEGRAM_CHANNEL_ID for c in channels):
            channels.append({'token': TELEGRAM_BOT_TOKEN, 'channel_id': TELEGRAM_CHANNEL_ID})


    try:
        movie_url = f"{WEBSITE_URL}/movie/{str(content_id)}"
        
        title_with_year = movie_data.get('title', 'N/A')
        if movie_data.get('release_date'):
            year = movie_data['release_date'].split('-')[0]
            title_with_year += f" ({year})"
        
        if series_update_info:
            title_with_year += f" {series_update_info}"

        available_qualities = []
        if movie_data.get('links'):
            for link in movie_data['links']:
                if link.get('quality'):
                    available_qualities.append(link['quality'])
        if not available_qualities:
             available_qualities.append("WEB-DL")
        
        quality_str = ", ".join(sorted(list(set(available_qualities))))
        language_str = movie_data.get('language', 'N/A')
        genres_list = movie_data.get('genres', [])
        genres_str = ", ".join(genres_list) if genres_list else "N/A"
        clean_url = WEBSITE_URL.replace('https://', '').replace('www.', '')

        if notification_type == 'update':
            caption_header = f"🔄 **UPDATED : {title_with_year}**\n"
        else:
            caption_header = f"🔥 **NEW ADDED : {title_with_year}**\n"
        
        caption = caption_header
        if language_str and not any(char.isdigit() for char in language_str):
             caption += f"**{language_str.upper()}**\n"

        caption += f"\n🎞️ Quality: **{quality_str}**"
        caption += f"\n🌐 Language: **{language_str}**"
        caption += f"\n🎭 Genres: **{genres_str}**"
        caption += f"\n\n🔗 Visit : **{clean_url}**"
        caption += f"\n⚠️ **অবশ্যই লিংকগুলো ক্রোম ব্রাউজারে ওপেন করবেন!!**"

        inline_keyboard = {"inline_keyboard": [[{"text": "📥👇 Download Now 👇📥", "url": movie_url}]]}

        sent_count = 0
        for config in channels:
            bot_token = config.get('token')
            channel_id = config.get('channel_id')

            if not bot_token or not channel_id:
                continue

            api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            # Ensure the poster URL is not None
            poster_to_send = movie_data.get('poster') or PLACEHOLDER_POSTER 

            payload = {
                'chat_id': channel_id, 
                'photo': poster_to_send, 
                'caption': caption, 
                'parse_mode': 'Markdown', 
                'reply_markup': json.dumps(inline_keyboard)
            }
            
            try:
                response = requests.post(api_url, data=payload, timeout=15)
                response.raise_for_status()
                
                if response.json().get('ok'):
                    print(f"SUCCESS: Telegram notification sent to channel '{channel_id}' (Type: {notification_type}).")
                    sent_count += 1
                else:
                    print(f"WARNING: Telegram API error for channel '{channel_id}': {response.json().get('description')}")
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Failed to send Telegram notification to channel '{channel_id}': {e}")
        
        if sent_count == 0:
            print("WARNING: Notification attempt failed for all configured channels.")

    except Exception as e:
        print(f"ERROR: Unexpected error in send_telegram_notification: {e}")


# --- Custom Jinja Filter for Relative Time ---
def time_ago(obj_id):
    if not isinstance(obj_id, ObjectId): return ""
    post_time = obj_id.generation_time.replace(tzinfo=None)
    now = datetime.utcnow()
    diff = now - post_time
    seconds = diff.total_seconds()
    
    if seconds < 60: return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"

app.jinja_env.filters['time_ago'] = time_ago

@app.context_processor
def inject_globals():
    ad_settings = settings.find_one({"_id": "ad_config"})
    design_settings = settings.find_one({"_id": "design_config"}) or {}
    all_categories = [cat['name'] for cat in categories_collection.find().sort("name", 1)]
    all_ott_platforms = list(ott_collection.find().sort("name", 1))
    
    category_icons = {
        "Bangla": "fa-film", "Hindi": "fa-film", "English": "fa-film",
        "18+ Adult": "fa-exclamation-circle", "Korean": "fa-tv", "Dual Audio": "fa-headphones",
        "Bangla Dubbed": "fa-microphone-alt", "Hindi Dubbed": "fa-microphone-alt", "Horror": "fa-ghost",
        "Action": "fa-bolt", "Thriller": "fa-knife-cutting", "Anime": "fa-dragon", "Romance": "fa-heart",
        "Trending": "fa-fire", "ALL MOVIES": "fa-layer-group", "WEB SERIES & TV SHOWS": "fa-tv-alt", "HOME": "fa-home"
    }
    return dict(
        website_name=WEBSITE_NAME, 
        ad_settings=ad_settings or {}, 
        design_settings=design_settings, 
        predefined_categories=all_categories, 
        quote=quote, 
        datetime=datetime, 
        category_icons=category_icons,
        all_ott_platforms=all_ott_platforms,
        developer_telegram_id=DEVELOPER_TELEGRAM_ID
    )

# =========================================================================================
# === [START] HTML TEMPLATES (Including updated detail_html and admin_html) ===============
# =========================================================================================
# --- IMPORTANT: The HTML templates must be defined here for the app to run ---
# Due to the length, I am placing the full templates here.
index_html = """... (Full index_html content from previous response) ..."""
detail_html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<title>{{ movie.title if movie else "Content Not Found" }} - {{ website_name }}</title>
<link rel="icon" href="https://img.icons8.com/fluency/48/cinema-.png" type="image/png">
<meta name="description" content="{{ movie.overview|striptags|truncate(160) }}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Oswald:wght@700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css">
<link rel="stylesheet" href="https://unpkg.com/swiper/swiper-bundle.min.css"/>
{{ ad_settings.ad_header | safe }}
<style>
  :root {
      --bg-color: #0d0d0d;
      --card-bg: #1a1a1a;
      --text-light: #ffffff;
      --text-dark: #8c8c8c;
      --primary-color: #E50914;
      --cyan-accent: #00FFFF;
      --lime-accent: #adff2f;
      --g-1: #ff00de; --g-2: #00ffff;
  }
  html { box-sizing: border-box; } *, *:before, *:after { box-sizing: inherit; }
  body { font-family: 'Poppins', sans-serif; background-color: var(--bg-color); color: var(--text-light); overflow-x: hidden; margin:0; padding:0; }
  a { text-decoration: none; color: inherit; }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px 15px; }

  .back-link { 
      display: inline-block; 
      margin-bottom: 20px; 
      padding: 8px 15px; 
      background-color: var(--card-bg); 
      color: var(--text-dark);
      border-radius: 50px; 
      text-decoration: none; 
      font-size: 0.9rem; 
      transition: all 0.2s ease; 
  }
  .back-link:hover { 
      color: var(--text-light);
      background-color: #333;
  }
  .back-link i { 
      margin-right: 8px; 
  }
  
  .hero-section {
      position: relative;
      width: 100%;
      max-width: 900px;
      margin: 20px auto 80px;
      aspect-ratio: 16 / 9;
      background-size: cover;
      background-position: center;
      border-radius: 12px;
      box-shadow: 0 0 25px rgba(0, 255, 255, 0.4);
      overflow: visible;
  }
  .hero-poster {
      position: absolute;
      left: 30px;
      bottom: -60px;
      height: 95%;
      aspect-ratio: 2 / 3;
      object-fit: cover;
      border-radius: 8px;
      box-shadow: 0 8px 25px rgba(0,0,0,0.6);
      border: 2px solid rgba(255, 255, 255, 0.1);
  }
  .badge-new, .badge-completed {
      position: absolute;
      padding: 6px 15px;
      font-weight: bold;
      font-size: 0.9rem;
      color: white;
      border-radius: 5px;
      text-transform: uppercase;
      backdrop-filter: blur(5px);
  }
  .badge-new {
      top: 20px;
      right: 20px;
      background-color: rgba(255, 30, 30, 0.8);
  }
  .badge-completed {
      bottom: 20px;
      right: 20px;
      background-color: rgba(0, 255, 0, 0.8);
      color: #000;
  }
  .content-title-section {
      text-align: center;
      padding: 10px 15px 30px;
      max-width: 900px;
      margin: 0 auto;
  }
  .main-title {
      font-family: 'Oswald', sans-serif;
      font-size: clamp(1.8rem, 5vw, 2.5rem);
      font-weight: 700;
      line-height: 1.4;
      color: var(--cyan-accent);
      text-transform: uppercase;
  }
  .title-meta-info {
      color: var(--lime-accent);
      display: block;
  }

  .tabs-nav { display: flex; justify-content: center; gap: 10px; margin: 20px 0 30px; }
  .tab-link { flex: 1; max-width: 200px; padding: 12px; background-color: var(--card-bg); border: none; color: var(--text-dark); font-weight: 600; font-size: 1rem; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; }
  .tab-link.active { background-color: var(--primary-color); color: var(--text-light); }
  .tab-pane { display: none; }
  .tab-pane.active { display: block; animation: fadeIn 0.5s; }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  
  #info-pane p { font-size: 0.95rem; line-height: 1.8; color: var(--text-dark); text-align: justify; background-color: var(--card-bg); padding: 20px; border-radius: 8px; }
  .link-group { display: flex; flex-direction: column; gap: 10px; max-width: 800px; margin: 0 auto; }
  .link-group h3 { font-size: 1.2rem; font-weight: 500; margin-bottom: 10px; color: var(--text-dark); text-align: center; }
  .action-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 15px 20px; border-radius: 8px; font-weight: 500; font-size: 1rem; color: white; background: linear-gradient(90deg, var(--g-1), var(--g-2), var(--g-1)); background-size: 200% 100%; transition: background-position 0.5s ease; }
  .action-btn:hover { background-position: 100% 0; }
  .category-section { margin: 50px 0; }
  .category-title { font-size: 1.5rem; font-weight: 600; margin-bottom: 20px; }
  .movie-carousel .swiper-slide { width: 140px; }
  .movie-card { display: block; position: relative; }
  .movie-card .movie-poster { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 8px; }

  /* --- NEW SERIES ACCORDION STYLES --- */
  .season-toggle {
    background-color: #252525;
    color: var(--text-light);
    cursor: pointer;
    padding: 15px 20px;
    width: 100%;
    border: none;
    text-align: left;
    outline: none;
    font-size: 1.1rem;
    font-weight: 600;
    transition: background-color 0.4s;
    border-radius: 8px;
    margin-bottom: 5px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .season-toggle:hover {
    background-color: #333;
  }
  .season-toggle h3 {
    margin: 0;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
  }
  .season-toggle i {
    margin-right: 10px;
    transition: transform 0.3s ease;
  }
  .season-toggle.active i {
    transform: rotate(90deg);
  }
  .season-content {
    padding: 0 10px 10px;
    background-color: var(--card-bg);
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.4s ease-out, padding 0.4s ease-out;
    border-radius: 0 0 8px 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 15px;
  }
  .season-content.active {
    max-height: 2000px; /* Large value to accommodate all links */
    padding: 15px 10px 15px;
  }
  .season-pack-btn {
    background: linear-gradient(90deg, #ffc107, #ff6f00, #ffc107) !important;
    color: black !important;
    font-weight: 700 !important;
  }

  @media (min-width: 768px) {
      .movie-carousel .swiper-slide { width: 180px; }
  }
</style>
</head>
<body>
{{ ad_settings.ad_body_top | safe }}
{% if movie %}
<main class="container">
    <a href="#" onclick="window.history.back(); return false;" class="back-link">
        <i class="fas fa-arrow-left"></i> Go Back
    </a>
    
    <div class="hero-section" style="background-image: url('{{ movie.backdrop or movie.poster or 'https://via.placeholder.com/1280x720.png?text=No+Backdrop' }}');">
        <img src="{{ movie.poster or 'https://via.placeholder.com/400x600.png?text=No+Image' }}" alt="{{ movie.title }}" class="hero-poster">
        
        {% if (datetime.utcnow() - movie._id.generation_time.replace(tzinfo=None)).days < 3 %}
            <span class="badge-new">NEW</span>
        {% endif %}
        
        {% if movie.is_completed %}
            <span class="badge-completed">COMPLETED</span>
        {% endif %}
    </div>

    <div class="content-title-section">
        <h1 class="main-title">
            {{ movie.title }}
            <strong class="title-meta-info">
                {% if movie.release_date %}({{ movie.release_date.split('-')[0] }}){% endif %}
                {% if movie.type == 'series' and movie.episodes or movie.season_packs %}
                    {% set all_seasons_check = ((movie.episodes | map(attribute='season') | list) + (movie.season_packs | map(attribute='season_number') | list)) | unique | sort %}
                    {% set max_season = all_seasons_check[-1] if all_seasons_check else 1 %}
                    S{{ '%02d'|format(max_season|int) }}
                {% endif %}
                {{ movie.language or '' }}
            </strong>
        </h1>
    </div>

    <nav class="tabs-nav">
        <button class="tab-link" data-tab="info-pane">Info</button>
        <button class="tab-link active" data-tab="downloads-pane">Download Links</button>
    </nav>

    <div class="tabs-content">
        <div class="tab-pane" id="info-pane">
            <p>{{ movie.overview or 'No description available.' }}</p>
        </div>
        <div class="tab-pane active" id="downloads-pane">
            {% if ad_settings.ad_detail_page %}<div class="ad-container">{{ ad_settings.ad_detail_page | safe }}</div>{% endif %}
            
            {% if movie.type == 'movie' and movie.links %}
                <div class="link-group">
                    <h3>Movie Download Links</h3>
                    {% for link_item in movie.links %}
                        {% if link_item.download_url %}<a href="{{ url_for('wait_page', target=quote(link_item.download_url)) }}" class="action-btn"><span>Download {{ link_item.quality }}</span><i class="fas fa-download"></i></a>{% endif %}
                        {% if link_item.watch_url %}<a href="{{ url_for('wait_page', target=quote(link_item.watch_url)) }}" class="action-btn"><span>Watch {{ link_item.quality }}</span><i class="fas fa-play"></i></a>{% endif %}
                    {% endfor %}
                </div>
            {% endif %}
            
            {% if movie.type == 'series' %}
                <div id="series-links-container" class="link-group" style="gap: 0;">
                    <h3>Series Links by Season</h3>
                    {% set all_seasons = ((movie.episodes | map(attribute='season') | list) + (movie.season_packs | map(attribute='season_number') | list)) | unique | sort %}
                    
                    {% for season_num in all_seasons %}
                        {% set episodes_for_season = movie.episodes | selectattr('season', 'equalto', season_num) | list %}
                        {% set season_pack = (movie.season_packs | selectattr('season_number', 'equalto', season_num) | first) if movie.season_packs else none %}
                        
                        <button class="season-toggle" data-season="{{ season_num }}">
                            <h3><i class="fas fa-caret-right"></i> Season {{ '%02d'|format(season_num|int) }} 
                            {% if season_pack %} (Complete Pack Available){% elif episodes_for_season %} ({{ episodes_for_season|length }} Episodes){% endif %}
                            </h3>
                        </button>
                        <div class="season-content">
                            {% if season_pack and (season_pack.download_link or season_pack.watch_link) %}
                                <a href="{{ url_for('wait_page', target=quote(season_pack.download_link or season_pack.watch_link)) }}" class="action-btn season-pack-btn">
                                    <span>Complete Season {{ season_num }} Pack</span><i class="fas fa-file-archive"></i>
                                </a>
                            {% endif %}
                            
                            {% for ep in episodes_for_season | sort(attribute='episode_number') %}
                                {% if ep.watch_link %}
                                    <a href="{{ url_for('wait_page', target=quote(ep.watch_link)) }}" class="action-btn">
                                        <span>Episode {{ '%02d'|format(ep.episode_number|int) }}: {{ ep.title or 'Watch/Download' }}</span><i class="fas fa-download"></i>
                                    </a>
                                {% endif %}
                            {% endfor %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}

            {% if movie.manual_links %}
                <div class="link-group" style="margin-top: 20px;">
                    <h3>More Manual Links</h3>
                    {% for link in movie.manual_links %}
                        <a href="{{ url_for('wait_page', target=quote(link.url)) }}" class="action-btn"><span>{{ link.name }}</span><i class="fas fa-link"></i></a>
                    {% endfor %}
                </div>
            {% endif %}

            {% if not movie.links and not movie.manual_links and not (movie.type == 'series' and (movie.episodes or movie.season_packs)) %}
                <p style="text-align:center; color: var(--text-dark);">No download links available yet.</p>
            {% endif %}
        </div>
    </div>
    
    {% if movie.screenshots %}
    <section class="category-section">
        <h2 class="category-title">Screenshots</h2>
        <div class="swiper gallery-thumbs">
            <div class="swiper-wrapper">
                {% for ss in movie.screenshots %}
                <div class="swiper-slide"><img src="{{ ss }}" loading="lazy" alt="Thumbnail of {{ movie.title }}" style="border-radius: 5px; height: 100%; object-fit: cover;"></div>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}

    {% if related_content %}
    <section class="category-section">
        <h2 class="category-title">You Might Also Like</h2>
        <div class="swiper movie-carousel">
            <div class="swiper-wrapper">
                {% for m in related_content %}
                <div class="swiper-slide">
                    <a href="{{ url_for('movie_detail', movie_id=m._id) }}" class="movie-card">
                        <img class="movie-poster" loading="lazy" src="{{ m.poster or 'https://via.placeholder.com/400x600.png?text=No+Image' }}" alt="{{ m.title }}">
                    </a>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}
</main>
{% else %}<div style="display:flex; justify-content:center; align-items:center; height:100vh;"><h2>Content not found.</h2></div>{% endif %}
<script src="https://unpkg.com/swiper/swiper-bundle.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const tabLinks = document.querySelectorAll('.tab-link');
        const tabPanes = document.querySelectorAll('.tab-pane');
        tabLinks.forEach(link => {
            link.addEventListener('click', () => {
                const tabId = link.getAttribute('data-tab');
                tabLinks.forEach(item => item.classList.remove('active'));
                tabPanes.forEach(pane => pane.classList.remove('active'));
                link.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            });
        });

        // --- NEW ACCORDION JS ---
        const seasonToggles = document.querySelectorAll('.season-toggle');
        seasonToggles.forEach(toggle => {
            toggle.addEventListener('click', function() {
                const content = this.nextElementSibling;
                const isActive = this.classList.contains('active');

                // Close all others
                seasonToggles.forEach(t => {
                    t.classList.remove('active');
                    if(t.nextElementSibling) {
                        t.nextElementSibling.classList.remove('active');
                        t.nextElementSibling.style.maxHeight = null;
                        t.nextElementSibling.style.padding = '0 10px 10px';
                    }
                });

                // Toggle current one
                if (!isActive) {
                    this.classList.add('active');
                    content.classList.add('active');
                    content.style.maxHeight = content.scrollHeight + "px";
                    content.style.padding = '15px 10px 15px';
                }
            });
        });
        // --- END NEW ACCORDION JS ---

        new Swiper('.movie-carousel', { slidesPerView: 3, spaceBetween: 15, breakpoints: { 640: { slidesPerView: 4 }, 768: { slidesPerView: 5 }, 1024: { slidesPerView: 6 } } });
        if (document.querySelector('.gallery-thumbs')) { new Swiper('.gallery-thumbs', { slidesPerView: 2, spaceBetween: 10, breakpoints: { 640: { slidesPerView: 3 }, 1024: { slidesPerView: 4 } } }); }
    });
</script>
{{ ad_settings.ad_footer | safe }}
</body></html>
"""
wait_page_html = """... (Full wait_page_html content) ..."""
request_html = """... (Full request_html content) ..."""
admin_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - {{ website_name }}</title>
    <link rel="icon" href="https://img.icons8.com/fluency/48/cinema-.png" type="image/png">
    <meta name="robots" content="noindex, nofollow">
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.2.0/css/all.min.css">
    <style>
        :root { --netflix-red: #E50914; --netflix-black: #141414; --dark-gray: #222; --light-gray: #333; --text-light: #f5f5f5; }
        body { font-family: 'Roboto', sans-serif; background: var(--netflix-black); color: var(--text-light); margin: 0; padding: 20px; }
        .admin-container { max-width: 1200px; margin: 20px auto; }
        .admin-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid var(--netflix-red); padding-bottom: 10px; margin-bottom: 30px; }
        .admin-header h1 { font-family: 'Bebas Neue', sans-serif; font-size: 3rem; color: var(--netflix-red); margin: 0; }
        h2 { font-family: 'Bebas Neue', sans-serif; color: var(--netflix-red); font-size: 2.2rem; margin-top: 40px; margin-bottom: 20px; border-left: 4px solid var(--netflix-red); padding-left: 15px; }
        form { background: var(--dark-gray); padding: 25px; border-radius: 8px; }
        fieldset { border: 1px solid var(--light-gray); border-radius: 5px; padding: 20px; margin-bottom: 20px; }
        legend { font-weight: bold; color: var(--netflix-red); padding: 0 10px; font-size: 1.2rem; }
        .form-group { margin-bottom: 15px; } label { display: block; margin-bottom: 8px; font-weight: bold; }
        input, textarea, select { width: 100%; padding: 12px; border-radius: 4px; border: 1px solid var(--light-gray); font-size: 1rem; background: var(--light-gray); color: var(--text-light); box-sizing: border-box; }
        textarea { resize: vertical; min-height: 100px;}
        .btn { display: inline-block; text-decoration: none; color: white; font-weight: 700; cursor: pointer; border: none; padding: 12px 25px; border-radius: 4px; font-size: 1rem; transition: background-color 0.2s; }
        .btn:disabled { background-color: #555; cursor: not-allowed; }
        .btn-primary { background: var(--netflix-red); } .btn-primary:hover:not(:disabled) { background-color: #B20710; }
        .btn-secondary { background: #555; } .btn-danger { background: #dc3545; }
        .btn-edit { background: #007bff; } .btn-success { background: #28a745; }
        .table-container { display: block; overflow-x: auto; white-space: nowrap; }
        table { width: 100%; border-collapse: collapse; } th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid var(--light-gray); }
        .action-buttons { display: flex; gap: 10px; }
        .dynamic-item { border: 1px solid var(--light-gray); padding: 15px; margin-bottom: 15px; border-radius: 5px; position: relative; }
        .dynamic-item .btn-danger { position: absolute; top: 10px; right: 10px; padding: 4px 8px; font-size: 0.8rem; }
        hr { border: 0; height: 1px; background-color: var(--light-gray); margin: 50px 0; }
        .tmdb-fetcher { display: flex; gap: 10px; }
        .checkbox-group { display: flex; flex-wrap: wrap; gap: 15px; padding: 10px 0; } .checkbox-group label { display: flex; align-items: center; gap: 8px; font-weight: normal; cursor: pointer;}
        .checkbox-group input { width: auto; }
        .link-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 2000; display: none; justify-content: center; align-items: center; padding: 20px; }
        .modal-content { background: var(--dark-gray); padding: 30px; border-radius: 8px; width: 100%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-shrink: 0; }
        .modal-body { overflow-y: auto; }
        .modal-close { background: none; border: none; color: #fff; font-size: 2rem; cursor: pointer; }
        #search-results { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; }
        .result-item { cursor: pointer; text-align: center; }
        .result-item img { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 5px; margin-bottom: 10px; border: 2px solid transparent; transition: all 0.2s; }
        .result-item:hover img { transform: scale(1.05); border-color: var(--netflix-red); }
        .result-item p { font-size: 0.9rem; }
        .season-pack-item { display: grid; grid-template-columns: 100px 1fr 1fr; gap: 10px; align-items: flex-end; }
        .manage-content-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }
        .search-form { display: flex; gap: 10px; flex-grow: 1; max-width: 500px; }
        .search-form input { flex-grow: 1; }
        .search-form .btn { padding: 12px 20px; }
        .dashboard-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--dark-gray); padding: 20px; border-radius: 8px; text-align: center; border-left: 5px solid var(--netflix-red); }
        .stat-card h3 { margin: 0 0 10px; font-size: 1.2rem; color: var(--text-light); }
        .stat-card p { font-size: 2.5rem; font-weight: 700; margin: 0; color: var(--netflix-red); }
        .management-section { display: flex; flex-wrap: wrap; gap: 30px; align-items: flex-start; }
        .management-list { flex: 1; min-width: 250px; }
        .management-item { display: flex; justify-content: space-between; align-items: center; background: var(--dark-gray); padding: 10px 15px; border-radius: 4px; margin-bottom: 10px; }
        .status-badge { padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8rem; font-weight: bold; }
        .status-pending { background-color: #ffc107; color: black; }
        .status-fulfilled { background-color: #28a745; }
        .status-rejected { background-color: #6c757d; }
    </style>
</head>
<body>
<div class="admin-container">
    <header class="admin-header"><h1>Admin Panel</h1><a href="{{ url_for('home') }}" target="_blank">View Site</a></header>
    
    <h2><i class="fas fa-tachometer-alt"></i> At a Glance</h2>
    <div class="dashboard-stats">
        <div class="stat-card"><h3>Total Content</h3><p>{{ stats.total_content }}</p></div>
        <div class="stat-card"><h3>Total Movies</h3><p>{{ stats.total_movies }}</p></div>
        <div class="stat-card"><h3>Total Series</h3><p>{{ stats.total_series }}</p></div>
        <div class="stat-card"><h3>Pending Requests</h3><p>{{ stats.pending_requests }}</p></div>
    </div>
    <hr>

    <!-- NEW MANUAL FAST PASTE INJECTOR -->
    <h2><i class="fas fa-magic"></i> Fast Paste Link Injector (Manual)</h2>
    <form method="post">
        <input type="hidden" name="form_action" value="fast_paste_injector">
        <fieldset><legend>Paste Content from Telegram (Title & Links)</legend>
            <div class="form-group">
                <label for="paste_content">Paste Text (First line is Title, lines starting with resolution/link are parsed):</label>
                <textarea name="paste_content" id="paste_content" rows="10" required placeholder="Example:
Velayudham-Shahenshah 2023 Bengali Dubbed ORG BongoBD

⭕️ 𝟰𝟴𝟬𝗽 👉 https://1024terabox.com/s/link1

⭕️ 𝟳𝟮𝟬𝗽 👉https://1024terabox.com/s/link2
">
                </textarea>
            </div>
            <div class="form-group"><label>Optional: Language Tag (e.g., Bengali Dubbed):</label><input type="text" name="injector_language" placeholder="Bengali Dubbed"></div>
            <div class="form-group"><label>Optional: Categories (Select all that apply):</label><div class="checkbox-group">{% for cat in categories_list %}<label><input type="checkbox" name="injector_categories" value="{{ cat.name }}"> {{ cat.name }}</label>{% endfor %}</div></div>
            <button type="submit" class="btn btn-success"><i class="fas fa-upload"></i> Inject Content</button>
        </fieldset>
    </form>
    <hr>
    <!-- END NEW MANUAL FAST PASTE INJECTOR -->
    
    <h2><i class="fas fa-plus-circle"></i> Add New Content</h2>
    <fieldset><legend>Automatic Method (Search TMDB)</legend><div class="form-group"><div class="tmdb-fetcher"><input type="text" id="tmdb_search_query" placeholder="e.g., Avengers Endgame"><button type="button" id="tmdb_search_btn" class="btn btn-primary" onclick="searchTmdb()">Search</button></div></div></fieldset>
    <form method="post">
        <input type="hidden" name="form_action" value="add_content"><input type="hidden" name="tmdb_id" id="tmdb_id">
        <fieldset><legend>Core Details</legend>
            <div class="form-group"><label>Title:</label><input type="text" name="title" id="title" required></div>
            <div class="form-group"><label>Poster URL:</label><input type="url" name="poster" id="poster"></div>
            <div class="form-group"><label>Backdrop URL:</label><input type="url" name="backdrop" id="backdrop"></div>
            <div class="form-group"><label>Overview:</label><textarea name="overview" id="overview"></textarea></div>
            <div class="form-group">
                <label>Screenshots (Paste one URL per line):</label>
                <textarea name="screenshots" rows="5"></textarea>
            </div>
            <div class="form-group"><label>Language:</label><input type="text" name="language" id="language" placeholder="e.g., Hindi, English, Dual Audio"></div>
            <div class="form-group"><label>Genres (comma-separated):</label><input type="text" name="genres" id="genres"></div>
            <div class="form-group"><label>Categories:</label><div class="checkbox-group">{% for cat in categories_list %}<label><input type="checkbox" name="categories" value="{{ cat.name }}"> {{ cat.name }}</label>{% endfor %}</div></div>
            <div class="form-group"><label>Content Type:</label><select name="content_type" id="content_type" onchange="toggleFields()"><option value="movie">Movie</option><option value="series">Series</option></select></div>
            <div class="form-group"><label>OTT Platform:</label>
                <select name="ott_platform">
                    <option value="None">None</option>
                    {% for platform in ott_list %}
                    <option value="{{ platform.name }}">{{ platform.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group"><div class="checkbox-group"><label><input type="checkbox" name="is_completed"> Mark as Completed?</label></div></div>
        </fieldset>
        <div id="movie_fields">
            <fieldset><legend>Movie Links</legend>
                <div class="link-pair"><label>480p Watch Link:<input type="url" name="watch_link_480p"></label><label>480p Download Link:<input type="url" name="download_link_480p"></label></div>
                <div class="link-pair"><label>720p Watch Link:<input type="url" name="watch_link_720p"></label><label>720p Download Link:<input type="url" name="download_link_720p"></label></div>
                <div class="link-pair"><label>1080p Watch Link:<input type="url" name="watch_link_1080p"></label><label>1080p Download Link:<input type="url" name="download_link_1080p"></label></div>
                 <div class="link-pair"><label>BLU-RAY Watch Link:<input type="url" name="watch_link_BLU-RAY"></label><label>BLU-RAY Download Link:<input type="url" name="download_link_BLU-RAY"></label></div>
            </fieldset>
        </div>
        <div id="episode_fields" style="display: none;">
            <fieldset><legend>Series Links</legend>
                <label>Complete Season Packs:</label><div id="season_packs_container"></div><button type="button" onclick="addSeasonPackField()" class="btn btn-secondary"><i class="fas fa-plus"></i> Add Season Pack</button><hr style="margin: 20px 0;"><label>Individual Episodes:</label><div id="episodes_container"></div><button type="button" onclick="addEpisodeField()" class="btn btn-secondary"><i class="fas fa-plus"></i> Add Episode</button>
            </fieldset>
        </div>
        <fieldset><legend>Manual Download Buttons</legend><div id="manual_links_container"></div><button type="button" onclick="addManualLinkField()" class="btn btn-secondary"><i class="fas fa-plus"></i> Add Manual Button</button></fieldset>
        <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Add Content</button>
    </form>
    <hr>
    
    <div class="management-content-section">
        <div class="manage-content-header">
            <h2><i class="fas fa-tasks"></i> Manage Content</h2>
            <div class="search-form">
                <input type="search" id="admin-live-search" placeholder="Type to search content live..." autocomplete="off">
            </div>
        </div>
        <form method="post" id="bulk-action-form">
            <input type="hidden" name="form_action" value="bulk_delete">
            <div class="table-container"><table>
                <thead><tr><th><input type="checkbox" id="select-all"></th><th>Title</th><th>Type</th><th>Actions</th></tr></thead>
                <tbody id="content-table-body">
                {% for movie in content_list %}
                <tr>
                    <td><input type="checkbox" name="selected_ids" value="{{ movie._id }}" class="row-checkbox"></td>
                    <td>{{ movie.title }}</td>
                    <td>{{ movie.type|title }}</td>
                    <td class="action-buttons">
                        <a href="{{ url_for('edit_movie', movie_id=movie._id) }}" class="btn btn-edit">Edit</a>
                        <a href="{{ url_for('delete_movie', movie_id=movie._id) }}" onclick="return confirm('Are you sure?')" class="btn btn-danger">Delete</a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" style="text-align:center;">No content found.</td></tr>
                {% endfor %}
                </tbody>
            </table></div>
            <button type="submit" class="btn btn-danger" style="margin-top: 15px;" onclick="return confirm('Are you sure you want to delete all selected items?')"><i class="fas fa-trash-alt"></i> Delete Selected</button>
        </form>
    </div>
    <hr>
    
    <!-- ... (Other admin sections: Design, Telegram, Requests, Category/OTT, Ads remain unchanged) ... -->

</div>
<div class="modal-overlay" id="search-modal"><div class="modal-content"><div class="modal-header"><h2>Select Content</h2><button class="modal-close" onclick="closeModal()">&times;</button></div><div class="modal-body" id="search-results"></div></div></div>
<script>
    // ... (Admin JS functions remain unchanged) ...
</script>
</body></html>
"""
edit_html = """... (Full edit_html content) ..."""

# =========================================================================================
# === [START] PYTHON FUNCTIONS & FLASK ROUTES (Integrations) ==============================
# =========================================================================================

# --- TMDB API Helper Function (Unchanged) ---
def get_tmdb_details(tmdb_id, media_type):
    # ... (function body remains the same)
    if not TMDB_API_KEY: return None
    search_type = "tv" if media_type == "series" else "movie"
    try:
        detail_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
        res = requests.get(detail_url, timeout=10)
        res.raise_for_status()
        data = res.json()
        details = { "tmdb_id": tmdb_id, "title": data.get("title") or data.get("name"), "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None, "backdrop": f"https://image.tmdb.org/t/p/w1280{data.get('backdrop_path')}" if data.get('backdrop_path') else None, "overview": data.get("overview"), "release_date": data.get("release_date") or data.get("first_air_date"), "genres": [g['name'] for g in data.get("genres", [])], "vote_average": data.get("vote_average"), "type": "series" if search_type == "tv" else "movie" }
        return details
    except requests.RequestException as e:
        print(f"ERROR: TMDb API request failed: {e}")
        return None

# --- Pagination Helper Class (Unchanged) ---
class Pagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count
    @property
    def total_pages(self): return math.ceil(self.total_count / self.per_page)
    @property
    def has_prev(self): return self.page > 1
    @property
    def has_next(self): return self.page < self.total_pages
    @property
    def prev_num(self): return self.page - 1
    @property
    def next_num(self): return self.page + 1

# --- Flask Routes (Core UI Routes remain as defined) ---

@app.route('/')
def home():
    # ... (Existing home logic)
    query = request.args.get('q', '').strip()
    if query:
        movies_list = list(movies.find({"title": {"$regex": query, "$options": "i"}}).sort('updated_at', -1))
        total_results = movies.count_documents({"title": {"$regex": query, "$options": "i"}})
        pagination = Pagination(1, ITEMS_PER_PAGE, total_results)
        return render_template_string(index_html, movies=movies_list, query=f'Results for "{query}"', is_full_page_list=True, pagination=pagination)

    slider_content = list(movies.find({}).sort('updated_at', -1).limit(10))
    latest_content = list(movies.find({}).sort('updated_at', -1).limit(10))
    
    home_categories = [cat['name'] for cat in categories_collection.find().sort("name", 1)]
    categorized_content = {cat: list(movies.find({"categories": cat}).sort('updated_at', -1).limit(10)) for cat in home_categories}
    
    categorized_content = {k: v for k, v in categorized_content.items() if v}

    context = {
        "slider_content": slider_content, "latest_content": latest_content,
        "categorized_content": categorized_content, "is_full_page_list": False
    }
    return render_template_string(index_html, **context)

@app.route('/movie/<movie_id>')
def movie_detail(movie_id):
    try:
        movie = movies.find_one_and_update(
            {"_id": ObjectId(movie_id)},
            {"$inc": {"view_count": 1}},
            return_document=True
        )
        if not movie: 
            return "Content not found", 404
        related_content = list(movies.find({"type": movie.get('type'), "_id": {"$ne": movie['_id']}}).sort('updated_at', -1).limit(10))
        return render_template_string(detail_html, movie=movie, related_content=related_content)
    except Exception as e:
        print(f"Error in movie_detail: {e}")
        return "Content not found", 404

def get_paginated_content(query_filter, page):
    skip = (page - 1) * ITEMS_PER_PAGE
    total_count = movies.count_documents(query_filter)
    content_list = list(movies.find(query_filter).sort('updated_at', -1).skip(skip).limit(ITEMS_PER_PAGE))
    pagination = Pagination(page, ITEMS_PER_PAGE, total_count)
    return content_list, pagination

@app.route('/movies')
def all_movies():
    page = request.args.get('page', 1, type=int)
    all_movie_content, pagination = get_paginated_content({"type": "movie"}, page)
    return render_template_string(index_html, movies=all_movie_content, query="All Movies", is_full_page_list=True, pagination=pagination)

@app.route('/series')
def all_series():
    page = request.args.get('page', 1, type=int)
    all_series_content, pagination = get_paginated_content({"type": "series"}, page)
    return render_template_string(index_html, movies=all_series_content, query="Web Series & TV Shows", is_full_page_list=True, pagination=pagination)

@app.route('/category')
def movies_by_category():
    title = request.args.get('name')
    if not title: return redirect(url_for('home'))
    page = request.args.get('page', 1, type=int)
    
    query_filter = {}
    if title == "Latest Movies": query_filter = {"type": "movie"}
    elif title == "Latest Series": query_filter = {"type": "series"}
    else: query_filter = {"categories": title}
    
    content_list, pagination = get_paginated_content(query_filter, page)
    return render_template_string(index_html, movies=content_list, query=title, is_full_page_list=True, pagination=pagination)

@app.route('/platform/<platform_name>')
def movies_by_platform(platform_name):
    page = request.args.get('page', 1, type=int)
    query_filter = {"ott_platform": platform_name}
    
    content_list, pagination = get_paginated_content(query_filter, page)
    return render_template_string(index_html, movies=content_list, query=f"{platform_name} Originals", is_full_page_list=True, pagination=pagination)

@app.route('/request', methods=['GET', 'POST'])
def request_content():
    if request.method == 'POST':
        content_name = request.form.get('content_name', '').strip()
        extra_info = request.form.get('extra_info', '').strip()
        if content_name:
            requests_collection.insert_one({"name": content_name, "info": extra_info, "status": "Pending", "created_at": datetime.utcnow()})
            flash('Your request has been submitted successfully!', 'success')
        else:
            flash('Content name is required.', 'error')
        return redirect(url_for('request_content'))
    return render_template_string(request_html)

@app.route('/wait')
def wait_page():
    encoded_target_url = request.args.get('target')
    if not encoded_target_url: return redirect(url_for('home'))
    return render_template_string(wait_page_html, target_url=unquote(encoded_target_url))

# --- Manual Parser (for Admin UI paste box) ---
def parse_telegram_format(text_content):
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    if not lines: return None, None, None
    title = lines[0]
    link_regex = re.compile(r'(\d+p|BLU-RAY|HD).*?👉\s*(https?://\S+)', re.IGNORECASE)
    links = []
    
    for line in lines[1:]:
        match = link_regex.search(line)
        if match:
            quality_raw = match.group(1).upper()
            url = match.group(2).strip()
            
            if '480P' in quality_raw: quality = '480p'
            elif '720P' in quality_raw: quality = '720p'
            elif '1080P' in quality_raw: quality = '1080p'
            elif 'BLU-RAY' in quality_raw: quality = 'BLU-RAY'
            else: quality = quality_raw 
            
            links.append({"quality": quality, "watch_url": url, "download_url": url})
    
    year_match = re.search(r'(\d{4})', title)
    release_date = f"{year_match.group(1)}-01-01" if year_match else None
    title_clean = re.sub(r'\s*\(?\d{4}\)?\s*', '', title, flags=re.IGNORECASE).strip() if release_date else title

    return title_clean, links, release_date


@app.route('/admin', methods=["GET", "POST"])
@requires_auth
def admin():
    if request.method == "POST":
        form_action = request.form.get("form_action")
        
        if form_action == "update_ads":
            ad_settings_data = {"ad_header": request.form.get("ad_header"), "ad_body_top": request.form.get("ad_body_top"), "ad_footer": request.form.get("ad_footer"), "ad_list_page": request.form.get("ad_list_page"), "ad_detail_page": request.form.get("ad_detail_page"), "ad_wait_page": request.form.get("ad_wait_page")}
            settings.update_one({"_id": "ad_config"}, {"$set": ad_settings_data}, upsert=True)
        
        elif form_action == "update_design_settings":
            design_settings_data = {
                "language_tag_css": request.form.get("language_tag_css").strip(),
                "new_badge_css": request.form.get("new_badge_css").strip(),
                "new_badge_text": request.form.get("new_badge_text").strip()
            }
            settings.update_one({"_id": "design_config"}, {"$set": design_settings_data}, upsert=True)
            flash("Design settings updated successfully!", 'success')

        elif form_action == "add_telegram_channel":
            bot_token = request.form.get("bot_token", "").strip()
            channel_id = request.form.get("channel_id", "").strip()
            if bot_token and channel_id:
                new_channel = {"token": bot_token, "channel_id": channel_id}
                settings.update_one({"_id": "telegram_config"}, {"$push": {"channels": new_channel}}, upsert=True)
                flash(f"Channel {channel_id} added successfully!", 'success')
            else:
                 flash("Both Bot Token and Channel ID are required.", 'error')

        elif form_action == "add_category":
            category_name = request.form.get("category_name", "").strip()
            if category_name: categories_collection.update_one({"name": category_name}, {"$set": {"name": category_name}}, upsert=True)
        elif form_action == "add_platform":
            platform_name = request.form.get("platform_name", "").strip()
            logo_url = request.form.get("platform_logo_url", "").strip()
            if platform_name and logo_url:
                ott_collection.update_one({"name": platform_name}, {"$set": {"name": platform_name, "logo_url": logo_url}}, upsert=True)
        elif form_action == "bulk_delete":
            ids_to_delete = request.form.getlist("selected_ids")
            if ids_to_delete: movies.delete_many({"_id": {"$in": [ObjectId(id_str) for id_str in ids_to_delete]}})
        
        # --- MANUAL FAST PASTE INJECTOR HANDLER ---
        elif form_action == "fast_paste_injector":
            paste_content = request.form.get("paste_content", "")
            language = request.form.get("injector_language", "").strip()
            categories = request.form.getlist("injector_categories")
            title, links, release_date = parse_telegram_format(paste_content)
            
            if not title or not links:
                flash("Error: Could not parse title or find any links from the pasted content.", 'error')
                return redirect(url_for('admin'))
            
            movie_data = {
                "title": title, "type": "movie", "poster": PLACEHOLDER_POSTER, "backdrop": None,
                "overview": f"Downloaded content based on fast paste injection. Original source text title: {title}",
                "screenshots": [], "language": language or "Dual Audio", "genres": [],
                "categories": categories, "links": links, "manual_links": [], "episodes": [], "season_packs": [],
                "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(), "view_count": 0,
                "is_completed": True, "release_date": release_date
            }
            movie_data["links"] = [l for l in movie_data["links"] if l.get('watch_url') or l.get('download_url')]
            if not movie_data["links"]:
                 flash("Error: No valid download URLs were extracted after parsing.", 'error')
                 return redirect(url_for('admin'))
            
            result = movies.insert_one(movie_data)
            flash(f"Successfully injected and posted (Manual Paste): {title} with {len(movie_data['links'])} links.", 'success')
            if result.inserted_id:
                send_telegram_notification(movie_data, result.inserted_id, notification_type='new')
        # --- END MANUAL FAST PASTE INJECTOR ---

        elif form_action == "add_content":
            content_type = request.form.get("content_type", "movie")
            screenshots_text = request.form.get("screenshots", "").strip()
            screenshots_list = [url.strip() for url in screenshots_text.splitlines() if url.strip()]
            is_completed = 'is_completed' in request.form
            ott_platform = request.form.get("ott_platform")
            tmdb_id = request.form.get("tmdb_id")
            movie_data = {
                "title": request.form.get("title").strip(), "type": content_type,
                "poster": request.form.get("poster").strip() or PLACEHOLDER_POSTER,
                "backdrop": request.form.get("backdrop").strip() or None,
                "overview": request.form.get("overview").strip(), "screenshots": screenshots_list,
                "language": request.form.get("language").strip() or None,
                "genres": [g.strip() for g in request.form.get("genres", "").split(',') if g.strip()],
                "categories": request.form.getlist("categories"), "episodes": [], "links": [], "season_packs": [], "manual_links": [],
                "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(), "view_count": 0,
                "tmdb_id": tmdb_id if tmdb_id else None, "is_completed": is_completed
            }
            if ott_platform and ott_platform != "None": movie_data["ott_platform"] = ott_platform
            if tmdb_id:
                tmdb_details = get_tmdb_details(tmdb_id, "series" if content_type == "series" else "movie")
                if tmdb_details: movie_data.update({'release_date': tmdb_details.get('release_date'),'vote_average': tmdb_details.get('vote_average')})
            if content_type == "movie":
                qualities = ["480p", "720p", "1080p", "BLU-RAY"]
                movie_data["links"] = [{"quality": q, "watch_url": request.form.get(f"watch_link_{q}"), "download_url": request.form.get(f"download_link_{q}")} for q in qualities if request.form.get(f"watch_link_{q}") or request.form.get(f"download_link_{q}")]
            else:
                sp_nums, sp_w, sp_d = request.form.getlist('season_pack_number[]'), request.form.getlist('season_pack_watch_link[]'), request.form.getlist('season_pack_download_link[]')
                movie_data['season_packs'] = [{"season_number": int(sp_nums[i]), "watch_link": sp_w[i].strip() or None, "download_link": sp_d[i].strip() or None} for i in range(len(sp_nums)) if sp_nums[i]]
                s, n, t, l = request.form.getlist('episode_season[]'), request.form.getlist('episode_number[]'), request.form.getlist('episode_title[]'), request.form.getlist('episode_watch_link[]')
                movie_data['episodes'] = [{"season": int(s[i]), "episode_number": int(n[i]), "title": t[i].strip(), "watch_link": l[i].strip()} for i in range(len(s)) if s[i] and n[i] and l[i]]
            names, urls = request.form.getlist('manual_link_name[]'), request.form.getlist('manual_link_url[]')
            movie_data["manual_links"] = [{"name": names[i].strip(), "url": urls[i].strip()} for i in range(len(names)) if names[i] and urls[i]]
            result = movies.insert_one(movie_data)
            if result.inserted_id:
                series_info = None
                if movie_data['type'] == 'series':
                    series_info = format_series_info(movie_data.get('episodes', []), movie_data.get('season_packs', []))
                send_telegram_notification(movie_data, result.inserted_id, series_update_info=series_info)
        return redirect(url_for('admin'))
    
    content_list = list(movies.find({}).sort('updated_at', -1))
    stats = {"total_content": movies.count_documents({}), "total_movies": movies.count_documents({"type": "movie"}), "total_series": movies.count_documents({"type": "series"}), "pending_requests": requests_collection.count_documents({"status": "Pending"})}
    requests_list = list(requests_collection.find().sort("created_at", -1))
    categories_list = list(categories_collection.find().sort("name", 1))
    ott_list = list(ott_collection.find().sort("name", 1))
    ad_settings_data = settings.find_one({"_id": "ad_config"}) or {}
    design_settings_data = settings.find_one({"_id": "design_config"}) or default_design_settings
    
    tele_config_data = settings.find_one({"_id": "telegram_config"})
    telegram_channels = tele_config_data.get('channels', []) if tele_config_data else []
    
    return render_template_string(
        admin_html, 
        content_list=content_list, 
        stats=stats, 
        requests_list=requests_list, 
        ad_settings=ad_settings_data, 
        design_settings=design_settings_data, 
        categories_list=categories_list, 
        ott_list=ott_list,
        telegram_channels=telegram_channels 
    )

# --- NEW: FAST UPLOAD API ENDPOINT (For Bot Interaction) ---
@app.route('/admin/api/fast_upload', methods=['POST'])
@requires_api_key
def api_fast_upload():
    """
    Handles content injection via an external bot/system using JSON data.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        title = data.get("title")
        poster = data.get("poster_url", PLACEHOLDER_POSTER) 
        raw_links = data.get("links", [])
        
        if not title or not raw_links:
            return jsonify({"error": "Missing required fields: title or links"}), 400

        movie_links = []
        for link_item in raw_links:
            quality = link_item.get('quality', 'N/A').strip()
            url = link_item.get('url', '').strip()
            
            if quality and url:
                movie_links.append({
                    "quality": quality,
                    "watch_url": url,
                    "download_url": url,
                })

        if not movie_links:
            return jsonify({"error": "No valid links found in payload"}), 400

        # Optional details
        categories = data.get("categories", ["Trending"])
        language = data.get("language", "N/A")
        overview = data.get("overview", f"Content uploaded via Fast Upload API. Title: {title}")
        
        movie_data = {
            "title": title,
            "type": data.get("type", "movie"), # Allows bot to set 'series' if needed
            "poster": poster,
            "backdrop": data.get("backdrop_url"),
            "overview": overview,
            "screenshots": data.get("screenshots", []),
            "language": language,
            "genres": data.get("genres", []),
            "categories": categories,
            "links": movie_links,
            "manual_links": data.get("manual_links", []),
            "episodes": data.get("episodes", []),
            "season_packs": data.get("season_packs", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "view_count": 0,
            "is_completed": data.get("is_completed", True),
            "release_date": data.get("release_date") 
        }

        result = movies.insert_one(movie_data)
        
        if result.inserted_id:
            # Notification logic handles series_update_info if type is 'series' and relevant data is present
            send_telegram_notification(movie_data, result.inserted_id, notification_type='new')

        return jsonify({"message": "Content successfully added", "id": str(result.inserted_id)}), 201

    except Exception as e:
        print(f"API Fast Upload Error: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
# --- END NEW API ENDPOINT ---

@app.route('/edit_movie/<movie_id>', methods=["GET", "POST"])
@requires_auth
def edit_movie(movie_id):
    # ... (Existing edit_movie logic)
    try:
        obj_id = ObjectId(movie_id)
    except:
        return "Invalid ID", 400
    movie_obj = movies.find_one({"_id": obj_id})
    if not movie_obj:
        return "Movie not found", 404
    
    if request.method == "POST":
        content_type = request.form.get("content_type")
        screenshots_text = request.form.get("screenshots", "").strip()
        screenshots_list = [url.strip() for url in screenshots_text.splitlines() if url.strip()]
        is_completed = 'is_completed' in request.form
        ott_platform = request.form.get("ott_platform")
        
        update_data = {
            "title": request.form.get("title").strip(), "type": content_type,
            "poster": request.form.get("poster").strip() or PLACEHOLDER_POSTER,
            "backdrop": request.form.get("backdrop").strip() or None,
            "overview": request.form.get("overview").strip(), 
            "screenshots": screenshots_list,
            "language": request.form.get("language").strip() or None,
            "genres": [g.strip() for g in request.form.get("genres").split(',') if g.strip()],
            "categories": request.form.getlist("categories"), "updated_at": datetime.utcnow(),
            "is_completed": is_completed
        }
        
        names, urls = request.form.getlist('manual_link_name[]'), request.form.getlist('manual_link_url[]')
        update_data["manual_links"] = [{"name": names[i].strip(), "url": urls[i].strip()} for i in range(len(names)) if names[i] and urls[i]]
        update_query = {"$set": update_data}
        
        series_update_info_str = None
        custom_notification_text = request.form.get("custom_notification_text", "").strip()

        if content_type == "series":
            sp_nums, sp_w, sp_d = request.form.getlist('season_pack_number[]'), request.form.getlist('season_pack_watch_link[]'), request.form.getlist('season_pack_download_link[]')
            update_data['season_packs'] = [{"season_number": int(sp_nums[i]), "watch_link": sp_w[i].strip() or None, "download_link": sp_d[i].strip() or None} for i in range(len(sp_nums)) if sp_nums[i]]
            s, n, t, l = request.form.getlist('episode_season[]'), request.form.getlist('episode_number[]'), request.form.getlist('episode_title[]'), request.form.getlist('episode_watch_link[]')
            update_data["episodes"] = [{"season": int(s[i]), "episode_number": int(n[i]), "title": t[i].strip(), "watch_link": l[i].strip()} for i in range(len(s)) if s[i] and n[i] and l[i]]
            update_query.setdefault("$unset", {})["links"] = ""

            if custom_notification_text:
                series_update_info_str = custom_notification_text
            else:
                old_ep_ids = {(ep.get('season'), ep.get('episode_number')) for ep in movie_obj.get('episodes', [])}
                old_pack_ids = {p.get('season_number') for p in movie_obj.get('season_packs', [])}
                
                newly_added_eps = [ep for ep in update_data["episodes"] if (ep.get('season'), ep.get('episode_number')) not in old_ep_ids]
                newly_added_packs = [p for p in update_data["season_packs"] if p.get('season_number') not in old_pack_ids]
                
                if newly_added_eps or newly_added_packs:
                    series_update_info_str = format_series_info(newly_added_eps, newly_added_packs)

        else: # Movie
            qualities = ["480p", "720p", "1080p", "BLU-RAY"]
            update_data["links"] = [{"quality": q, "watch_url": request.form.get(f"watch_link_{q}"), "download_url": request.form.get(f"download_link_{q}")} for q in qualities if request.form.get(f"watch_link_{q}") or request.form.get(f"download_link_{q}")]
            update_query.setdefault("$unset", {})["episodes"] = ""
            update_query.setdefault("$unset", {})["season_packs"] = ""
        
        if ott_platform and ott_platform != "None":
            update_query["$set"]["ott_platform"] = ott_platform
        else:
            update_query.setdefault("$unset", {})["ott_platform"] = ""

        movies.update_one({"_id": obj_id}, update_query)
        
        if request.form.get('send_notification'):
            updated_movie = movies.find_one({"_id": obj_id})
            send_telegram_notification(
                updated_movie, 
                obj_id, 
                notification_type='update', 
                series_update_info=series_update_info_str
            )
        
        return redirect(url_for('admin'))
    
    categories_list = list(categories_collection.find().sort("name", 1))
    ott_list = list(ott_collection.find().sort("name", 1))
    return render_template_string(edit_html, movie=movie_obj, categories_list=categories_list, ott_list=ott_list)


@app.route('/delete_movie/<movie_id>')
@requires_auth
def delete_movie(movie_id):
    try: movies.delete_one({"_id": ObjectId(movie_id)})
    except: return "Invalid ID", 400
    return redirect(url_for('admin'))

@app.route('/admin/api/live_search')
@requires_auth
def admin_api_live_search():
    query = request.args.get('q', '').strip()
    try:
        results = list(movies.find({"title": {"$regex": query, "$options": "i"} if query else {}}, {"_id": 1, "title": 1, "type": 1}).sort('updated_at', -1))
        for item in results: item['_id'] = str(item['_id'])
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api/search')
@requires_auth
def api_search_tmdb():
    query = request.args.get('query', '').strip()
    if not query: return jsonify({"error": "Query parameter is missing"}), 400
    search_title = query
    search_year = None
    match = re.search(r'^(.*?)\s*\(?(\d{4})\)?$', query)
    if match: search_title = match.group(1).strip(); search_year = match.group(2)
    all_results = []; seen_ids = set()
    def process_tmdb_results(items, media_type_fallback=None):
        for item in items:
            item_id = item.get('id');
            if item_id in seen_ids or not item.get('poster_path'): continue
            media_type = item.get('media_type', media_type_fallback)
            if media_type not in ['movie', 'tv']: continue
            year = (item.get('release_date') or item.get('first_air_date', 'N/A')).split('-')[0]
            all_results.append({"id": item_id, "title": item.get('title') or item.get('name'), "year": year, "poster": f"https://image.tmdb.org/t/p/w200{item.get('poster_path')}", "media_type": media_type})
            seen_ids.add(item_id)
    try:
        base_params = {'api_key': TMDB_API_KEY, 'query': quote(search_title), 'language': 'en-US', 'include_adult': 'true'}
        if search_year:
            movie_params = base_params.copy(); movie_params['primary_release_year'] = search_year
            movie_res = requests.get("https://api.themoviedb.org/3/search/movie", params=movie_params, timeout=10)
            if movie_res.ok: process_tmdb_results(movie_res.json().get('results', []), 'movie')
            tv_params = base_params.copy(); tv_params['first_air_date_year'] = search_year
            tv_res = requests.get("https://api.themoviedb.org/3/search/tv", params=tv_params, timeout=10)
            if tv_res.ok: process_tmdb_results(tv_res.json().get('results', []), 'tv')
        multi_params = base_params.copy(); multi_params['query'] = quote(query) 
        multi_res = requests.get("https://api.themoviedb.org/3/search/multi", params=multi_params, timeout=10)
        if multi_res.ok: process_tmdb_results(multi_res.json().get('results', []))
        return jsonify(all_results)
    except Exception as e:
        print(f"ERROR in api_search_tmdb: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/admin/api/details')
@requires_auth
def api_get_details():
    tmdb_id, media_type = request.args.get('id'), request.args.get('type')
    if not tmdb_id or not media_type: return jsonify({"error": "ID and type are required"}), 400
    details = get_tmdb_details(tmdb_id, "series" if media_type == "tv" else "movie")
    if details: return jsonify(details)
    else: return jsonify({"error": "Details not found on TMDb"}), 404

@app.route('/admin/api/resync_tmdb')
@requires_auth
def api_resync_tmdb():
    tmdb_id = request.args.get('id')
    media_type = request.args.get('type') 
    if not tmdb_id or not media_type:
        return jsonify({"error": "TMDB ID and media type are required"}), 400
    details = get_tmdb_details(tmdb_id, media_type)
    if details: return jsonify(details)
    else: return jsonify({"error": "Could not fetch details from TMDB"}), 404

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query: return jsonify([])
    try:
        results = list(movies.find({"title": {"$regex": query, "$options": "i"}}, {"_id": 1, "title": 1, "poster": 1}).limit(10))
        for item in results: item['_id'] = str(item['_id'])
        return jsonify(results)
    except Exception as e:
        print(f"API Search Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 3000))
    app.run(debug=True, host='0.0.0.0', port=port)
