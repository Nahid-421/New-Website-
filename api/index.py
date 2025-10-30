# app.py (or index.py) - A highly simplified Flask web app for demonstration

from flask import Flask, render_template_string, request, redirect, url_for
import json # Used for dummy data storage for demonstration

app = Flask(__name__)

# --- Dummy Database (In a real app, this would be MongoDB or another database) ---
# For demonstration, we'll store movie data in a simple Python list
# In a real app, you'd connect to MongoDB Atlas here.
# Example: from pymongo import MongoClient
#          client = MongoClient("YOUR_MONGODB_CONNECTION_STRING")
#          db = client.cinehub_db
#          movies_collection = db.movies

movies_data = [
    {"id": 1, "title": "The Last Sentinel", "year": 2023, "genre": "Sci-Fi", "poster": "https://via.placeholder.com/200x300/e94560/ffffff?text=Movie+1", "trailer_link": "#", "download_link": "#"},
    {"id": 2, "title": "Neon Samurai", "year": 2022, "genre": "Action", "poster": "https://via.placeholder.com/200x300/0f3460/ffffff?text=Movie+2", "trailer_link": "#", "download_link": "#"},
    {"id": 3, "title": "Cosmic Echoes", "year": 2023, "genre": "Adventure", "poster": "https://via.placeholder.com/200x300/16213e/ffffff?text=Movie+3", "trailer_link": "#", "download_link": "#"},
    # Add more dummy movies here
]
next_movie_id = max([m['id'] for m in movies_data]) + 1 if movies_data else 1

# --- HTML Templates (In a real app, these would be separate .html files in a 'templates' folder) ---
# For demonstration, everything is inlined as strings.

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
        .admin-form textarea {
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
                    <!-- Add more navigation items here -->
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

ADMIN_DASHBOARD_CONTENT = """
        <section class="admin-section container">
            <h2 class="section-title">Admin Dashboard</h2>

            <h3>Add New Movie</h3>
            <div class="admin-form">
                <form method="POST" action="{{ url_for('add_movie') }}">
                    <label for="title">Title:</label>
                    <input type="text" id="title" name="title" required>

                    <label for="year">Year:</label>
                    <input type="text" id="year" name="year" required>

                    <label for="genre">Genre:</label>
                    <input type="text" id="genre" name="genre">
                    
                    <label for="poster">Poster URL:</label>
                    <input type="text" id="poster" name="poster" value="https://via.placeholder.com/200x300?text=New+Movie">

                    <label for="trailer_link">Trailer Link (YouTube/Vimeo):</label>
                    <input type="text" id="trailer_link" name="trailer_link">
                    
                    <label for="download_link">Download Link (Direct URL):</label>
                    <input type="text" id="download_link" name="download_link">

                    <button type="submit">Add Movie</button>
                    <!-- TODO: Add a button to fetch data from TMDb based on title -->
                    <!-- In a real app, this would involve a separate API call from the backend -->
                </form>
            </div>

            <h3>Manage Movies</h3>
            <ul class="admin-movie-list">
                {% for movie in movies %}
                <li class="admin-movie-item">
                    <span>{{ movie.title }} ({{ movie.year }})</span>
                    <div class="actions">
                        <a href="{{ url_for('edit_movie', movie_id=movie.id) }}">Edit</a>
                        <form method="POST" action="{{ url_for('delete_movie', movie_id=movie.id) }}" style="display:inline;">
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
                <form method="POST" action="{{ url_for('update_movie', movie_id=movie.id) }}">
                    <label for="title">Title:</label>
                    <input type="text" id="title" name="title" value="{{ movie.title }}" required>

                    <label for="year">Year:</label>
                    <input type="text" id="year" name="year" value="{{ movie.year }}" required>

                    <label for="genre">Genre:</label>
                    <input type="text" id="genre" name="genre" value="{{ movie.genre }}">

                    <label for="poster">Poster URL:</label>
                    <input type="text" id="poster" name="poster" value="{{ movie.poster }}">

                    <label for="trailer_link">Trailer Link (YouTube/Vimeo):</label>
                    <input type="text" id="trailer_link" name="trailer_link" value="{{ movie.trailer_link or '' }}">
                    
                    <label for="download_link">Download Link (Direct URL):</label>
                    <input type="text" id="download_link" name="download_link" value="{{ movie.download_link or '' }}">

                    <button type="submit">Update Movie</button>
                    <a href="{{ url_for('admin_dashboard') }}" class="btn" style="margin-left: 10px;">Cancel</a>
                </form>
            </div>
        </section>
"""

# --- Routes ---

@app.route('/')
def home():
    # In a real app, you'd fetch movies from MongoDB here
    return render_template_string(BASE_HTML, title="CineHub - Home", content=render_template_string(HOME_CONTENT, movies=movies_data))

@app.route('/admin')
def admin_dashboard():
    # In a real app, you'd fetch movies from MongoDB here
    return render_template_string(BASE_HTML, title="CineHub - Admin", content=render_template_string(ADMIN_DASHBOARD_CONTENT, movies=movies_data))

@app.route('/admin/add_movie', methods=['POST'])
def add_movie():
    global next_movie_id
    # TODO: In a real app, you'd interact with TMDb here to get full movie details.
    # Example: response = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key=YOUR_TMD_API_KEY&query={request.form['title']}")
    #          movie_details = response.json().get('results')[0] # and then parse it.

    new_movie = {
        "id": next_movie_id,
        "title": request.form['title'],
        "year": int(request.form['year']),
        "genre": request.form.get('genre', 'Unknown'),
        "poster": request.form.get('poster', 'https://via.placeholder.com/200x300?text=New+Movie'),
        "trailer_link": request.form.get('trailer_link', '#'),
        "download_link": request.form.get('download_link', '#')
    }
    movies_data.append(new_movie)
    next_movie_id += 1
    # In a real app, you'd insert into MongoDB here: movies_collection.insert_one(new_movie)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_movie/<int:movie_id>')
def edit_movie(movie_id):
    movie_to_edit = next((movie for movie in movies_data if movie['id'] == movie_id), None)
    if movie_to_edit:
        return render_template_string(BASE_HTML, title=f"Edit {movie_to_edit['title']}", content=render_template_string(EDIT_MOVIE_CONTENT, movie=movie_to_edit))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_movie/<int:movie_id>', methods=['POST'])
def update_movie(movie_id):
    movie_to_update = next((movie for movie in movies_data if movie['id'] == movie_id), None)
    if movie_to_update:
        movie_to_update.update({
            "title": request.form['title'],
            "year": int(request.form['year']),
            "genre": request.form.get('genre', 'Unknown'),
            "poster": request.form.get('poster', 'https://via.placeholder.com/200x300?text=New+Movie'),
            "trailer_link": request.form.get('trailer_link', '#'),
            "download_link": request.form.get('download_link', '#')
        })
        # In a real app, you'd update in MongoDB here: movies_collection.update_one({"id": movie_id}, {"$set": movie_to_update})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    global movies_data
    movies_data = [movie for movie in movies_data if movie['id'] != movie_id]
    # In a real app, you'd delete from MongoDB here: movies_collection.delete_one({"id": movie_id})
    return redirect(url_for('admin_dashboard'))


# --- Run the app ---
if __name__ == '__main__':
    app.run(debug=True)
