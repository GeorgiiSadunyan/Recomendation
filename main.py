import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Заголовок приложения
st.title("🍿 Рекомендательная система для фильмов")


# Загрузка данных с явным указанием типов
@st.cache_data
def load_data():
    movies = pd.read_csv("movies.csv")
    # Читаем ratings.csv, явно указывая типы колонок и пропуская строку с заголовками
    ratings = pd.read_csv("ratings.csv", 
                         names=["userId", "movieId", "rating", "timestamp"],
                         header=None,
                         dtype={'userId': int, 'movieId': int, 'rating': float, 'timestamp': str},
                         skiprows=1)
    return movies, ratings

movies, ratings = load_data()

# # Проверка и очистка данных
# st.write("Первые 5 строк ratings:")
# st.write(ratings.head())

# Убедимся, что rating действительно числовой
ratings['rating'] = pd.to_numeric(ratings['rating'], errors='coerce')
ratings = ratings.dropna(subset=['rating'])

# Предобработка данных
movies['genres'] = movies['genres'].str.split('|')

# Создание матрицы пользователь-фильм с проверкой
try:
    user_movie_matrix = ratings.pivot_table(
        index='userId', 
        columns='movieId', 
        values='rating', 
        aggfunc='mean'  # Явно указываем агрегацию
    ).fillna(0)
    
    # # Проверка, что матрица создана корректно
    # st.write(f"Размер матрицы пользователь-фильм: {user_movie_matrix.shape}")
    # st.write("Пример данных из матрицы:")
    # st.write(user_movie_matrix.iloc[:5, :5])
    
except Exception as e:
    st.error(f"Ошибка при создании матрицы: {str(e)}")
    st.stop()

# Функция для рекомендаций
def recommend_movies(user_id, top_n=5):
    try:
        if user_id not in user_movie_matrix.index:
            return pd.DataFrame()
            
        user_ratings = user_movie_matrix.loc[user_id].values.reshape(1, -1)
        similarities = cosine_similarity(user_ratings, user_movie_matrix)
        similar_users = np.argsort(similarities[0])[::-1][1:top_n+1]
        
        recommended_movies = ratings[ratings["userId"].isin(similar_users)]
        top_movies = recommended_movies.groupby("movieId")["rating"].mean().sort_values(ascending=False).head(top_n)
        
        return movies[movies['movieId'].isin(top_movies.index)][['title', 'genres']]
    
    except Exception as e:
        st.error(f"Ошибка при генерации рекомендаций: {str(e)}")
        return pd.DataFrame()

# Интерфейс
tab1, tab2 = st.tabs(["Рекомендации", "Поиск"])

with tab1:
    st.subheader("Персональные рекомендации")
    user_id = st.number_input("Введите ваш user_id:", 
                            min_value=1, 
                            max_value=ratings['userId'].max(), 
                            value=1)
    
    if st.button("Получить рекомендации"):
        recommendations = recommend_movies(user_id)
        if not recommendations.empty:
            st.write("Вам могут понравиться:")
            for i, row in recommendations.iterrows():
                st.write(f"- **{row['title']}** ({', '.join(row['genres'])})")
        else:
            st.warning("Пользователь не найден или недостаточно данных. Попробуйте другой ID.")

with tab2:
    st.subheader("Поиск фильмов по жанру")
    all_genres = sorted(set([genre for sublist in movies['genres'] for genre in sublist]))
    selected_genres = st.multiselect("Выберите жанры:", all_genres)
    
    if selected_genres:
        mask = movies['genres'].apply(lambda x: any(genre in x for genre in selected_genres))
        filtered_movies = movies[mask][['title', 'genres']].head(20)
        st.write(f"Найдено фильмов: {len(filtered_movies)}")
        for i, row in filtered_movies.iterrows():
            st.write(f"- **{row['title']}** ({', '.join(row['genres'])})")

# Дополнительная информация
st.sidebar.markdown("### О системе")
st.sidebar.write("""
Используется коллаборативная фильтрация:
1. Находит пользователей с похожими вкусами
2. Рекомендует фильмы, которые они высоко оценили
""")
st.sidebar.write(f"Всего фильмов: {len(movies)}")
st.sidebar.write(f"Всего оценок: {len(ratings)}")
st.sidebar.write(f"Уникальных пользователей: {user_movie_matrix.shape[0]}")
st.sidebar.write(f"Уникальных фильмов: {user_movie_matrix.shape[1]}")