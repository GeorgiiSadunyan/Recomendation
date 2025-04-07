import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import requests
from PIL import Image
from io import BytesIO
import os

# Настройка страницы
st.set_page_config(page_title="🍿 Кинорекомендатель")

# Стили CSS
st.markdown("""
<style>
.movie-card {
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    background-color: #f0f2f6;
}
.title {
    color: #ff4b4b;
    font-size: 1.2em !important;
}
.genre {
    color: #666;
    font-style: italic;
}
</style>
""", unsafe_allow_html=True)

# Загрузка данных
@st.cache_data
def load_data():
    movies = pd.read_csv("movies.csv")
    ratings = pd.read_csv("ratings.csv", 
                         header=None,
                         names=["userId", "movieId", "rating", "timestamp"])
    
    # Обработка жанров
    movies['genres'] = movies['genres'].apply(
        lambda x: [x] if '|' not in str(x) else str(x).split('|')
    )
    return movies, ratings

movies, ratings = load_data()

# Функция для получения постера (заглушка)
def get_poster(title):
    return None  # Замените на реальный API

# Главный интерфейс
st.title("🎬 Персональные рекомендации фильмов")

# Выбор пользователя на главной странице
user_id = st.number_input(
    "Введите ваш ID пользователя:", 
    min_value=1, 
    max_value=ratings['userId'].max(),
    value=1
)

# Рекомендации
if st.button("Показать рекомендации"):
    # Ваш код рекомендаций
    recommended_movies = movies.sample(5)  # Замените на реальные рекомендации
    
    st.subheader("Вам может понравиться:")
    cols = st.columns(2)
    for i, row in recommended_movies.iterrows():
        with cols[i%2]:
            poster = get_poster(row['title'])
            if poster:
                st.image(poster, width=150)
            else:
                st.image("https://via.placeholder.com/150x225?text=No+Poster", width=150)
            
            st.markdown(f"""
            <div class="movie-card">
                <div class="title">{row['title']}</div>
                <div class="genre">{', '.join(row['genres'])}</div>
            </div>
            """, unsafe_allow_html=True)

# Поиск по жанрам
st.divider()
st.subheader("🔍 Поиск фильмов по жанру")

all_genres = sorted({g for genres in movies['genres'] for g in genres})
selected_genres = st.multiselect("Выберите жанры:", all_genres)

if selected_genres:
    filtered_movies = movies[movies['genres'].apply(
        lambda x: any(g in x for g in selected_genres)
    )].head(20)
    
    for _, row in filtered_movies.iterrows():
        st.markdown(f"- **{row['title']}** ({', '.join(row['genres'])})")