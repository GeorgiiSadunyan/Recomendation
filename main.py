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
    new_data.to_csv('new_ratings.csv', mode='a', header=not os.path.exists('new_ratings.csv'), index=False)
    
    
    
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



# Функция для рекомендаций (5 случайных фильмов)
def recommend_movies(user_id, top_n=5):
    try:
        return movies.sample(5)
    
    except Exception as e:
        st.error(f"Ошибка при генерации рекомендаций: {str(e)}")
        return pd.DataFrame()
   
   
    
# Профиль
def show_user_profile(user_id):
    user_ratings = ratings[ratings['userId'] == user_id]
    if not user_ratings.empty:
        st.subheader(f"Ваши любимые фильмы (UserID: {user_id})")
        liked_movies = user_ratings.merge(movies, on='movieId').sort_values('rating', ascending=False)
        st.dataframe(liked_movies[['title', 'genres', 'rating']].head(10))
    else:
        st.warning("У вас пока нет оценённых фильмов.")



# Интерфейс
tab1, tab2, tab3 = st.tabs(["Рекомендации", "Поиск", "Профиль"])

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
    global ratings 
    st.subheader("Шаг 1/1: Оцените 10 фильмов")
    sample_movies = movies.sample(10)
    
    with st.form("onboarding_form"):
        ratings_input = {}
        for _, row in sample_movies.iterrows():
            ratings_input[row['movieId']] = st.slider(
                f"Фильм: {row['title']} ({', '.join(row['genres'])})",
                0.5, 5.0, 3.0, step=0.5,
                key=f"rate_{row['movieId']}"
            )
        
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
if st.session_state.onboarding:  # Вместо hasattr
    onboarding_step(st.session_state.current_user)
    st.stop()
    
stats = get_current_stats()
st.sidebar.metric("👥 Пользователей", stats["users_total"])
st.sidebar.metric("🎬 Фильмов", stats["movies_total"])
st.sidebar.metric("⭐ Оценок", stats["ratings_total"])