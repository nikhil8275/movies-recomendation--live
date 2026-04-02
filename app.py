from flask import Flask, render_template, request, jsonify
import pandas as pd
import ast
import re
from sklearn.metrics.pairwise import cosine_similarity
import os
import pickle
import os

app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROCESSED_PATH = os.path.join(BASE_DIR, "processed_movies.pkl")
TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")


def load_pickle(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required artifact '{path}' not found. Run prepare_data.py locally and commit the generated files for deployment."
        )
    with open(path, 'rb') as f:
        return pickle.load(f)


def initialize_app():
    new_movies = load_pickle(PROCESSED_PATH)
    tfidf = load_pickle(TFIDF_PATH)
    tfidf_matrix = tfidf.transform(new_movies['tags'])
    similarity = cosine_similarity(tfidf_matrix)
    return new_movies, tfidf, tfidf_matrix, similarity


new_movies, tfidf, tfidf_matrix, similarity = initialize_app()

indices = pd.Series(new_movies.index, index=new_movies['title']).drop_duplicates()
title_lookup = {title.lower(): title for title in new_movies['title'].tolist()}

def get_exact_title(query):
    query = query.strip().lower()
    if not query:
        return None
    if query in title_lookup:
        return title_lookup[query]

    from difflib import get_close_matches
    close = get_close_matches(query, list(title_lookup.keys()), n=1, cutoff=0.8)
    if close:
        return title_lookup[close[0]]
    return None


def tokenize_query(query):
    return re.findall(r'\w+', query.lower())


def search_query_movies(query, top_n=5):
    query = query.strip().lower()
    if not query:
        return []

    tokens = tokenize_query(query)
    if not tokens:
        return []

    token_pattern = r'\b(' + '|'.join(re.escape(t) for t in tokens) + r')\b'
    phrase_mask = new_movies['tags'].str.contains(re.escape(query), na=False)
    direct_mask = new_movies['tags'].str.contains(token_pattern, regex=True, na=False)

    if phrase_mask.any() or direct_mask.any():
        matched = new_movies[phrase_mask | direct_mask].copy()

        def score_row(row):
            tags = row['tags']
            tagline_text = row['tagline'] if isinstance(row['tagline'], str) else ''
            exact_phrase = bool(re.search(re.escape(query), tags))
            token_matches = sum(1 for t in tokens if re.search(rf'\b{re.escape(t)}\b', tags))
            genre_matches = sum(1 for t in tokens if t in [g.lower() for g in row['genres']])
            keyword_matches = sum(1 for t in tokens if t in [k.lower() for k in row['keywords']])
            title_matches = sum(1 for t in tokens if re.search(rf'\b{re.escape(t)}\b', row['title'].lower()))
            tagline_matches = sum(1 for t in tokens if re.search(rf'\b{re.escape(t)}\b', tagline_text.lower()))
            return (1 if exact_phrase else 0,
                    genre_matches * 4 + keyword_matches * 3,
                    title_matches * 2 + tagline_matches,
                    token_matches)

        matched['score'] = matched.apply(score_row, axis=1)
        matched = matched.sort_values(by=['score'], ascending=False)
        return matched['title'].head(top_n).tolist()

    query_vec = tfidf.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_indices = [i for i in similarities.argsort()[::-1] if similarities[i] > 0.05][:top_n]
    return new_movies.iloc[top_indices]['title'].tolist()


def recommend(title, cosine_sim=similarity):
    title = title.strip()
    exact_match = get_exact_title(title)
    if exact_match:
        idx = indices[exact_match]
        distances = list(enumerate(cosine_sim[idx]))
        distances = sorted(distances, key=lambda x: x[1], reverse=True)[1:6]
        rec_indices = [i[0] for i in distances]
        rec_movies = new_movies.iloc[rec_indices]['title'].tolist()
        return rec_movies

    return search_query_movies(title, top_n=5)

@app.route('/movie_info', methods=['POST'])
def movie_info():
    title = request.json.get('title', '').strip()
    exact_match = get_exact_title(title)
    if exact_match:
        movie_title = exact_match
    else:
        search_results = search_query_movies(title, top_n=1)
        if not search_results:
            return jsonify({'found': False})
        movie_title = search_results[0]

    movie = new_movies.loc[new_movies['title'] == movie_title].iloc[0]
    tagline = movie['tagline'] if isinstance(movie['tagline'], str) else ''
    overview = movie['overview'] if isinstance(movie['overview'], str) else ''
    release_date = movie['release_date'] if isinstance(movie['release_date'], str) else ''
    vote_average = str(movie['vote_average']) if pd.notna(movie['vote_average']) else ''

    return jsonify({
        'found': True,
        'title': movie['title'],
        'tagline': tagline,
        'overview': overview,
        'release_date': release_date,
        'vote_average': vote_average
    })

@app.route('/')
def home():
    titles = new_movies['title'].tolist()[:100]  # Sample for dropdown
    return render_template('index.html', titles=titles)

@app.route('/recommend', methods=['POST'])
def get_recommendations():
    title = request.json.get('title', '').strip()
    recs = recommend(title)
    return jsonify({'recommendations': recs})

if __name__ == '__main__':
    app.run(debug=True)

