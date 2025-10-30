# app.py - FINAL CORRECTED VERSION
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, abort, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import requests
import os
import base64

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a_very_strong_and_unique_secret_key_for_cinehub_final")

# --- Configuration ---
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "7dc544d9253bccc3cfecc1c677f69819")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")

# --- Database Connection ---
client = MongoClient(MONGO_URI)
db = client.cinehub_db
movies_collection = db.movies

# --- TMDb API URLs ---
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"


# --- HTML Templates (Unchanged from previous version) ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - CineHub</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-primary: #0B0C10; --bg-secondary: #1F2833; --text-primary: #C5C6C7; --text-secondary: #66FCF1; --accent: #45A29E; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-primary); color: var(--text-primary); }
        .container { max-width: 1400px; margin: 0 auto; padding: 0 20px; }
        a { color: var(--text-secondary); text-decoration: none; transition: color 0.3s; }
        a:hover { color: var(--accent); }
        .btn { display: inline-block; background: var(--accent); color: #fff; padding: 12px 28px; border-radius: 8px; font-weight: 600; text-decoration: none; border: none; cursor: pointer; transition: background-color 0.3s; }
        .btn:hover { background-color: var(--text-secondary); color: var(--bg-primary); }
        .header { background-color: rgba(11, 12, 16, 0.8); backdrop-filter: blur(10px); padding: 20px 0; position: sticky; top: 0; z-index: 1000; border-bottom: 1px solid var(--bg-secondary); }
        .navbar { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 2em; font-weight: 700; color: var(--text-secondary); }
        .flash-message { padding: 15px; text-align: center; border-radius: 8px; margin: 20px auto; font-weight: 600; max-width: 1200px; }
        .flash-message.success { background-color: #28a745; color: white; }
        .flash-message.error { background-color: #dc3545; color: white; }
        main { padding-top: 40px; }
        .section-title { font-size: 1.8em; font-weight: 600; color: #fff; margin-bottom: 20px; border-left: 4px solid var(--accent); padding-left: 10px; }
        .hero { position: relative; height: 70vh; display: flex; align-items: flex-end; }
        .hero-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: -1; }
        .hero-gradient { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to top, var(--bg-primary) 10%, rgba(11, 12, 16, 0.5) 60%, var(--bg-primary) 100%); }
        .hero-content { max-width: 50%; }
        .hero-title { font-size: 3.5em; font-weight: 700; color: #fff; text-shadow: 2px 2px 10px rgba(0,0,0,0.7); }
        .hero-overview { font-size: 1.1em; margin: 20px 0; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
        .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
        .movie-card { background: var(--bg-secondary); border-radius: 8px; overflow: hidden; transform: scale(1); transition: transform 0.3s, box-shadow 0.3s; }
        .movie-card:hover { transform: scale(1.05); box-shadow: 0 10px 30px rgba(102, 252, 241, 0.2); }
        .movie-poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
        .details-backdrop { height: 60vh; position: relative; }
        .details-content { display: flex; gap: 40px; margin-top: -150px; position: relative; z-index: 2; }
        .details-poster img { width: 280px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
        .details-info h1 { font-size: 3em; font-weight: 700; color: #fff; }
        .details-meta { display: flex; gap: 20px; opacity: 0.8; margin: 15px 0; }
        .details-actions { margin-top: 30px; display: flex; gap: 15px; }
        .form-container { max-width: 500px; margin: 40px auto; background-color: var(--bg-secondary); padding: 40px; border-radius: 12px; }
        .form-container label { display: block; margin-bottom: 8px; font-weight: 600; }
        .form-container input, .form-container textarea { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid var(--accent); border-radius: 8px; background-color: var(--bg-primary); color: var(--text-primary); font-size: 1em; }
        .admin-section { margin-bottom: 40px; }
        .admin-movie-list li { background-color: var(--bg-secondary); padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <header class="header">
        <div class="container navbar">
            <a href="{{ url_for('home') }}" class="logo">CineHub</a>
            <nav>
                <a href="{{ url_for('admin_dashboard') }}" style="font-weight: 600;">Admin Panel</a>
                 {% if session.logged_in %}
                    <a href="{{ url_for('logout') }}" style="margin-left: 20px;">Logout</a>
                {% endif %}
            </nav>
        </div>
    </header>
    <main>
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}{% for category, message in messages %}<div class="flash-message {{ category }}">{{ message }}</div>{% endfor %}{% endif %}
            {% endwith %}
        </div>
        {{ content | safe }}
    </main>
    <footer style="text-align:center; padding: 40px; margin-top: 50px; background-color: var(--bg-secondary);">&copy; 2024 CineHub. All Rights Reserved.</footer>
</body>
</html>
"""

HOME_CONTENT = """
{% set hero_movie = movies[0] if movies else None %}
<section class="hero">
    {% if hero_movie %}
    <img src="{{ hero_movie.backdrop }}" alt="{{ hero_movie.title }} backdrop" class="hero-bg">
    <div class="hero-gradient"></div>
    <div class="container">
        <div class="hero-content">
            <h1 class="hero-title">{{ hero_movie.title }}</h1>
            <p class="hero-overview">{{ hero_movie.overview }}</p>
            <a href="{{ url_for('movie_details', movie_id=hero_movie._id|string) }}" class="btn">View Details</a>
        </div>
    </div>
    {% endif %}
</section>
<div class="container">
    <section class="movie-row" style="margin-top: 40px;">
        <h2 class="section-title">Latest Movies</h2>
        <div class="movie-grid">
            {% for movie in movies %}
            <a href="{{ url_for('movie_details', movie_id=movie._id|string) }}">
                <div class="movie-card">
                    <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster" class="movie-poster">
                </div>
            </a>
            {% endfor %}
        </div>
    </section>
</div>
"""

MOVIE_DETAILS_CONTENT = """
<section class="details-backdrop">
    <img src="{{ movie.backdrop }}" alt="" class="hero-bg">
    <div class="hero-gradient"></div>
</section>
<div class="container">
    <section class="details-content">
        <div class="details-poster">
            <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster">
        </div>
        <div class="details-info">
            <h1>{{ movie.title }}</h1>
            <div class="details-meta">
                <span>{{ movie.year }}</span><span>&bull;</span><span>{{ movie.genre }}</span>
            </div>
            <p>{{ movie.overview }}</p>
            <div class="details-actions">
                <a href="{{ movie.trailer_link or '#' }}" target="_blank" class="btn">Watch Trailer</a>
                <a href="{{ movie.download_link or '#' }}" target="_blank" class="btn" style="background-color: var(--bg-secondary);">Download</a>
            </div>
        </div>
    </section>
</div>
"""

# সমাধান: লগইন ফর্মের action অ্যাট্রিবিউটটি সংশোধন করা হয়েছে
LOGIN_PAGE_CONTENT = """
<div class="form-container">
    <h1 style="text-align: center; margin-bottom: 20px; color: #fff;">Admin Login</h1>
    <form method="POST" action="{{ url_for('login') }}">
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" required>
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required>
        <button type="submit" class="btn" style="width: 100%;">Login</button>
    </form>
</div>
"""

ADMIN_DASHBOARD_CONTENT = """
<div class="container">
    <h1 style="text-align:center; color: #fff; margin-bottom: 40px;">Admin Dashboard</h1>
    <div class="admin-section form-container" style="max-width: 700px;">
        <h2 class="section-title">Add Movie from TMDb</h2>
        <p style="opacity: 0.8; margin-bottom: 20px;">Simply enter a movie title, and we'll fetch all the details for you.</p>
        <form method="POST" action="{{ url_for('add_movie_from_tmdb') }}">
            <label for="title">Movie Title:</label>
            <input type="text" id="title" name="title" placeholder="e.g., Inception" required>
            <button type="submit" class="btn">Search & Add Movie</button>
        </form>
    </div>
    <div class="admin-section">
        <h2 class="section-title">Manage Existing Movies</h2>
        <ul style="list-style: none; padding: 0;">
            {% for movie in movies %}
            <li class="admin-movie-list">
                <span>{{ movie.title }} ({{ movie.year }})</span>
                <div style="display: flex; gap: 15px; align-items: center;">
                    <a href="{{ url_for('edit_movie', movie_id=movie._id|string) }}" style="color: var(--accent);">Edit</a>
                    <form method="POST" action="{{ url_for('delete_movie', movie_id=movie._id|string) }}" onsubmit="return confirm('Are you sure you want to delete this movie?');" style="margin:0;">
                        <button type="submit" style="background:none; border:none; color: #dc3545; cursor:pointer; font-size: 1em; padding:0; font-family: 'Inter', sans-serif;">Delete</button>
                    </form>
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>
</div>
"""

EDIT_MOVIE_CONTENT = """
<div class="container">
    <div class="form-container" style="max-width: 700px;">
        <h2 class="section-title">Edit: {{ movie.title }}</h2>
        <form method="POST" action="{{ url_for('update_movie', movie_id=movie._id|string) }}">
            <label>Title:</label><input type="text" name="title" value="{{ movie.title }}" required>
            <label>Year:</label><input type="text" name="year" value="{{ movie.year }}" required>
            <label>Genre:</label><input type="text" name="genre" value="{{ movie.genre or '' }}">
            <label>Poster URL:</label><input type="text" name="poster" value="{{ movie.poster or '' }}">
            <label>Backdrop URL:</label><input type="text" name="backdrop" value="{{ movie.backdrop or '' }}">
            <label>Trailer URL:</label><input type="text" name="trailer_link" value="{{ movie.trailer_link or '' }}">
            <label>Download URL:</label><input type="text" name="download_link" value="{{ movie.download_link or '' }}">
            <label>Overview:</label><textarea name="overview" rows="5">{{ movie.overview or '' }}</textarea>
            <button type="submit" class="btn">Update Movie</button>
        </form>
    </div>
</div>
"""

# --- Helper Functions & Decorators ---
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session: return f(*args, **kwargs)
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))
    wrap.__name__ = f.__name__
    return wrap

# --- Main App Routes ---
@app.route('/favicon.ico')
def favicon():
    favicon_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
    return Response(base64.b64decode(favicon_b64), mimetype='image/png')

@app.route('/')
def home():
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="Home", content=render_template_string(HOME_CONTENT, movies=movies))

@app.route('/movie/<movie_id>')
def movie_details(movie_id):
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if not movie: abort(404)
        return render_template_string(BASE_HTML, title=movie['title'], content=render_template_string(MOVIE_DETAILS_CONTENT, movie=movie))
    except InvalidId:
        abort(404)

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session: return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials. Please try again.', 'error')
    return render_template_string(BASE_HTML, title="Admin Login", content=LOGIN_PAGE_CONTENT)

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="Admin Dashboard", content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies))

@app.route('/admin/add_tmdb', methods=['POST'])
@login_required
def add_movie_from_tmdb():
    title_query = request.form.get('title')
    try:
        # Search for the movie to get its ID
        search_url = f"{TMDB_BASE_URL}/search/movie"
        response = requests.get(search_url, params={"api_key": TMDB_API_KEY, "query": title_query})
        response.raise_for_status()
        results = response.json().get('results')
        if not results:
            flash(f'Movie not found for "{title_query}".', 'error')
            return redirect(url_for('admin_dashboard'))
        
        movie_id = results[0]['id']

        # Get detailed information using the ID
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=videos"
        details_resp = requests.get(details_url)
        details_resp.raise_for_status()
        details = details_resp.json()
        
        trailer_key = next((v['key'] for v in details.get('videos', {}).get('results', []) if v['site'] == 'YouTube' and v['type'] == 'Trailer'), None)
        
        new_movie = {
            "title": details.get('title'),
            "year": int(details.get('release_date', '0000').split('-')[0]),
            "genre": ", ".join([g['name'] for g in details.get('genres', [])]),
            "overview": details.get('overview'),
            "poster": f"{TMDB_IMAGE_BASE_URL}{details.get('poster_path')}" if details.get('poster_path') else '',
            "backdrop": f"{TMDB_BACKDROP_BASE_URL}{details.get('backdrop_path')}" if details.get('backdrop_path') else '',
            "trailer_link": f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else '',
            "download_link": ""
        }
        movies_collection.insert_one(new_movie)
        flash(f"'{new_movie['title']}' was added successfully!", 'success')
    except requests.exceptions.RequestException as e:
        flash(f'API Error: Could not connect to TMDb. {e}', 'error')
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<movie_id>', methods=['GET'])
@login_required
def edit_movie(movie_id):
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if not movie: abort(404)
        return render_template_string(BASE_HTML, title=f"Edit {movie['title']}", content=render_template_string(EDIT_MOVIE_CONTENT, movie=movie))
    except InvalidId:
        abort(404)

@app.route('/admin/update/<movie_id>', methods=['POST'])
@login_required
def update_movie(movie_id):
    try:
        updated_data = {key: request.form.get(key, '') for key in ['title', 'year', 'genre', 'poster', 'backdrop', 'trailer_link', 'download_link', 'overview']}
        updated_data['year'] = int(updated_data['year'])
        movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$set": updated_data})
        flash(f"'{updated_data['title']}' updated successfully!", 'success')
    except Exception as e:
        flash(f'Error updating movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<movie_id>', methods=['POST'])
@login_required
def delete_movie(movie_id):
    try:
        movies_collection.delete_one({"_id": ObjectId(movie_id)})
        flash("Movie deleted successfully.", 'success')
    except Exception as e:
        flash(f'Error deleting movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # Add a default movie if the database is empty on first run
    if movies_collection.count_documents({}) == 0:
        print("Database is empty. You can add a movie from the admin panel after logging in.")
    app.run(debug=True, port=5000)
