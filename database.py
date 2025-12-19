# -*- coding: utf-8 -*-
# database.py

from models import db, User, Analysis, AnalysisResult, Exercise, UserProgress
from flask import Flask
import os
import json

def init_db(app):
    """Database initialization"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("[DB] Database initialized")
        
        # Load exercises from JSON if not already loaded
        load_exercises_from_json()
        print("[DB] Exercises loaded")


def load_exercises_from_json():
    """Load exercises from exercises_database.json into database"""
    # Check if exercises already exist
    if Exercise.query.count() > 0:
        print("[INFO] Exercises already loaded in DB, skipping")
        return
    
    # Path to exercises file
    json_path = 'exercises_database.json'
    
    if not os.path.exists(json_path):
        print(f"[WARNING] File {json_path} not found. Creating empty exercises database")
        create_sample_exercises()
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            exercises_data = json.load(f)
        
        # Add exercises to database
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
        print(f"[OK] Loaded {len(exercises_data)} exercises from JSON")
        
    except Exception as e:
        print(f"[ERROR] Failed to load exercises: {e}")
        db.session.rollback()


def create_sample_exercises():
    """Create sample exercises for testing (used if exercises_database.json is missing)"""
    sample_exercises = [
        {
            'category': 'tempo',
            'difficulty': 'beginner',
            'title': 'Slow Speech Exercise',
            'description': 'Exercise to reduce speech rate and improve diction',
            'instructions': '1. Select any text (news, article)\n2. Read it aloud, intentionally stretching vowel sounds\n3. Ensure speech rate is not more than 2-3 words per second\n4. Repeat 3-5 times, gradually returning to normal pace',
            'duration_minutes': 5,
            'practice_text': 'The quick brown fox jumps over the lazy dog.',
            'demo_url': None
        },
        {
            'category': 'filler_words',
            'difficulty': 'beginner',
            'title': 'Start Over Technique',
            'description': 'Self-control technique to eliminate filler words',
            'instructions': '1. Choose a topic for a 2-minute story\n2. Ask a friend or record yourself\n3. Start speaking\n4. Each time you say a filler word - stop and start over\n5. Continue until you tell the whole story without fillers',
            'duration_minutes': 10,
            'practice_text': None,
            'demo_url': None
        },
        {
            'category': 'pauses',
            'difficulty': 'beginner',
            'title': 'Box Breathing',
            'description': 'Breathing exercise to control pauses',
            'instructions': '1. Inhale through nose for 4 counts\n2. Hold breath for 4 counts\n3. Exhale through mouth for 4 counts\n4. Hold breath for 4 counts\n5. Repeat 5-7 cycles',
            'duration_minutes': 3,
            'practice_text': None,
            'demo_url': None
        },
    ]
    
    for ex_data in sample_exercises:
        exercise = Exercise(**ex_data)
        db.session.add(exercise)
    
    db.session.commit()
    print(f"[OK] Created {len(sample_exercises)} sample exercises")


def create_test_user():
    """Create test user for development"""
    # Check if users already exist
    if User.query.count() > 0:
        print("[INFO] Users already exist")
        return
    
    test_user = User(
        email='test@example.com',
        username='Test User'
    )
    test_user.set_password('test123')
    
    db.session.add(test_user)
    db.session.commit()
    print("[OK] Test user created: test@example.com / test123")


# Standalone execution to create database
if __name__ == '__main__':
    os.makedirs('instance', exist_ok=True)
    print("[OK] Instance folder created")
    
    app = Flask(__name__)
    
    # Use absolute path for Windows
    db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print(f"[DB] Path: {db_path}")
    
    init_db(app)
    
    with app.app_context():
        create_test_user()
    
    print("\n[SUCCESS] Database created successfully!")
    print(f"[DB] Location: {db_path}")
