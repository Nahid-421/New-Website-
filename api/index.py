# app.py - A simplified Flask web app with MongoDB, TMDb integration, and basic Admin Login

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId # For handling MongoDB's default _id
import requests # For making HTTP requests to TMDb API
import os # To get environment variables
import json # For debugging/pretty printing API responses

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_super_secret_key") # Change this in production!

# --- TODO 1: MongoDB Connection Configuration ---
# You need to get your MongoDB Atlas Connection String and replace the placeholder.
# For local testing, you can use "mongodb://localhost:27017/"
# On Vercel, set MONGODB_URI as an Environment Variable.
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") 
client = MongoClient(MONGO_URI)
db = client.cinehub_db # Your database name (e.g., cinehub_db)
movies_collection = db.movies # Your collection name (e.g., movies)

# --- TODO 2: TMDb API Configuration ---
# Get your TMDb API Key (v3) and replace the placeholder.
# On Vercel, set TMDB_API_KEY as an Environment Variable.
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "7dc544d9253bccc3cfecc1c677f69819") 
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500" # Base URL for TMDb movie posters

# --- TODO 3: Admin Credentials (For basic login, change in production!) ---
# In a real app, store hashed passwords in a database.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password") # Hashed password recommended for production

# --- HTML Templates (In a real app, these would be separate .html files) ---
# For demonstration, everything is inlined as strings.
# The CSS is included here to keep it in one file as requested.

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        /* Basic Reset & Body Styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background-color: #1a1a2e; color: #e0e0e0; line-height: 1.6; }
        a { color: #e94560; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }

        /* Header */
        .header { background-color: #16213e; padding: 15px 0; border-bottom: 1px solid #0f3460; position: sticky; top: 0; z-index: 1000; }
        .navbar { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.8em; font-weight: 700; color: #e94560; text-transform: uppercase; }
        .nav-menu { display: flex; list-style: none; }
        .nav-item a { color: #e0e0e0; margin-left: 25px; font-weight: 500; transition: color 0.3s ease; }
        .nav-item a:hover { color: #e94560; text-decoration: none; }
        .hamburger { display: none; flex-direction: column; cursor: pointer; font-size: 1.8em; color: #e0e0e0; }
        .hamburger span { height: 3px; width: 25px; background-color: #e0e0e0; margin: 4px 0; transition: all 0.3s ease; }

        /* Hero Section */
        .hero { position: relative; height: 60vh; background-image: url('https://via.placeholder.com/1200x600/0f3460/e0e0e0?text=Featured+Movie+Banner'); background-size: cover; background-position: center; display: flex; align-items: center; justify-content: center; text-align: center; color: #fff; margin-bottom: 40px; }
        .hero::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.6); }
        .hero-content { position: relative; z-index: 1; max-width: 800px; padding: 20px; }
        .hero-title { font-size: 3.5em; margin-bottom: 15px; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .hero-description { font-size: 1.2em; margin-bottom: 30px; line-height: 1.5; }
        .btn { background-color: #e94560; color: #fff; padding: 12px 25px; border-radius: 5px; font-weight: 600; transition: background-color 0.3s ease; }
        .btn:hover { background-color: #c03952; text-decoration: none; }

        /* Section Titles */
        .section-title { font-size: 2em; color: #e94560; margin-bottom: 30px; text-align: center; position: relative; padding-bottom: 10px; }
        .section-title::after { content: ''; position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); width: 80px; height: 3px; background-color: #0f3460; border-radius: 5px; }

        /* Movie Grid */
        .movie-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 25px; margin-bottom: 60px; }
        .movie-card { background-color: #16213e; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .movie-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); }
        .movie-poster { width: 100%; height: 270px; object-fit: cover; display: block; }
        .movie-info { padding: 15px; }
        .movie-title { font-size: 1.1em; font-weight: 600; margin-bottom: 8px; height: 2.2em; overflow: hidden; text-overflow: ellipsis; white-space: normal; }
        .movie-genre, .movie-year { font-size: 0.9em; color: #a0a0a0; margin-bottom: 5px; }

        /* Admin Styles */
        .admin-section { padding: 40px 0; }
        .admin-form { background-color: #16213e; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); margin-bottom: 30px;}
        .admin-form label { display: block; margin-bottom: 8px; font-weight: 600; color: #e94560; }
        .admin-form input[type="text"],
        .admin-form textarea,
        .admin-form input[type="password"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #0f3460;
            border-radius: 5px;
            background-color: #1a1a2e;
            color: #e0e0e0;
            font-family: 'Poppins', sans-serif;
            font-size: 1em;
        }
        .admin-form button {
            background-color: #e94560;
            color: #fff;
            padding: 12px 25px;
            border-radius: 5px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .admin-form button:hover { background-color: #c03952; }
        .admin-movie-list { list-style: none; }
        .admin-movie-item {
            background-color: #16213e;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .admin-movie-item span { font-weight: 600; }
        .admin-movie-item .actions a { margin-left: 15px; }
        .admin-movie-item .actions button {
            background: none;
            border: none;
            color: #e94560;
            cursor: pointer;
            font-size: 1em;
            margin-left: 10px;
            transition: color 0.3s ease;
        }
        .admin-movie-item .actions button:hover { color: #c03952; }

        /* Messages */
        .flash-message {
            background-color: #4CAF50; /* Green for success */
            color: white;
            padding: 15px;
            text-align: center;
            border-radius: 5px;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .flash-message.error {
            background-color: #f44336; /* Red for error */
        }
        
        /* Footer */
        .footer { background-color: #16213e; color: #a0a0a0; padding: 30px 0; text-align: center; border-top: 1px solid #0f3460; margin-top: 50px; }
        .footer-links a { color: #a0a0a0; margin: 0 10px; transition: color 0.3s ease; }
        .footer-links a:hover { color: #e94560; text-decoration: none; }
        .social-icons { margin-top: 20px; }
        .social-icons a { font-size: 1.5em; margin: 0 10px; color: #e0e0e0; transition: color 0.3s ease; }
        .social-icons a:hover { color: #e94560; }

        /* Responsive Design */
        @media (max-width: 768px) {
            .nav-menu { display: none; flex-direction: column; position: absolute; top: 60px; left: 0; width: 100%; background-color: #16213e; border-top: 1px solid #0f3460; }
            .nav-menu.active { display: flex; }
            .nav-item { margin: 0; border-bottom: 1px solid #0f3460; }
            .nav-item a { display: block; padding: 15px 20px; margin-left: 0; text-align: center; }
            .hamburger { display: flex; }
            .hero { height: 50vh; }
            .hero-title { font-size: 2.5em; }
            .hero-description { font-size: 1em; }
            .movie-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
        }
        @media (max-width: 480px) {
            .logo { font-size: 1.5em; }
            .hero { height: 40vh; }
            .hero-title { font-size: 2em; }
            .hero-description { font-size: 0.9em; }
            .btn { padding: 10px 20px; font-size: 0.9em; }
            .section-title { font-size: 1.7em; }
            .movie-poster { height: 220px; }
            .movie-title { font-size: 1em; }
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
                    {% if session.logged_in %}
                    <li class="nav-item"><a href="{{ url_for('logout') }}">Logout</a></li>
                    {% endif %}
                </ul>
                <div class="hamburger" id="hamburger-menu">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </nav>
        </div>
    </header>

    <main>
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        {{ content }}
    </main>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2023 CineHub. All rights reserved.</p>
            <div class="footer-links">
                <a href="#">Privacy Policy</a>
                <a href="#">Terms of Service</a>
                <a href="#">DMCA</a>
            </div>
            <div class="social-icons">
                <!-- Replace with actual Font Awesome or simple text icons -->
                <a href="#">FB</a>
                <a href="#">TW</a>
                <a href="#">IG</a>
            </div>
        </div>
    </footer>
    
    <script>
        // Hamburger Menu Toggle
        document.addEventListener('DOMContentLoaded', function() {
            const hamburger = document.getElementById('hamburger-menu');
            const navMenu = document.querySelector('.nav-menu');

            if (hamburger && navMenu) {
                hamburger.addEventListener('click', function() {
                    navMenu.classList.toggle('active');
                    hamburger.classList.toggle('open');
                });
            }
        });
    </script>
</body>
</html>
"""

HOME_CONTENT = """
        <section class="hero">
            <div class="hero-content">
                <h1 class="hero-title">The Last Sentinel</h1>
                <p class="hero-description">A thrilling sci-fi adventure that pushes the boundaries of time and space, with humanity's fate hanging in the balance.</p>
                <a href="#" class="btn">Watch Trailer</a>
            </div>
        </section>

        <section class="movies-section container">
            <h2 class="section-title">Latest Movies</h2>
            <div class="movie-grid">
                {% for movie in movies %}
                <div class="movie-card">
                    <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster" class="movie-poster">
                    <div class="movie-info">
                        <h3 class="movie-title">{{ movie.title }}</h3>
                        <p class="movie-year">{{ movie.year }}</p>
                        <p class="movie-genre">{{ movie.genre }}</p>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
"""

LOGIN_PAGE_CONTENT = """
    <section class="admin-section container">
        <h2 class="section-title">Admin Login</h2>
        <div class="admin-form" style="max-width: 400px; margin: 0 auto;">
            <form method="POST" action="{{ url_for('login') }}">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </section>
"""

ADMIN_DASHBOARD_CONTENT = """
        <section class="admin-section container">
            <h2 class="section-title">Admin Dashboard</h2>

            <h3>Add New Movie</h3>
            <div class="admin-form">
                <form method="POST" action="{{ url_for('add_movie') }}">
                    <label for="title">Movie Title:</label>
                    <input type="text" id="title" name="title" placeholder="Enter movie title to search or add manually" required>

                    <button type="submit" name="action" value="search_add_tmdb">Search & Add from TMDb</button>
                    <button type="submit" name="action" value="add_manual">Add Manually</button>
                </form>
            </div>
            
            {% if movie_search_result %}
            <div class="admin-form" style="margin-top: 20px;">
                <h3>TMDb Search Result: {{ movie_search_result.title }}</h3>
                <form method="POST" action="{{ url_for('add_movie_from_tmdb') }}">
                    <input type="hidden" name="tmdb_id" value="{{ movie_search_result.id }}">
                    
                    <label for="final_title">Title:</label>
                    <input type="text" id="final_title" name="title" value="{{ movie_search_result.title }}" required>

                    <label for="final_year">Year:</label>
                    <input type="text" id="final_year" name="year" value="{{ movie_search_result.year }}" required>

                    <label for="final_genre">Genre:</label>
                    <input type="text" id="final_genre" name="genre" value="{{ movie_search_result.genre }}" placeholder="e.g., Action, Sci-Fi">
                    
                    <label for="final_poster">Poster URL:</label>
                    <input type="text" id="final_poster" name="poster" value="{{ movie_search_result.poster }}" required>

                    <label for="final_trailer_link">Trailer Link (YouTube/Vimeo URL):</label>
                    <input type="text" id="final_trailer_link" name="trailer_link" value="{{ movie_search_result.trailer_link or '' }}">
                    
                    <label for="final_download_link">Download Link (Direct URL):</label>
                    <input type="text" id="final_download_link" name="download_link" placeholder="Enter download link here">

                    <button type="submit">Confirm Add Movie</button>
                </form>
            </div>
            {% elif manual_add_form %}
            <div class="admin-form" style="margin-top: 20px;">
                <h3>Add Movie Manually</h3>
                <form method="POST" action="{{ url_for('add_movie_manual_save') }}">
                    <label for="manual_title">Title:</label>
                    <input type="text" id="manual_title" name="title" required>

                    <label for="manual_year">Year:</label>
                    <input type="text" id="manual_year" name="year" required>

                    <label for="manual_genre">Genre:</label>
                    <input type="text" id="manual_genre" name="genre" placeholder="e.g., Action, Sci-Fi">
                    
                    <label for="manual_poster">Poster URL:</label>
                    <input type="text" id="manual_poster" name="poster" value="https://via.placeholder.com/200x300?text=New+Movie">

                    <label for="manual_trailer_link">Trailer Link (YouTube/Vimeo URL):</label>
                    <input type="text" id="manual_trailer_link" name="trailer_link">
                    
                    <label for="manual_download_link">Download Link (Direct URL):</label>
                    <input type="text" id="manual_download_link" name="download_link">

                    <button type="submit">Save Manual Movie</button>
                </form>
            </div>
            {% endif %}


            <h3 style="margin-top: 40px;">Manage Movies</h3>
            <ul class="admin-movie-list">
                {% for movie in movies %}
                <li class="admin-movie-item">
                    <span>{{ movie.title }} ({{ movie.year }})</span>
                    <div class="actions">
                        <a href="{{ url_for('edit_movie', movie_id=movie._id|string) }}">Edit</a>
                        <form method="POST" action="{{ url_for('delete_movie', movie_id=movie._id|string) }}" style="display:inline;">
                            <button type="submit">Delete</button>
                        </form>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </section>
"""

EDIT_MOVIE_CONTENT = """
        <section class="admin-section container">
            <h2 class="section-title">Edit Movie: {{ movie.title }}</h2>

            <div class="admin-form">
                <form method="POST" action="{{ url_for('update_movie', movie_id=movie._id|string) }}">
                    <label for="title">Title:</label>
                    <input type="text" id="title" name="title" value="{{ movie.title }}" required>

                    <label for="year">Year:</label>
                    <input type="text" id="year" name="year" value="{{ movie.year }}" required>

                    <label for="genre">Genre:</label>
                    <input type="text" id="genre" name="genre" value="{{ movie.genre or '' }}" placeholder="e.g., Action, Sci-Fi">

                    <label for="poster">Poster URL:</label>
                    <input type="text" id="poster" name="poster" value="{{ movie.poster }}" required>

                    <label for="trailer_link">Trailer Link (YouTube/Vimeo URL):</label>
                    <input type="text" id="trailer_link" name="trailer_link" value="{{ movie.trailer_link or '' }}">
                    
                    <label for="download_link">Download Link (Direct URL):</label>
                    <input type="text" id="download_link" name="download_link" value="{{ movie.download_link or '' }}">

                    <button type="submit">Update Movie</button>
                    <a href="{{ url_for('admin_dashboard') }}" class="btn" style="margin-left: 10px;">Cancel</a>
                </form>
            </div>
        </section>
"""

# --- Decorator for Admin Login Required ---
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.', 'error')
            return redirect(url_for('login_page'))
    wrap.__name__ = f.__name__ # Important for Flask to register unique endpoints
    return wrap

# --- Routes ---

@app.route('/')
def home():
    movies = list(movies_collection.find().sort("year", -1)) # Fetch all movies
    return render_template_string(BASE_HTML, title="CineHub - Home", content=render_template_string(HOME_CONTENT, movies=movies))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template_string(BASE_HTML, title="Admin Login", content=LOGIN_PAGE_CONTENT)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    movies = list(movies_collection.find().sort("_id", -1)) # Fetch all movies
    return render_template_string(BASE_HTML, title="CineHub - Admin", content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies))

@app.route('/admin/add_movie', methods=['POST'])
@login_required
def add_movie():
    action = request.form.get('action')
    movie_title_from_form = request.form['title']

    if action == "search_add_tmdb":
        tmdb_search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": movie_title_from_form,
            "language": "en-US" # You can change language here
        }
        
        try:
            tmdb_response = requests.get(tmdb_search_url, params=params)
            tmdb_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            movie_details = tmdb_response.json().get('results')

            if movie_details and len(movie_details) > 0:
                first_result = movie_details[0]
                
                # Try to get genre names from TMDb
                genre_names = []
                genre_ids = first_result.get('genre_ids', [])
                if genre_ids:
                    # In a real app, you'd cache this or make a separate API call for genres
                    # For simplicity, we'll just put IDs here, or leave as placeholder
                    genre_names = [str(gid) for gid in genre_ids] # Just show IDs for now
                
                # Fetching trailer link (requires another API call)
                trailer_link = ""
                if first_result.get('id'):
                    videos_url = f"{TMDB_BASE_URL}/movie/{first_result['id']}/videos"
                    video_params = {"api_key": TMDB_API_KEY, "language": "en-US"}
                    video_response = requests.get(videos_url, params=video_params)
                    video_data = video_response.json().get('results', [])
                    for video in video_data:
                        if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                            trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
                            break
                
                movie_search_result = {
                    "id": first_result.get('id'),
                    "title": first_result.get('title', movie_title_from_form),
                    "year": int(first_result.get('release_date', '0000').split('-')[0]),
                    "genre": ", ".join(genre_names) if genre_names else "Unknown", # Use joined genre names
                    "poster": f"{TMDB_IMAGE_BASE_URL}{first_result['poster_path']}" if first_result.get('poster_path') else 'https://via.placeholder.com/200x300?text=No+Poster',
                    "trailer_link": trailer_link
                }
                
                movies = list(movies_collection.find().sort("_id", -1)) # Reload movie list
                return render_template_string(BASE_HTML, title="CineHub - Admin", 
                                              content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies, movie_search_result=movie_search_result))
            else:
                flash(f'No movie found on TMDb for "{movie_title_from_form}". Try adding manually.', 'error')
                return redirect(url_for('admin_dashboard', manual_add_form=True)) # Redirect with flag for manual form

        except requests.exceptions.RequestException as e:
            flash(f'Error connecting to TMDb API: {e}. Please try again manually.', 'error')
            return redirect(url_for('admin_dashboard', manual_add_form=True))
    
    elif action == "add_manual":
        # Redirect to show the manual add form
        return redirect(url_for('admin_dashboard', manual_add_form=True))
    
    flash('Invalid action.', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_movie_from_tmdb', methods=['POST'])
@login_required
def add_movie_from_tmdb():
    new_movie = {
        "title": request.form['title'],
        "year": int(request.form['year']),
        "genre": request.form.get('genre', 'Unknown'),
        "poster": request.form.get('poster', 'https://via.placeholder.com/200x300?text=New+Movie'),
        "trailer_link": request.form.get('trailer_link', '#'),
        "download_link": request.form.get('download_link', '#')
    }
    movies_collection.insert_one(new_movie)
    flash(f"Movie '{new_movie['title']}' added successfully!", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_movie_manual_save', methods=['POST'])
@login_required
def add_movie_manual_save():
    new_movie = {
        "title": request.form['title'],
        "year": int(request.form['year']),
        "genre": request.form.get('genre', 'Unknown'),
        "poster": request.form.get('poster', 'https://via.placeholder.com/200x300?text=New+Movie'),
        "trailer_link": request.form.get('trailer_link', '#'),
        "download_link": request.form.get('download_link', '#')
    }
    movies_collection.insert_one(new_movie)
    flash(f"Movie '{new_movie['title']}' added manually successfully!", 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_movie/<movie_id>')
@login_required
def edit_movie(movie_id):
    try:
        movie_to_edit = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if movie_to_edit:
            return render_template_string(BASE_HTML, title=f"Edit {movie_to_edit['title']}", content=render_template_string(EDIT_MOVIE_CONTENT, movie=movie_to_edit))
        else:
            flash('Movie not found!', 'error')
    except Exception as e:
        flash(f'Invalid Movie
