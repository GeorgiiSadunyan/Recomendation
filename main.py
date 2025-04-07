import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import requests
from PIL import Image
from io import BytesIO
import os

# --- Настройка страницы ---
st.set_page_config(
    page_title="🍿Фильмы",
    page_icon="🎬",
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
    try:
        movies = pd.read_csv("movies.csv")
        
        movies['genres'] = movies['genres'].apply(
        lambda x: [x] if isinstance(x, str) and '|' not in x else x.split('|') if isinstance(x, str) else []
        )
        
        ratings = pd.read_csv(
            "ratings.csv",
            header=None,  # Явно указываем, что заголовков нет
            names=["userId", "movieId", "rating", "timestamp"],
            dtype={'userId': int, 'movieId': int, 'rating': float, 'timestamp': str},
            skiprows=1
        )
        
        # Проверка на пустые данные
        if ratings.empty or movies.empty:
            st.error("Один из файлов пуст!")
            return None, None
            
        return movies, ratings
        
    except Exception as e:
        st.error(f"Критическая ошибка загрузки: {str(e)}")
        return None, None

movies, ratings = load_data()

# Проверка данных
if not os.path.exists("ratings.csv"):
    st.error("Файл ratings.csv не найден!")
if ratings is None or movies is None:
    st.stop()

if ratings.empty or movies.empty:
    st.error("Файлы данных пусты!")
    st.stop()

# Безопасное получение максимального ID
max_user_id = int(ratings['userId'].max()) if not ratings['userId'].empty else 1

try:
    user_id = st.number_input(
        "Ваш User ID", 
        min_value=1, 
        max_value=max_user_id,
        value=min(1, max_user_id),
        help=f"Доступные ID: от 1 до {max_user_id}"
    )
    if st.button("🎯 Получить рекомендации", use_container_width=True):
        st.session_state['recommend'] = True
except Exception as e:
    st.error(f"Ошибка ввода: {str(e)}")
    st.stop()

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