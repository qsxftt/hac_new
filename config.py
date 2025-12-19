# -*- coding: utf-8 -*-
# config.py

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    # API Keys
    GIGACHAT_API_KEY: str = os.getenv("GIGACHAT_API_KEY", "")
    if not GIGACHAT_API_KEY:
        print("[WARNING] GIGACHAT_API_KEY not found in .env")
        print("   Получите ключ на https://developers.sber.ru/portal/products/gigachat")
    
    # Настройки модели
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    
    # Пороги анализа
    SPEED_THRESHOLD: float = float(os.getenv("SPEED_THRESHOLD", "5.0"))
    PAUSE_THRESHOLD: float = float(os.getenv("PAUSE_THRESHOLD", "1.0"))
    REPETITION_THRESHOLD: int = int(os.getenv("REPETITION_THRESHOLD", "3"))
    
    # Настройки GigaChat
    GIGACHAT_MAX_TOKENS: int = int(os.getenv("GIGACHAT_MAX_TOKENS", "2000"))
    GIGACHAT_TEMPERATURE: float = float(os.getenv("GIGACHAT_TEMPERATURE", "0.7"))
    GIGACHAT_MODEL: str = os.getenv("GIGACHAT_MODEL", "GigaChat")
    
    # Пути
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    PLOTS_FOLDER: str = os.getenv("PLOTS_FOLDER", "static/plots")
    AUDIO_FOLDER: str = os.getenv("AUDIO_FOLDER", "audio")
    TRANSCRIPTS_FOLDER: str = os.getenv("TRANSCRIPTS_FOLDER", "transcripts")
    RESULTS_FOLDER: str = os.getenv("RESULTS_FOLDER", "results")
    
    # Настройки приложения
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SAVE_TRANSCRIPT: bool = os.getenv("SAVE_TRANSCRIPT", "True").lower() == "true"
    SEND_TO_GIGACHAT: bool = os.getenv("SEND_TO_GIGACHAT", "True").lower() == "true"
    
    # Настройки видео
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", "100")) * 1024 * 1024  # MB to bytes
    
    # ======== НОВЫЕ НАСТРОЙКИ БД ========
    
    # Путь к базе данных SQLite
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///instance/app.db"
    )
    
    # Отключаем tracking для производительности
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    
    # Секретный ключ для сессий (ВАЖНО: измените в продакшене!)
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Настройки сессий
    SESSION_TYPE: str = "filesystem"
    PERMANENT_SESSION_LIFETIME: int = 86400  # 24 часа в секундах
    
    @classmethod
    def validate(cls):
        """Configuration validation"""
        print("\n[CONFIG] CURRENT SETTINGS:")
        print(f"   - Whisper Model: {cls.WHISPER_MODEL}")
        print(f"   - GigaChat Temperature: {cls.GIGACHAT_TEMPERATURE}")
        print(f"   - GigaChat Max Tokens: {cls.GIGACHAT_MAX_TOKENS}")
        print(f"   - Speed Threshold: {cls.SPEED_THRESHOLD} words/sec")
        print(f"   - GigaChat Enabled: {'YES' if cls.SEND_TO_GIGACHAT else 'NO'}")
        print(f"   - Database: {cls.SQLALCHEMY_DATABASE_URI}")
        
        required_dirs = [
            cls.UPLOAD_FOLDER,
            cls.PLOTS_FOLDER,
            cls.AUDIO_FOLDER,
            cls.TRANSCRIPTS_FOLDER,
            cls.RESULTS_FOLDER,
            'instance'
        ]
        
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
        
        return cls

# Создаем экземпляр конфигурации
config = Config.validate()
