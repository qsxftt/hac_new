# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    analyses = db.relationship('Analysis', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    progress = db.relationship('UserProgress', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Хеширование пароля"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def get_statistics(self):
        """Получить статистику пользователя"""
        analyses = self.analyses.filter_by(status='completed').all()
        
        if not analyses:
            return {
                'total_analyses': 0,
                'total_exercises': 0,
                'exercises_completed': 0,
                'completion_rate': 0,
                'avg_metrics': {},
                'avg_audio': {}  # НОВОЕ
            }
        
        total_exercises = Exercise.query.count()
        exercises_completed = UserProgress.query.filter_by(user_id=self.id).count()
        completion_rate = (exercises_completed / (total_exercises * len(analyses)) * 100) if total_exercises > 0 else 0
        
        # Собираем метрики
        all_metrics = []
        all_audio = []  # НОВОЕ
        
        for analysis in analyses:
            if analysis.result:
                metrics = analysis.result.get_metrics()
                all_metrics.append(metrics)
                
                # НОВОЕ: собираем аудио метрики
                audio_features = analysis.result.get_audio_features()
                if audio_features and 'energy_score' in audio_features:
                    all_audio.append(audio_features)
        
        # Средние метрики речи
        avg_metrics = {}
        if all_metrics:
            metric_keys = ['avg_tempo', 'pauses_count', 'filler_words_count', 'repetitions_count']
            for key in metric_keys:
                values = [m.get(key, 0) for m in all_metrics if m.get(key) is not None]
                avg_metrics[key] = sum(values) / len(values) if values else 0
        
        # НОВОЕ: Средние аудио метрики
        avg_audio = {}
        if all_audio:
            audio_keys = ['avg_volume', 'energy_score', 'pitch_variance']
            for key in audio_keys:
                values = [a.get(key, 0) for a in all_audio if a.get(key) is not None]
                avg_audio[key] = sum(values) / len(values) if values else 0
        
        return {
            'total_analyses': len(analyses),
            'total_exercises': total_exercises,
            'exercises_completed': exercises_completed,
            'completion_rate': completion_rate,
            'avg_metrics': avg_metrics,
            'avg_audio': avg_audio  # НОВОЕ
        }

    
    def get_progress_timeline(self):
        """Получить временную линию прогресса"""
        analyses = self.analyses.filter_by(status='completed') \
            .order_by(Analysis.created_at.asc()) \
            .all()
        
        timeline = []
        for analysis in analyses:
            if analysis.result:
                metrics = analysis.result.get_metrics()
                audio = analysis.result.get_audio_features()  # НОВОЕ
                
                timeline.append({
                    'date': analysis.created_at.strftime('%d.%m.%Y'),
                    'tempo': metrics.get('avg_tempo', 0),
                    'pauses': metrics.get('pauses_count', 0),
                    'fillers': metrics.get('filler_words_count', 0),
                    'repetitions': metrics.get('repetitions_count', 0),
                    'energy': audio.get('energy_score', 0) if audio else 0  # НОВОЕ
                })
        
        return timeline

    
    def get_improvement_suggestions(self):
        """Генерировать персональные советы на основе последних анализов"""
        recent_analyses = self.analyses.filter_by(status='completed') \
            .order_by(Analysis.created_at.desc()) \
            .limit(3) \
            .all()
        
        if not recent_analyses:
            return []
        
        suggestions = []
        
        # Собираем метрики
        recent_metrics = []
        recent_audio = []  # НОВОЕ
        
        for analysis in recent_analyses:
            if analysis.result:
                recent_metrics.append(analysis.result.get_metrics())
                # НОВОЕ: собираем аудио
                audio = analysis.result.get_audio_features()
                if audio:
                    recent_audio.append(audio)
        
        if not recent_metrics:
            return []
        
        # Средние значения
        avg_tempo = sum(m.get('avg_tempo', 0) for m in recent_metrics) / len(recent_metrics)
        avg_pauses = sum(m.get('pauses_count', 0) for m in recent_metrics) / len(recent_metrics)
        avg_fillers = sum(m.get('filler_words_count', 0) for m in recent_metrics) / len(recent_metrics)
        avg_reps = sum(m.get('repetitions_count', 0) for m in recent_metrics) / len(recent_metrics)
        
        # НОВОЕ: Средние аудио метрики
        avg_energy = 0
        avg_volume = 0
        if recent_audio:
            avg_energy = sum(a.get('energy_score', 0) for a in recent_audio) / len(recent_audio)
            avg_volume = sum(a.get('avg_volume', 0) for a in recent_audio) / len(recent_audio)
        
        # Советы по темпу
        if avg_tempo > 5:
            suggestions.append({
                'icon': 'fa-tachometer-alt',
                'color': 'danger',
                'title': 'Слишком быстрый темп',
                'text': 'Ты говоришь слишком быстро. Практикуй осознанные паузы и дыхание.',
                'category': 'tempo'
            })
        elif avg_tempo < 2:
            suggestions.append({
                'icon': 'fa-tachometer-alt',
                'color': 'warning',
                'title': 'Медленный темп речи',
                'text': 'Попробуй ускориться до 3-4 слов в секунду.',
                'category': 'tempo'
            })
        
        # Советы по словам-паразитам
        if avg_fillers > 10:
            suggestions.append({
                'icon': 'fa-comment-dots',
                'color': 'danger',
                'title': 'Много слов-паразитов',
                'text': 'Заменяй "эээ" и "нуу" на осмысленные паузы.',
                'category': 'filler_words'
            })
        
        # Советы по паузам
        if avg_pauses > 8:
            suggestions.append({
                'icon': 'fa-pause-circle',
                'color': 'warning',
                'title': 'Много длинных пауз',
                'text': 'Старайся держать паузы в пределах 1-2 секунд.',
                'category': 'pauses'
            })
        
        # Советы по повторам
        if avg_reps > 5:
            suggestions.append({
                'icon': 'fa-redo',
                'color': 'warning',
                'title': 'Частые повторы слов',
                'text': 'Используй синонимы для разнообразия речи.',
                'category': 'repetitions'
            })
        
        # ========== НОВЫЕ СОВЕТЫ ПО АУДИО ==========
        
        if avg_energy > 0:  # Если есть аудио данные
            if avg_energy < 40:
                suggestions.append({
                    'icon': 'fa-battery-quarter',
                    'color': 'danger',
                    'title': 'Низкая энергия речи',
                    'text': 'Твоя речь звучит монотонно и тихо. Работай над громкостью и интонацией!',
                    'category': 'energy'
                })
            elif avg_energy < 60:
                suggestions.append({
                    'icon': 'fa-battery-half',
                    'color': 'warning',
                    'title': 'Средняя энергия речи',
                    'text': 'Добавь больше эмоций и вариации в интонацию для вовлечения аудитории.',
                    'category': 'energy'
                })
        
        if avg_volume > 0 and avg_volume < 30:
            suggestions.append({
                'icon': 'fa-volume-down',
                'color': 'warning',
                'title': 'Тихая речь',
                'text': 'Твой голос слишком тихий. Практикуй дыхание диафрагмой и проекцию голоса.',
                'category': 'volume'
            })
        
        # Если всё отлично
        if not suggestions:
            suggestions.append({
                'icon': 'fa-star',
                'color': 'success',
                'title': 'Отличная работа!',
                'text': 'Твои показатели в норме. Продолжай практиковаться!',
                'category': 'general'
            })
        
        return suggestions




class Analysis(db.Model):
    """Модель анализа видео"""
    __tablename__ = 'analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    video_filename = db.Column(db.String(255), nullable=False)
    video_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    scenario_type = db.Column(db.String(50), nullable=True)  # academic/project/hackathon/public/custom
    scenario_text = db.Column(db.Text, nullable=True)  # Для custom сценариев
    status = db.Column(db.String(20), default='processing')  # processing/completed/error
    
    # Связи
    result = db.relationship('AnalysisResult', backref='analysis', uselist=False, cascade='all, delete-orphan')
    progress_records = db.relationship('UserProgress', backref='analysis', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Analysis {self.id} - {self.video_filename}>'


class AnalysisResult(db.Model):
    """Модель результатов анализа"""
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False, unique=True, index=True)
    transcript = db.Column(db.Text, nullable=True)
    transcript_with_timestamps = db.Column(db.Text, nullable=True)
    metrics = db.Column(db.Text, nullable=False)  # JSON строка с метриками
    feedback = db.Column(db.Text, nullable=True)  # Фидбэк от GigaChat
    plots_paths = db.Column(db.Text, nullable=True)  # JSON строка с путями к графикам
    audio_features = db.Column(db.Text, nullable=True)  # JSON строка с аудио-данными
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_metrics(self):
        """Получить метрики как dict"""
        try:
            return json.loads(self.metrics) if self.metrics else {}
        except:
            return {}
    
    def set_metrics(self, metrics_dict):
        """Сохранить метрики как JSON"""
        self.metrics = json.dumps(metrics_dict, ensure_ascii=False)
    
    def get_plots_paths(self):
        """Получить пути к графикам как list"""
        try:
            return json.loads(self.plots_paths) if self.plots_paths else []
        except:
            return []
    
    def set_plots_paths(self, paths_list):
        """Сохранить пути как JSON"""
        self.plots_paths = json.dumps(paths_list, ensure_ascii=False)
    
    def get_audio_features(self):
        """Получить аудио-характеристики как dict"""
        try:
            return json.loads(self.audio_features) if self.audio_features else {}
        except:
            return {}
    
    def set_audio_features(self, features_dict):
        """Сохранить аудио-характеристики как JSON"""
        self.audio_features = json.dumps(features_dict, ensure_ascii=False)
    
    def __repr__(self):
        return f'<AnalysisResult for Analysis {self.analysis_id}>'


class Exercise(db.Model):
    """Модель упражнения (из базы упражнений)"""
    __tablename__ = 'exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)  # tempo/filler_words/pauses/diction/breathing/practice
    difficulty = db.Column(db.String(20), nullable=False)  # beginner/intermediate/advanced
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    duration_minutes = db.Column(db.Integer, default=5)
    practice_text = db.Column(db.Text, nullable=True)  # Текст для практики (если есть)
    demo_url = db.Column(db.String(500), nullable=True)  # Ссылка на демо-видео
    
    # Связи
    progress_records = db.relationship('UserProgress', backref='exercise', lazy='dynamic')
    
    def __repr__(self):
        return f'<Exercise {self.id} - {self.title}>'


class UserProgress(db.Model):
    """Модель прогресса пользователя (выполненные упражнения)"""
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=True, index=True)  # Связь с конкретным анализом
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text, nullable=True)  # Заметки пользователя
    
    def __repr__(self):
        return f'<UserProgress {self.user_id} - Exercise {self.exercise_id}>'
