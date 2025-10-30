# app.py - FINAL, APP-LIKE VERSION
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_super_secret_key_12345")

# --- MongoDB Configuration ---
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb+srv://Demo270:Demo270@cluster0.ls1igsg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client.cinehub_db
movies_collection = db.movies

# --- TMDb API Configuration ---
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "7dc544d9253bccc3cfecc1c677f69819")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"

# --- Admin Credentials ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")

# --- HTML Templates ---

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - CineHub</title>
    <!-- সমাধান: Favicon যোগ করা হয়েছে -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Poppins', sans-serif; background-color: #1a1a2e; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
        .header { background-color: rgba(22, 33, 62, 0.8); backdrop-filter: blur(10px); padding: 15px 0; border-bottom: 1px solid #0f3460; position: sticky; top: 0; z-index: 1000; }
        .navbar { display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.8em; font-weight: 700; color: #e94560; text-transform: uppercase; text-decoration: none; }
        .nav-menu { display: flex; list-style: none; }
        .nav-item a { color: #e0e0e0; margin-left: 25px; font-weight: 500; text-decoration: none; transition: color 0.3s; }
        .nav-item a:hover { color: #e94560; }
        .hamburger { display: none; cursor: pointer; }
        .hamburger span { display: block; height: 3px; width: 25px; background-color: #e0e0e0; margin: 5px 0; }
        .btn { display: inline-block; background-color: #e94560; color: #fff; padding: 12px 25px; border-radius: 5px; font-weight: 600; text-decoration: none; transition: background-color 0.3s; border: none; cursor: pointer; }
        .btn:hover { background-color: #c03952; }
        .section-title { font-size: 2em; color: #e94560; margin-bottom: 30px; text-align: center; }
        .flash-message { padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; font-weight: 600; }
        .flash-message.success { background-color: #4CAF50; color: white; }
        .flash-message.error { background-color: #f44336; color: white; }
        
        /* Home Page Styles */
        .hero { position: relative; height: 70vh; background-size: cover; background-position: center; display: flex; align-items: flex-end; padding: 40px; text-align: left; }
        .hero::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to top, rgba(26, 26, 46, 1) 10%, transparent 100%); }
        .hero-content { position: relative; z-index: 1; max-width: 600px; }
        .hero-title { font-size: 3em; margin-bottom: 15px; font-weight: 700; text-shadow: 2px 2px 8px rgba(0,0,0,0.7); }
        .hero-description { font-size: 1.1em; margin-bottom: 30px; max-height: 3.3em; overflow: hidden; }
        .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }
        .movie-card a { text-decoration: none; color: inherit; }
        .movie-card-inner { background-color: #16213e; border-radius: 8px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; }
        .movie-card-inner:hover { transform: translateY(-8px); box-shadow: 0 10px 25px rgba(233, 69, 96, 0.2); }
        .movie-poster { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; }
        .movie-info { padding: 15px; }
        .movie-title { font-size: 1.05em; font-weight: 600; margin-bottom: 5px; height: 2.4em; overflow: hidden; }
        .movie-year { font-size: 0.9em; color: #a0a0a0; }

        /* Movie Details Page Styles - উন্নতি: নতুন পেজের জন্য নতুন স্টাইল */
        .movie-detail-header { position: relative; height: 50vh; background-size: cover; background-position: center; }
        .movie-detail-header::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to top, #1a1a2e 1%, transparent 50%); }
        .movie-detail-content { display: flex; gap: 30px; margin-top: -150px; position: relative; z-index: 2; }
        .movie-detail-poster img { width: 250px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .movie-detail-info h1 { font-size: 2.5em; margin-bottom: 10px; }
        .movie-detail-meta { display: flex; gap: 20px; color: #a0a0a0; margin-bottom: 20px; }
        .movie-detail-actions { margin-top: 30px; display: flex; gap: 15px; }

        /* Admin & Login Page Styles */
        .admin-section { padding: 40px 0; }
        .admin-form { background-color: #16213e; padding: 30px; border-radius: 8px; margin-bottom: 30px; }
        .admin-form label { display: block; margin-bottom: 8px; font-weight: 600; color: #e94560; }
        .admin-form input, .admin-form textarea { width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #0f3460; border-radius: 5px; background-color: #1a1a2e; color: #e0e0e0; font-size: 1em; }
        .admin-form input:focus { border-color: #e94560; outline: none; }
        .admin-movie-list li { background-color: #16213e; padding: 15px; margin-bottom: 10px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        
        @media (max-width: 768px) {
            .nav-menu { display: none; flex-direction: column; position: absolute; top: 65px; left: 0; width: 100%; background-color: #16213e; }
            .nav-menu.active { display: flex; }
            .nav-item { margin: 0; }
            .nav-item a { display: block; padding: 15px 20px; text-align: center; border-bottom: 1px solid #0f3460; }
            .hamburger { display: block; }
            .hero-title { font-size: 2.5em; }
            .movie-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); }
            .movie-detail-content { flex-direction: column; align-items: center; text-align: center; }
            .movie-detail-poster img { width: 200px; }
            .movie-detail-info h1 { font-size: 2em; }
            .movie-detail-actions { justify-content: center; }
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
        <!-- সমাধান: HTML রেন্ডার করার জন্য |safe ফিল্টার ব্যবহার করা হয়েছে -->
        {{ content | safe }}
    </main>
    <footer style="text-align:center; padding: 30px; margin-top: 50px; background-color: #16213e;">&copy; 2024 CineHub. All rights reserved.</footer>
    <script>
        document.getElementById('hamburger-menu')?.addEventListener('click', () => {
            document.querySelector('.nav-menu')?.classList.toggle('active');
        });
    </script>
</body>
</html>
"""

HOME_CONTENT = """
{% set hero_movie = movies[0] if movies else None %}
<section class="hero" style="background-image: url('{{ hero_movie.backdrop if hero_movie and hero_movie.backdrop else 'https://via.placeholder.com/1200x600/0f3460/e0e0e0?text=CineHub' }}');">
    <div class="container">
        <div class="hero-content">
            <h1 class="hero-title">{{ hero_movie.title if hero_movie else 'Welcome to CineHub' }}</h1>
            <p class="hero-description">{{ hero_movie.overview if hero_movie and hero_movie.overview else 'Discover and watch the latest movies.' }}</p>
            {% if hero_movie %}
            <a href="{{ url_for('movie_details', movie_id=hero_movie._id|string) }}" class="btn">View Details</a>
            {% endif %}
        </div>
    </div>
</section>
<section class="movies-section container">
    <h2 class="section-title">Latest Movies</h2>
    <div class="movie-grid">
        {% for movie in movies %}
        <div class="movie-card">
            <!-- উন্নতি: এখন কার্ডে ক্লিক করলে মুভির ডিটেইলস পেজে যাবে -->
            <a href="{{ url_for('movie_details', movie_id=movie._id|string) }}">
                <div class="movie-card-inner">
                    <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster" class="movie-poster">
                    <div class="movie-info">
                        <h3 class="movie-title">{{ movie.title }}</h3>
                        <p class="movie-year">{{ movie.year }}</p>
                    </div>
                </div>
            </a>
        </div>
        {% endfor %}
    </div>
</section>
"""

# উন্নতি: নতুন মুভি ডিটেইলস পেজের টেমপ্লেট
MOVIE_DETAILS_CONTENT = """
<div class="movie-detail-header" style="background-image: url('{{ movie.backdrop }}')"></div>
<div class="container">
    <div class="movie-detail-content">
        <div class="movie-detail-poster">
            <img src="{{ movie.poster }}" alt="{{ movie.title }} Poster">
        </div>
        <div class="movie-detail-info">
            <h1>{{ movie.title }}</h1>
            <div class="movie-detail-meta">
                <span>{{ movie.year }}</span>
                <span>&bull;</span>
                <span>{{ movie.genre }}</span>
            </div>
            <p class="movie-detail-overview">{{ movie.overview }}</p>
            <div class="movie-detail-actions">
                <a href="{{ movie.trailer_link or '#' }}" target="_blank" class="btn">Watch Trailer</a>
                <a href="{{ movie.download_link or '#' }}" target="_blank" class="btn" style="background-color: #0f3460;">Download</a>
            </div>
        </div>
    </div>
</div>
"""

LOGIN_PAGE_CONTENT = """
<div class="container admin-section">
    <div style="max-width: 400px; margin: 40px auto;">
        <div class="admin-form">
            <h2 class="section-title" style="margin-bottom: 20px;">Admin Login</h2>
            <form method="POST" action="{{ url_for('login_page') }}">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <button type="submit" class="btn" style="width: 100%;">Login</button>
            </form>
        </div>
    </div>
</div>
"""

# সমাধান: অ্যাডমিন ড্যাশবোর্ডের সম্পূর্ণ টেমপ্লেট যোগ করা হয়েছে
ADMIN_DASHBOARD_CONTENT = """
<section class="admin-section container">
    <h2 class="section-title">Admin Dashboard</h2>
    <div class="admin-form">
        <h3>Add New Movie</h3>
        <form method="POST" action="{{ url_for('add_movie') }}">
            <label for="title">Movie Title (Search on TMDb):</label>
            <input type="text" id="title" name="title" placeholder="e.g., The Matrix" required>
            <button type="submit" name="action" value="search_add_tmdb" class="btn">Search & Add from TMDb</button>
        </form>
    </div>
    <div class="admin-form">
        <h3>Add Movie Manually</h3>
        <form method="POST" action="{{ url_for('add_movie_manual_save') }}">
            <label>Title:</label><input type="text" name="title" required>
            <label>Year:</label><input type="text" name="year" required>
            <label>Genre:</label><input type="text" name="genre" placeholder="Action, Sci-Fi">
            <label>Poster URL:</label><input type="text" name="poster">
            <label>Trailer URL:</label><input type="text" name="trailer_link">
            <label>Download URL:</label><input type="text" name="download_link">
            <label>Overview:</label><textarea name="overview" rows="4"></textarea>
            <button type="submit" class="btn">Save Manual Movie</button>
        </form>
    </div>
    <div style="margin-top: 40px;">
        <h3 class="section-title">Manage Movies</h3>
        <ul class="admin-movie-list" style="padding: 0;">
            {% for movie in movies %}
            <li>
                <span>{{ movie.title }} ({{ movie.year }})</span>
                <div class="actions">
                    <a href="{{ url_for('edit_movie', movie_id=movie._id|string) }}" style="color: #4CAF50;">Edit</a>
                    <form method="POST" action="{{ url_for('delete_movie', movie_id=movie._id|string) }}" style="display:inline;" onsubmit="return confirm('Are you sure?');">
                        <button type="submit" style="background:none; border:none; color:#e94560; cursor:pointer; font-size: 1em; margin-left:15px;">Delete</button>
                    </form>
                </div>
            </li>
            {% endfor %}
        </ul>
    </div>
</section>
"""

# সমাধান: এডিট পেজের সম্পূর্ণ টেমপ্লেট যোগ করা হয়েছে
EDIT_MOVIE_CONTENT = """
<section class="admin-section container">
    <h2 class="section-title">Edit Movie: {{ movie.title }}</h2>
    <div class="admin-form">
        <form method="POST" action="{{ url_for('update_movie', movie_id=movie._id|string) }}">
            <label>Title:</label><input type="text" name="title" value="{{ movie.title }}" required>
            <label>Year:</label><input type="text" name="year" value="{{ movie.year }}" required>
            <label>Genre:</label><input type="text" name="genre" value="{{ movie.genre or '' }}">
            <label>Poster URL:</label><input type="text" name="poster" value="{{ movie.poster or '' }}">
            <label>Backdrop URL:</label><input type="text" name="backdrop" value="{{ movie.backdrop or '' }}">
            <label>Trailer URL:</label><input type="text" name="trailer_link" value="{{ movie.trailer_link or '' }}">
            <label>Download URL:</label><input type="text" name="download_link" value="{{ movie.download_link or '' }}">
            <label>Overview:</label><textarea name="overview" rows="4">{{ movie.overview or '' }}</textarea>
            <button type="submit" class="btn">Update Movie</button>
            <a href="{{ url_for('admin_dashboard') }}" class="btn" style="background-color: #555; margin-left: 10px;">Cancel</a>
        </form>
    </div>
</section>
"""

# --- Decorator & Routes ---

def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' in session: return f(*args, **kwargs)
        else:
            flash('You need to login first.', 'error')
            return redirect(url_for('login_page'))
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def home():
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="Home", content=render_template_string(HOME_CONTENT, movies=movies))

# উন্নতি: নতুন মুভি ডিটেইলস পেজের জন্য রুট
@app.route('/movie/<movie_id>')
def movie_details(movie_id):
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        if movie:
            return render_template_string(BASE_HTML, title=movie['title'], content=render_template_string(MOVIE_DETAILS_CONTENT, movie=movie))
        abort(404)
    except:
        abort(404)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'logged_in' in session: return redirect(url_for('admin_dashboard'))
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
    movies = list(movies_collection.find().sort("_id", -1))
    return render_template_string(BASE_HTML, title="Admin Dashboard", content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies))

@app.route('/admin/add', methods=['POST'])
@login_required
def add_movie():
    title_query = request.form.get('title')
    try:
        search_url = f"{TMDB_BASE_URL}/search/movie"
        response = requests.get(search_url, params={"api_key": TMDB_API_KEY, "query": title_query})
        response.raise_for_status()
        results = response.json().get('results')
        if not results:
            flash(f'No movie found for "{title_query}".', 'error')
            return redirect(url_for('admin_dashboard'))
        
        movie_id = results[0]['id']
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        details_resp = requests.get(details_url, params={"api_key": TMDB_API_KEY, "append_to_response": "videos"})
        details = details_resp.json()
        
        trailer = next((v['key'] for v in details.get('videos', {}).get('results', []) if v['site'] == 'YouTube' and v['type'] == 'Trailer'), None)
        
        new_movie = {
            "title": details.get('title'),
            "year": int(details.get('release_date', '0000').split('-')[0]),
            "genre": ", ".join([g['name'] for g in details.get('genres', [])]),
            "overview": details.get('overview'),
            "poster": f"{TMDB_IMAGE_BASE_URL}{details['poster_path']}" if details.get('poster_path') else '',
            "backdrop": f"{TMDB_BACKDROP_BASE_URL}{details['backdrop_path']}" if details.get('backdrop_path') else '',
            "trailer_link": f"https://www.youtube.com/watch?v={trailer}" if trailer else '',
        }
        movies_collection.insert_one(new_movie)
        flash(f"Movie '{new_movie['title']}' added successfully!", 'success')
    except Exception as e:
        flash(f'Error adding movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_manual', methods=['POST'])
@login_required
def add_movie_manual_save():
    try:
        new_movie = {key: request.form[key] for key in request.form}
        new_movie['year'] = int(new_movie['year'])
        movies_collection.insert_one(new_movie)
        flash(f"Movie '{new_movie['title']}' added manually!", 'success')
    except Exception as e:
        flash(f'Error adding movie manually: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<movie_id>')
@login_required
def edit_movie(movie_id):
    movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
    if movie:
        return render_template_string(BASE_HTML, title=f"Edit {movie['title']}", content=render_template_string(EDIT_MOVIE_CONTENT, movie=movie))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update/<movie_id>', methods=['POST'])
@login_required
def update_movie(movie_id):
    try:
        updated_data = {key: request.form[key] for key in request.form}
        updated_data['year'] = int(updated_data['year'])
        movies_collection.update_one({"_id": ObjectId(movie_id)}, {"$set": updated_data})
        flash("Movie updated successfully!", 'success')
    except Exception as e:
        flash(f'Error updating movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<movie_id>', methods=['POST'])
@login_required
def delete_movie(movie_id):
    try:
        movies_collection.delete_one({"_id": ObjectId(movie_id)})
        flash("Movie deleted successfully!", 'success')
    except Exception as e:
        flash(f'Error deleting movie: {e}', 'error')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    if movies_collection.count_documents({}) == 0:
        # Adding a default movie for first time run
        add_movie_from_tmdb_title("Avatar")
    app.run(debug=True)
