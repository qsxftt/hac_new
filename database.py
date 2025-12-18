# database.py

from models import db, User, Analysis, AnalysisResult, Exercise, UserProgress
from flask import Flask
import os
import json

def init_db(app):
    """
    Инициализация базы данных
    """
    db.init_app(app)
    
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("✅ База данных инициализирована")
        
        # Загружаем упражнения из JSON (если еще не загружены)
        load_exercises_from_json()
        print("✅ Упражнения загружены")


def load_exercises_from_json():
    """
    Загрузка упражнений из exercises_database.json в БД
    """
    # Проверяем, есть ли уже упражнения
    if Exercise.query.count() > 0:
        print("ℹ️  Упражнения уже загружены в БД, пропускаем")
        return
    
    # Путь к файлу с упражнениями
    json_path = 'exercises_database.json'
    
    if not os.path.exists(json_path):
        print(f"⚠️  Файл {json_path} не найден. Создаем пустую базу упражнений")
        create_sample_exercises()
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            exercises_data = json.load(f)
        
        # Добавляем упражнения в БД
        for ex_data in exercises_data:
            exercise = Exercise(
                category=ex_data.get('category'),
                difficulty=ex_data.get('difficulty', 'beginner'),
                title=ex_data.get('title'),
                description=ex_data.get('description'),
                instructions=ex_data.get('instructions'),
                duration_minutes=ex_data.get('duration_minutes', 5),
                practice_text=ex_data.get('practice_text'),
                demo_url=ex_data.get('demo_url')
            )
            db.session.add(exercise)
        
        db.session.commit()
        print(f"✅ Загружено {len(exercises_data)} упражнений из JSON")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки упражнений: {e}")
        db.session.rollback()


def create_sample_exercises():
    """
    Создание примеров упражнений для тестирования
    (используется если exercises_database.json отсутствует)
    """
    sample_exercises = [
        {
            'category': 'tempo',
            'difficulty': 'beginner',
            'title': 'Медленноговорки',
            'description': 'Упражнение для снижения темпа речи и улучшения дикции',
            'instructions': '1. Выберите любой текст (новость, статью)\n2. Прочитайте его вслух, сознательно растягивая гласные звуки\n3. Контролируйте, чтобы темп был не более 2-3 слов в секунду\n4. Повторите 3-5 раз, постепенно возвращаясь к нормальному темпу',
            'duration_minutes': 5,
            'practice_text': 'Глокая куздра штеко будланула бокра и кудрячит бокрёнка.',
            'demo_url': None
        },
        {
            'category': 'filler_words',
            'difficulty': 'beginner',
            'title': 'Начни сначала',
            'description': 'Техника самоконтроля для избавления от слов-паразитов',
            'instructions': '1. Выберите тему для 2-минутного рассказа\n2. Попросите друга или включите диктофон\n3. Начните говорить\n4. Каждый раз, когда произносите слово-паразит — останавливайтесь и начинайте сначала\n5. Продолжайте до тех пор, пока не расскажете всю историю без единого "ээ", "это", "ну"',
            'duration_minutes': 10,
            'practice_text': None,
            'demo_url': None
        },
        {
            'category': 'pauses',
            'difficulty': 'beginner',
            'title': 'Квадрат дыхания',
            'description': 'Дыхательное упражнение для контроля пауз',
            'instructions': '1. Вдох через нос на 4 счета\n2. Задержка дыхания на 4 счета\n3. Выдох через рот на 4 счета\n4. Задержка дыхания на 4 счета\n5. Повторить 5-7 циклов\n\nЭто упражнение поможет контролировать дыхание во время выступления и делать осознанные паузы.',
            'duration_minutes': 3,
            'practice_text': None,
            'demo_url': None
        },
    ]
    
    for ex_data in sample_exercises:
        exercise = Exercise(**ex_data)
        db.session.add(exercise)
    
    db.session.commit()
    print(f"✅ Создано {len(sample_exercises)} примеров упражнений")


def create_test_user():
    """
    Создание тестового пользователя (для разработки)
    """
    # Проверяем, есть ли уже пользователи
    if User.query.count() > 0:
        print("ℹ️  Пользователи уже существуют")
        return
    
    test_user = User(
        email='test@example.com',
        username='Тестовый Пользователь'
    )
    test_user.set_password('test123')
    
    db.session.add(test_user)
    db.session.commit()
    print("✅ Создан тестовый пользователь: test@example.com / test123")


# Standalone запуск для создания БД
if __name__ == '__main__':
    # ========= ИСПРАВЛЕНИЕ: Сначала создаем папку! =========
    os.makedirs('instance', exist_ok=True)
    print("📁 Папка instance создана")
    
    app = Flask(__name__)
    
    # Используем абсолютный путь для Windows
    db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print(f"📍 Путь к БД: {db_path}")
    
    init_db(app)
    
    with app.app_context():
        create_test_user()
    
    print("\n🎉 База данных успешно создана!")
    print(f"📁 Расположение: {db_path}")
