import ast
import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

PROCESSED_PATH = 'processed_movies.pkl'
TFIDF_PATH = 'tfidf.pkl'


def load_raw_datasets():
    movies = pd.read_csv('data/tmdb_5000_movies.csv')
    credits = pd.read_csv('data/tmdb_5000_credits.csv')
    return movies, credits


def preprocess_data():
    movies_raw, credits_raw = load_raw_datasets()
    movies = movies_raw.merge(credits_raw, on='title')
    movies = movies[['movie_id', 'title', 'overview', 'tagline', 'release_date', 'vote_average', 'genres', 'keywords', 'cast', 'crew']]

    def convert(obj):
        return [i['name'] for i in ast.literal_eval(obj)]

    movies['genres'] = movies['genres'].apply(convert)
    movies['keywords'] = movies['keywords'].apply(convert)

    def convert_cast(obj):
        if isinstance(obj, list):
            return [i['name'] for i in obj[:3]]
        return []

    movies['cast'] = movies['cast'].apply(lambda x: [i.replace(' ', '') for i in convert_cast(x)])

    def convert_crew(obj):
        return [i['name'] for i in ast.literal_eval(obj) if i['job'] == 'Director']

    movies['crew'] = movies['crew'].apply(convert_crew)

    movies['overview_list'] = movies['overview'].apply(lambda x: x.split() if isinstance(x, str) else [])
    movies['tagline_list'] = movies['tagline'].apply(lambda x: x.split() if isinstance(x, str) else [])
    movies['title_list'] = movies['title'].apply(lambda x: x.split() if isinstance(x, str) else [])

    movies['genres'] = movies['genres'].apply(lambda x: [i.replace(' ', '') for i in x])
    movies['keywords'] = movies['keywords'].apply(lambda x: [i.replace(' ', '') for i in x])
    movies['cast'] = movies['cast'].apply(lambda x: [i.replace(' ', '') for i in x])
    movies['crew'] = movies['crew'].apply(lambda x: [i.replace(' ', '') for i in x])

    movies['tags'] = (
        movies['overview_list']
        + movies['tagline_list']
        + movies['title_list']
        + movies['genres']
        + movies['keywords']
        + movies['cast']
        + movies['crew']
    )

    new_movies = movies[['movie_id', 'title', 'tags', 'overview', 'tagline', 'release_date', 'vote_average', 'genres', 'keywords', 'cast', 'crew']].copy()
    new_movies['tags'] = new_movies['tags'].apply(lambda x: ' '.join(x).lower())
    return new_movies


def build_and_save_artifacts():
    print('Loading raw data and preprocessing...')
    new_movies = preprocess_data()
    print('Building TF-IDF model...')
    tfidf = TfidfVectorizer(max_features=5000, stop_words='english')
    tfidf.fit(new_movies['tags'])

    print(f'Saving processed metadata to {PROCESSED_PATH}')
    with open(PROCESSED_PATH, 'wb') as f:
        pickle.dump(new_movies, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f'Saving TF-IDF model to {TFIDF_PATH}')
    with open(TFIDF_PATH, 'wb') as f:
        pickle.dump(tfidf, f, protocol=pickle.HIGHEST_PROTOCOL)

    print('Artifact generation complete.')


if __name__ == '__main__':
    build_and_save_artifacts()
