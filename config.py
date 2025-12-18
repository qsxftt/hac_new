# config.py
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    # API Keys
    GIGACHAT_API_KEY: str = os.getenv("GIGACHAT_API_KEY", "")
    
    if not GIGACHAT_API_KEY:
        print("⚠️  ВНИМАНИЕ: GIGACHAT_API_KEY не найден в .env")
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
    
    @classmethod
    def validate(cls):
        """Валидация конфигурации"""
        print("\n⚙️  ТЕКУЩИЕ НАСТРОЙКИ:")
        print(f"   • Модель Whisper: {cls.WHISPER_MODEL}")
        print(f"   • Температура GigaChat: {cls.GIGACHAT_TEMPERATURE}")
        print(f"   • Макс. токены GigaChat: {cls.GIGACHAT_MAX_TOKENS}")
        print(f"   • Порог темпа: {cls.SPEED_THRESHOLD} слов/сек")
        print(f"   • Отправка в GigaChat: {'ВКЛ' if cls.SEND_TO_GIGACHAT else 'ВЫКЛ'}")
        
        required_dirs = [
            cls.UPLOAD_FOLDER,
            cls.PLOTS_FOLDER,
            cls.AUDIO_FOLDER,
            cls.TRANSCRIPTS_FOLDER,
            cls.RESULTS_FOLDER
        ]
        
        for directory in required_dirs:
            os.makedirs(directory, exist_ok=True)
        
        return cls

# Создаем экземпляр конфигурации
config = Config.validate()