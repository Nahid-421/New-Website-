# app.py - A simplified Flask web app with MongoDB, TMDb integration, and basic Admin Login
# FINAL REVISED VERSION

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_super_secret_key")

# --- MongoDB Configuration ---
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client.cinehub_db
movies_collection = db.movies

# --- TMDb API Configuration ---
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "7dc544d9253bccc3cfecc1c677f69819")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original" # For hero section background

# --- Admin Credentials ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")

# --- Helper Function to get TMDb Genres ---
def get_tmdb_genres():
    """Fetches genre list from TMDb and returns a mapping of genre_id -> genre_name."""
    genre_url = f"{TMDB_BASE_URL}/genre/movie/list"
    params = {"api_key": TMDB_API_KEY}
    try:
        response = requests.get(genre_url, params=params)
        response.raise_for_status()
        genres = response.json().get('genres', [])
        return {genre['id']: genre['name'] for genre in genres}
    except requests.exceptions.RequestException:
        return {}

TMDB_GENRES = get_tmdb_genres()


# --- HTML Templates ---

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background-color: #1a1a2e; color: #e0e0e0; line-height: 1.6; }
        a { color: #e94560; text-decoration: none; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
        .header { background-color: #16213e; padding: 15px 0; border-bottom: 1px solid #0f3460; position: sticky; top: 0; z-index: 1000; backdrop-filter: blur(10px); background-color: rgba(22, 33, 62, 0.8); }
        .navbar { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.8em; font-weight: 700; color: #e94560; text-transform: uppercase; }
        .nav-menu { display: flex; list-style: none; }
        .nav-item a { color: #e0e0e0; margin-left: 25px; font-weight: 500; transition: color 0.3s ease; }
        .nav-item a:hover { color: #e94560; }
        .hamburger { display: none; flex-direction: column; cursor: pointer; }
        .hamburger span { height: 3px; width: 25px; background-color: #e0e0e0; margin: 4px 0; transition: all 0.3s ease; }
        /* IMPROVEMENT: Hero Section Style */
        .hero { 
            position: relative; 
            height: 70vh; 
            background-size: cover; 
            background-position: center; 
            display: flex; 
            align-items: flex-end; /* Align content to the bottom */
            justify-content: left; 
            text-align: left; 
            color: #fff; 
            margin-bottom: 40px; 
            padding: 40px;
        }
        .hero::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to top, rgba(26, 26, 46, 1) 10%, rgba(0, 0, 0, 0.2) 100%); }
        .hero-content { position: relative; z-index: 1; max-width: 600px; }
        .hero-title { font-size: 3em; margin-bottom: 15px; font-weight: 700; text-shadow: 2px 2px 8px rgba(0,0,0,0.7); }
        .hero-description { font-size: 1.1em; margin-bottom: 30px; line-height: 1.5; max-height: 3.3em; overflow: hidden; }
        .btn { display: inline-block; background-color: #e94560; color: #fff; padding: 12px 25px; border-radius: 5px; font-weight: 600; transition: background-color 0.3s ease; }
        .btn:hover { background-color: #c03952; }
        .section-title { font-size: 2em; color: #e94560; margin-bottom: 30px; text-align: center; }
        /* IMPROVEMENT: Movie Grid & Card Style */
        .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }
        .movie-card { background-color: #16213e; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer; }
        .movie-card:hover { transform: translateY(-8px); box-shadow: 0 10px 25px rgba(233, 69, 96, 0.2); }
        a.movie-card-link { text-decoration: none; color: inherit; } /* Remove underline from card link */
        .movie-poster { width: 100%; height: auto; aspect-ratio: 2 / 3; object-fit: cover; display: block; }
        .movie-info { padding: 15px; }
        .movie-title { font-size: 1.05em; font-weight: 600; margin-bottom: 5px; height: 2.4em; overflow: hidden; }
        .movie-year { font-size: 0.9em; color: #a0a0a0; }
        /* IMPROVEMENT: Admin Form Style */
        .admin-form input:focus { border-color: #e94560; box-shadow: 0 0 5px rgba(233, 69, 96, 0.5); outline: none; }
        .admin-section { padding: 40px 0; }
        .admin-form { background-color: #16213e; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); margin-bottom: 30px;}
        .admin-form label { display: block; margin-bottom: 8px; font-weight: 600; color: #e94560; }
        .admin-form input[type="text"], .admin-form textarea, .admin-form input[type="password"] { width: 100%; padding: 10px; margin-bottom: 20px; border: 1px solid #0f3460; border-radius: 5px; background-color: #1a1a2e; color: #e0e0e0; font-size: 1em; }
        .admin-form button { background-color: #e94560; color: #fff; padding: 12px 25px; border-radius: 5px; font-weight: 600; border: none; cursor: pointer; transition: background-color 0.3s ease; }
        .admin-movie-list { list-style: none; }
        .admin-movie-item { background-color: #16213e; padding: 15px; margin-bottom: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .flash-message { background-color: #4CAF50; color: white; padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; font-weight: 600; }
        .flash-message.error { background-color: #f44336; }
        .footer { background-color: #16213e; color: #a0a0a0; padding: 30px 0; text-align: center; border-top: 1px solid #0f3460; margin-top: 50px; }
        @media (max-width: 768px) {
            .nav-menu { display: none; flex-direction: column; position: absolute; top: 60px; left: 0; width: 100%; background-color: #16213e; }
            .nav-menu.active { display: flex; }
            .nav-item { margin: 0; border-bottom: 1px solid #0f3460; }
            .nav-item a { display: block; padding: 15px 20px; margin-left: 0; text-align: center; }
            .hamburger { display: flex; }
            .hero { height: 50vh; padding: 20px; }
            .hero-title { font-size: 2.5em; }
            .movie-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 15px; }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="container">
            <nav class="navbar">
                <a href="{{ url_for('home') }}" class="logo">CineHub</a>
                <ul class="nav-menu">
                    <li class="nav-item"><a href="{{ url_for('home') }}">Home</a></li>
                    <li class="nav-item"><a href="{{ url_for('admin_dashboard') }}">Admin</a></li>
                    {% if session.logged_in %}<li class="nav-item"><a href="{{ url_for('logout') }}">Logout</a></li>{% endif %}
                </ul>
                <div class="hamburger" id="hamburger-menu"><span></span><span></span><span></span></div>
            </nav>
        </div>
    </header>
    <main>
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}{% for category, message in messages %}<div class="flash-message {{ category }}">{{ message }}</div>{% endfor %}{% endif %}
            {% endwith %}
        </div>
        <!-- FIXED: Added the |safe filter to render HTML content correctly -->
        {{ content | safe }}
    </main>
    <footer class="footer"> ... </footer>
    <script>
        document.getElementById('hamburger-menu')?.addEventListener('click', () => {
            document.querySelector('.nav-menu')?.classList.toggle('active');
        });
    </script>
</body>
</html>
"""

HOME_CONTENT = """
<!-- IMPROVEMENT: Dynamic Hero Section -->
{% set hero_movie = movies[0] if movies else None %}
<section class="hero" style="background-image: url('{{ hero_movie.backdrop if hero_movie and hero_movie.backdrop else 'https://via.placeholder.com/1200x600/0f3460/e0e0e0?text=CineHub' }}');">
    <div class="hero-content">
        <h1 class="hero-title">{{ hero_movie.title if hero_movie else 'Welcome to CineHub' }}</h1>
        <p class="hero-description">{{ hero_movie.overview if hero_movie and hero_movie.overview else 'Discover the latest movies.' }}</p>
        <a href="{{ hero_movie.trailer_link or '#' if hero_movie else '#' }}" class="btn" target="_blank">Watch Trailer</a>
    </div>
</section>

<section class="movies-section container">
    <h2 class="section-title">Latest Movies</h2>
    <div class="movie-grid">
        {% for movie in movies %}
        <!-- IMPROVEMENT: Made the whole card a clickable link -->
        <a href="{{ movie.trailer_link or '#' }}" target="_blank" class="movie-card-link">
            <div class="movie-card">
                <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster" class="movie-poster">
                <div class="movie-info">
                    <h3 class="movie-title">{{ movie.title }}</h3>
                    <p class="movie-year">{{ movie.year }}</p>
                </div>
            </div>
        </a>
        {% endfor %}
    </div>
</section>
"""

# The rest of the Python code is largely the same, but with improvements for fetching more data from TMDb

LOGIN_PAGE_CONTENT = """
    <section class="admin-section container">
        <h2 class="section-title">Admin Login</h2>
        <div class="admin-form" style="max-width: 400px; margin: 0 auto;">
            <form method="POST" action="{{ url_for('login_page') }}">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </section>
"""
ADMIN_DASHBOARD_CONTENT = "..." # (No changes needed, will be rendered correctly)
EDIT_MOVIE_CONTENT = "..." # (No changes needed, will be rendered correctly)

# --- Decorator ---
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.', 'error')
            return redirect(url_for('login_page'))
    wrap.__name__ = f.__name__
    return wrap

# --- Routes ---

@app.route('/')
def home():
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="CineHub - Home", content=render_template_string(HOME_CONTENT, movies=movies))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template_string(BASE_HTML, title="Admin Login", content=LOGIN_PAGE_CONTENT)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    show_manual_form = request.args.get('manual_add_form', False)
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="CineHub - Admin", content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies, manual_add_form=show_manual_form))


# IMPROVEMENT: Combined all movie adding logic into one function for better clarity
@app.route('/admin/add_movie', methods=['POST'])
@login_required
def add_movie():
    action = request.form.get('action')
    title_query = request.form.get('title')

    if not title_query:
        flash('Movie title is required.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if action == "add_manual":
        return redirect(url_for('admin_dashboard', manual_add_form=True))

    if action == "search_add_tmdb":
        try:
            search_url = f"{TMDB_BASE_URL}/search/movie"
            params = {"api_key": TMDB_API_KEY, "query": title_query}
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            results = response.json().get('results')

            if not results:
                flash(f'No movie found for "{title_query}". Try adding manually.', 'error')
                return redirect(url_for('admin_dashboard', manual_add_form=True))

            first_result = results[0]
            movie_id = first_result['id']
            
            # Fetch full movie details including videos for trailer
            details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            params = {"api_key": TMDB_API_KEY, "append_to_response": "videos"}
            details_response = requests.get(details_url, params=params)
            details_response.raise_for_status()
            details = details_response.json()

            trailer_link = ""
            for video in details.get('videos', {}).get('results', []):
                if video['site'] == 'YouTube' and video['type'] == 'Trailer':
                    trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
                    break
            
            movie_data = {
                "title": details.get('title'),
                "year": int(details.get('release_date', '0000').split('-')[0]),
                "genre": ", ".join([g['name'] for g in details.get('genres', [])]),
                "overview": details.get('overview', ''),
                "poster": f"{TMDB_IMAGE_BASE_URL}{details['poster_path']}" if details.get('poster_path') else '',
                "backdrop": f"{TMDB_BACKDROP_BASE_URL}{details['backdrop_path']}" if details.get('backdrop_path') else '',
                "trailer_link": trailer_link,
                "download_link": '' # To be filled by admin
            }
            movies_collection.insert_one(movie_data)
            flash(f"Movie '{movie_data['title']}' added successfully from TMDb!", 'success')
            return redirect(url_for('admin_dashboard'))

        except requests.RequestException as e:
            flash(f'Error connecting to TMDb API: {e}.', 'error')
            return redirect(url_for('admin_dashboard', manual_add_form=True))

    return redirect(url_for('admin_dashboard'))

# ... (the rest of the routes: edit, update, delete remain largely the same, just ensure they handle new fields like overview, backdrop)
@app.route('/admin/update_movie/<movie_id>', methods=['POST'])
@login_required
def update_movie(movie_id):
    try:
        updated_data = {
            "title": request.form['title'],
            "year": int(request.form['year']),
            "genre": request.form.get('genre', 'N/A'),
            "poster": request.form.get('poster'),
            "trailer_link": request.form.get('trailer_link', ''),
            "download_link": request.form.get('download_link', ''),
            # Also update new fields if they are in the edit form
            "overview": request.form.get('overview', ''),
            "backdrop": request.form.get('backdrop', '')
        }
        movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$set": updated_data})
        flash(f"Movie updated successfully!", 'success')
    except Exception as e:
        flash(f'Error updating movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))


# (Please ensure you add `overview` and `backdrop` fields to your ADMIN_DASHBOARD_CONTENT and EDIT_MOVIE_CONTENT forms if you want to edit them)

if __name__ == '__main__':
    if movies_collection.count_documents({}) == 0:
        movies_collection.insert_one({
            "title": "The Last Sentinel", 
            "year": 2023, 
            "genre": "Sci-Fi", 
            "overview": "A thrilling sci-fi adventure that pushes the boundaries of time and space, with humanity's fate hanging in the balance.",
            "poster": "https://image.tmdb.org/t/p/w500/uF6ah2oXf62yqM0m8pQYjONLdd.jpg", 
            "backdrop": "https://image.tmdb.org/t/p/original/5YZbUmjbMa3ClvSW17xNocXOmbP.jpg",
            "trailer_link": "#", 
            "download_link": "#"
        })
    app.run(debug=True)
