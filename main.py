from collections import defaultdict
import streamlit as st
import pandas as pd
import os


st.title("🍿 Рекомендации фильмов")
NEW_RATINGS_FILE = "new_ratings.csv"


# Загрузка данных с явным указанием типов
@st.cache_data
def load_data():
    movies = pd.read_csv("movies.csv")

    ratings = pd.read_csv("ratings.csv", 
                         names=["userId", "movieId", "rating", "timestamp"],
                         header=None,
                         dtype={'userId': int, 'movieId': int, 'rating': float, 'timestamp': str},
                         skiprows=1)
    return movies, ratings


movies, ratings = load_data()


if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'onboarding' not in st.session_state:
    st.session_state.onboarding = False


# Убедимся, что rating действительно числовой
ratings['rating'] = pd.to_numeric(ratings['rating'], errors='coerce')
ratings = ratings.dropna(subset=['rating'])

# Предобработка данных
movies['genres'] = movies['genres'].str.split('|')


# Функция сохранения
def save_ratings(user_id, ratings_dict):
    """Простое сохранение оценок в CSV"""
    new_data = pd.DataFrame({
        'userId': [user_id] * len(ratings_dict),
        'movieId': list(ratings_dict.keys()),
        'rating': list(ratings_dict.values())
    })
    
    # Записываем в файл (дозапись в конец)
    # new_data.to_csv('new_ratings.csv', mode='a', header=not os.path.exists('new_ratings.csv'), index=False)
    
    # Проверка существования файла для корректного заголовка
    file_exists = os.path.exists(NEW_RATINGS_FILE)
    
    # Запись данных и синхронизация внутри одного контекста
    with open(NEW_RATINGS_FILE, 'a') as f:
        new_data.to_csv(f, mode='a', header=not file_exists, index=False)
        f.flush()
        os.fsync(f.fileno())
    
    
# Создание матрицы пользователь-фильм с проверкой
try:
    user_movie_matrix = ratings.pivot_table(
        index='userId', 
        columns='movieId', 
        values='rating', 
        aggfunc='mean'  # Явно указываем агрегацию
    ).fillna(0)
    
except Exception as e:
    st.error(f"Ошибка при создании матрицы: {str(e)}")
    st.stop()


# Генерация ID
def generate_user_id():
    existing_ids = set(ratings['userId'].unique())
    if os.path.exists(NEW_RATINGS_FILE):
        new_ratings = pd.read_csv(NEW_RATINGS_FILE)
        existing_ids.update(new_ratings['userId'].unique())
    return max(existing_ids) + 1 if existing_ids else 1


#функция рекомендаций
def recommend_movies(user_id, top_n=5):
    try:
        # Объединяем все рейтинги
        all_ratings = pd.concat([ratings, pd.read_csv(NEW_RATINGS_FILE)] if os.path.exists(NEW_RATINGS_FILE) else ratings)
        
        # 1. Собираем данные пользователя
        user_ratings = all_ratings[all_ratings['userId'] == user_id]
        
        # 2. Взвешивание жанров
        user_movies = user_ratings.merge(movies, on='movieId')
        genre_weights = defaultdict(float)
        for _, row in user_movies.iterrows():
            for genre in row['genres']:
                genre_weights[genre] += row['rating']  # Вес = сумма оценок
        
        # 3. Байесовский рейтинг
        C = all_ratings['rating'].mean()  # Средний рейтинг по всем фильмам
        m = all_ratings['movieId'].value_counts().quantile(0.7)  # Порог популярности
        
        movie_stats = all_ratings.groupby('movieId').agg(
            avg_rating=('rating', 'mean'),
            num_ratings=('rating', 'count')
        ).reset_index()
        
        # Формула байесовского среднего
        movie_stats['bayesian_rating'] = (
            (movie_stats['num_ratings'] / (movie_stats['num_ratings'] + m)) * movie_stats['avg_rating'] + 
            (m / (movie_stats['num_ratings'] + m)) * C
        )
        
        # 4. Фильтрация кандидатов (оригинальная логика)
        candidates = movies[
            (~movies['movieId'].isin(user_ratings['movieId'])) & 
            (movies['genres'].apply(lambda x: any(g in x for g in genre_weights.keys())))
        ]
        
        # 5. Гибридный скоринг (новое)
        recommendations = candidates.merge(movie_stats, on='movieId')
        
        # Рассчет жанрового веса для каждого фильма
        recommendations['genre_score'] = recommendations['genres'].apply(
            lambda x: sum(genre_weights.get(g, 0) for g in x)
        )
        
        # Нормализация показателей
        recommendations['bayesian_norm'] = (recommendations['bayesian_rating'] - recommendations['bayesian_rating'
            ].min()) / (recommendations['bayesian_rating'].max() - recommendations['bayesian_rating'].min())
        
        recommendations['genre_norm'] = (recommendations['genre_score'] - recommendations['genre_score'
            ].min()) / (recommendations['genre_score'].max() - recommendations['genre_score'].min())
        
        # Комбинированный рейтинг (60% байесовский + 40% жанры)
        recommendations['final_score'] = 0.6 * recommendations['bayesian_norm'] + 0.4 * recommendations['genre_norm']
        
        # Сортировка по комбинированному рейтингу
        recommendations = recommendations.sort_values('final_score', ascending=False)
        
        return recommendations.head(top_n)
    
    except Exception as e:
        st.error(f"Ошибка: {str(e)}")
        return pd.DataFrame()
   
    
# Профиль
def show_user_profile(user_id):
    
    movies, ratings = load_data()
    movies['genres'] = movies['genres'].str.split('|')
    
    ratings = pd.concat([ratings, pd.read_csv(NEW_RATINGS_FILE)] 
                        if os.path.exists(NEW_RATINGS_FILE) else ratings)
    
    user_ratings = ratings[ratings['userId'] == user_id]
    
    if not user_ratings.empty:
        st.subheader(f"Ваши любимые фильмы (UserID: {user_id})")
        liked_movies = user_ratings.merge(
            movies, 
            on='movieId',
            how='inner')
        
        if liked_movies.empty:
            st.error("Ошибка: некорректные данные в оценках.")
            return
        
        genre_weights = defaultdict(float) #вес жанра
        for _, row in liked_movies.iterrows():
            for genre in row['genres']:
                genre_weights[genre] += row['rating']
        
        liked_movies['genre_score'] = liked_movies['genres'].apply(
            lambda x: sum(genre_weights.get(g, 0) for g in x)
        )
        
        # Сортировка: сначала по оценке (убывание), затем по genre_score (убывание)
        liked_movies = liked_movies.sort_values(
            ['rating', 'genre_score'], 
            ascending=[False, False]
        )
        
        st.dataframe(liked_movies[['title', 'genres', 'rating']].head(10),
                     hide_index=True,
                     column_config={
                         "title": "Название фильма",
                         "genres": "Жанр",
                         "rating": "Оценка"
                     })
    else:
        st.warning("У вас пока нет оценённых фильмов.")


# Интерфейс
tab1, tab2, tab3 = st.tabs(["Рекомендации", "Поиск", "Профиль"])


with tab1:
    st.subheader("Персональные рекомендации")
    new_ratings = pd.read_csv(NEW_RATINGS_FILE)
    user_id = st.number_input("Введите ваш user_id:", 
                            min_value=1, 
                            max_value=new_ratings['userId'].max(),
                            value=1)
    
    if st.button("Получить рекомендации"):
        recommendations = recommend_movies(user_id)
        if not recommendations.empty:
            st.write(f"5 рекомендаций для пользователя {user_id}:")
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


with tab3:
    show_user_profile(user_id)
    
    
# Добавление нового пользователя  
# Глобально инициализируем
if 'new_user_ratings' not in st.session_state:
    st.session_state.new_user_ratings = pd.DataFrame(columns=['userId', 'movieId', 'rating'])


def add_new_user():
    new_id = generate_user_id()
    st.session_state.current_user = new_id
    st.session_state.new_user_ratings = pd.DataFrame(columns=['userId', 'movieId', 'rating'])
    st.session_state.onboarding = True
    return new_id


# Кнопка в сайдбаре
if st.sidebar.button("➕ Новый пользователь"):
    new_id = add_new_user()
    st.success(f"Создан пользователь ID: {new_id}")
    st.session_state.onboarding = True  # Флаг для onboarding

    
# Выбор 10 фильмов для нового пользователя
def onboarding_step(user_id):
    st.cache_data.clear()
    # Перезагружаем данные
    movies, ratings = load_data()
    movies['genres'] = movies['genres'].str.split('|')

    st.subheader("Пожалуйста, оцените 10 фильмов")
    sample_movies = movies.sample(10)
    
    
    with st.form("onboarding_form"):
        ratings_input = {}
        for _, row in sample_movies.iterrows():
            rating = st.slider(
                f"Фильм: {row['title']} ({', '.join(row['genres'])})",
                0.5, 5.0, 3.0, step=0.5,
                key=f"rate_{user_id}_{row['movieId']}"
            )
            ratings_input[row['movieId']] = rating
        
        if st.form_submit_button("💾Сохранить оценки"):
            save_ratings(st.session_state.current_user, ratings_input)
            
            # Обновляем основной DataFrame
            new_ratings = pd.DataFrame({
                'userId': [st.session_state.current_user] * len(ratings_input),
                'movieId': list(ratings_input.keys()),
                'rating': list(ratings_input.values())
            })
            ratings = pd.concat([ratings, new_ratings], ignore_index=True)
                        
            st.success("Оценки сохранены!")
            st.session_state.onboarding = False
            st.cache_data.clear()
            st.rerun() 
            
  
# Статус для Сайдбара 
def get_current_stats():
    # Объединяем все оценки
    if os.path.exists(NEW_RATINGS_FILE):
        all_ratings = pd.concat([ratings, pd.read_csv(NEW_RATINGS_FILE)])
    else:
        all_ratings = ratings.copy()
    
    # Добавляем текущие несохраненные оценки
    if 'new_user_ratings' in st.session_state and not st.session_state.new_user_ratings.empty:
        all_ratings = pd.concat([all_ratings, st.session_state.new_user_ratings])
    
    return {
        "movies_total": len(movies),
        "ratings_total": len(all_ratings),
        "users_total": all_ratings['userId'].nunique(),
    }


# Проверяем onboarding-режим
if st.session_state.onboarding:
    onboarding_step(st.session_state.current_user)
    st.stop()
    
#боковая панель
stats = get_current_stats()
st.sidebar.metric("👥 Пользователей", stats["users_total"])
st.sidebar.metric("🎬 Фильмов", stats["movies_total"])
st.sidebar.metric("⭐ Оценок", stats["ratings_total"])