import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import requests
from PIL import Image
from io import BytesIO

# --- Настройка страницы ---
st.set_page_config(
    page_title="🍿 MovieMagic Recommender",
    page_icon="🎬",
    layout="wide"
)

# --- Стили CSS ---
def load_css():
    st.markdown("""
    <style>
    .movie-card {
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        background-color: #262730;
    }
    .movie-card:hover {
        transform: scale(1.02);
    }
    .title {
        color: #FF4B4B;
        font-size: 1.5em !important;
    }
    .genre {
        color: #8A8A8A;
        font-style: italic;
    }
    .stButton>button {
        background-color: #FF4B4B !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# --- Загрузка данных ---
@st.cache_data
def load_data():
    movies = pd.read_csv("movies.csv")
    ratings = pd.read_csv("ratings.csv", names=["userId", "movieId", "rating", "timestamp"])
    return movies, ratings

movies, ratings = load_data()

# --- Получение постера фильма (через OMDb API) ---
def get_poster(title):
    try:
        response = requests.get(f"http://img.omdbapi.com/?apikey=5fc1940d&t={title}")
        return response.url if response.status_code == 200 else None
    except:
        return None

# --- Интерфейс ---
st.title("🎬 MovieMagic Recommender")
st.markdown("""
<style>
[data-testid="stMarkdownContainer"] p {
    font-size: 1.1em !important;
}
</style>
""", unsafe_allow_html=True)

# --- Сайдбар ---
with st.sidebar:
    st.header("⚙️ Настройки")
    theme = st.selectbox("Тема", ["Светлая", "Тёмная"])
    user_id = st.number_input("Ваш User ID", min_value=1, max_value=ratings['userId'].max(), value=1)
    if st.button("🎯 Получить рекомендации", use_container_width=True):
        st.session_state['recommend'] = True

# --- Рекомендации ---
if 'recommend' in st.session_state:
    st.subheader("🔮 Вам может понравиться")
    
    # Заглушка для примера (замените на вашу модель)
    recommended_movies = movies.sample(5)
    
    cols = st.columns(2)
    for i, row in recommended_movies.iterrows():
        with cols[i % 2]:
            with st.container():
                st.markdown(f"""
                <div class="movie-card">
                    <h3 class="title">{row['title']}</h3>
                    <p class="genre">{', '.join(row['genres'])}</p>
                    <img src="https://via.placeholder.com/300x450?text=Poster+Missing" width="100%">
                </div>
                """, unsafe_allow_html=True)

# --- Поиск по жанрам ---
st.divider()
st.subheader("🔍 Поиск фильмов по жанру")

selected_genres = st.multiselect(
    "Выберите жанры", 
    options=sorted(set([g for genres in movies['genres'] for g in genres])),
    default=["Comedy", "Action"]
)

if selected_genres:
    filtered_movies = movies[movies['genres'].apply(lambda x: any(g in x for g in selected_genres))]
    st.dataframe(
        filtered_movies[['title', 'genres']],
        column_config={
            "title": "Название",
            "genres": "Жанры"
        },
        hide_index=True,
        use_container_width=True
    )