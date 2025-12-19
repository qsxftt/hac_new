# -*- coding: utf-8 -*-
# trainer.py

import json
import logging
from typing import List, Dict, Any
from models import Exercise, UserProgress, db
from gigachat_analyzer import analyzer
from config import config
from gigachat.models import Messages, MessagesRole, Chat

logger = logging.getLogger(__name__)


def load_exercises_from_db() -> List[Exercise]:
    """Загрузить все упражнения из БД"""
    try:
        exercises = Exercise.query.all()
        if not exercises:
            logger.warning("[WARNING] Exercises not found in database")
            return []
        return exercises
    except Exception as e:
        logger.error(f"Ошибка загрузки упражнений: {e}")
        return []


def select_exercises_for_metrics(metrics: Dict[str, Any], limit: int = 7) -> List[Exercise]:
    """
    Подбор упражнений на основе метрик анализа (включая аудио)
    
    Args:
        metrics: Словарь с метриками (avg_tempo, pauses_count, filler_words_count, audio и т.д.)
        limit: Максимальное количество упражнений
    
    Returns:
        Список подобранных упражнений
    """
    selected = []
    
    # Получаем метрики речи
    avg_tempo = metrics.get('avg_tempo', 0)
    pauses_count = metrics.get('pauses_count', 0)
    filler_words_count = metrics.get('filler_words_count', 0)
    repetitions_count = metrics.get('repetitions_count', 0)
    
    # ========== НОВОЕ: Получаем аудио метрики ==========
    audio_features = metrics.get('audio_features', {})
    energy_score = audio_features.get('energy_score', 0) if isinstance(audio_features, dict) else 0
    avg_volume = audio_features.get('avg_volume', 0) if isinstance(audio_features, dict) else 0
    pitch_variance = audio_features.get('pitch_variance', 0) if isinstance(audio_features, dict) else 0
    
    logger.info(f"Подбор упражнений для метрик: tempo={avg_tempo}, pauses={pauses_count}, fillers={filler_words_count}, reps={repetitions_count}, energy={energy_score}, volume={avg_volume}")
    
    # Приоритеты проблем (чем больше значение, тем серьезнее проблема)
    priorities = []
    
    # 1. Проблемы с темпом
    if avg_tempo > 5:
        priorities.append(('tempo', 3, 'Слишком быстрый темп'))
    elif avg_tempo < 2:
        priorities.append(('tempo', 2, 'Слишком медленный темп'))
    
    # 2. Слова-паразиты
    if filler_words_count > 15:
        priorities.append(('filler_words', 3, 'Очень много слов-паразитов'))
    elif filler_words_count > 7:
        priorities.append(('filler_words', 2, 'Много слов-паразитов'))
    elif filler_words_count > 0:
        priorities.append(('filler_words', 1, 'Есть слова-паразиты'))
    
    # 3. Паузы
    if pauses_count > 10:
        priorities.append(('pauses', 3, 'Очень много пауз'))
    elif pauses_count > 5:
        priorities.append(('pauses', 2, 'Много пауз'))
    
    # 4. Повторы
    if repetitions_count > 5:
        priorities.append(('repetitions', 2, 'Много повторов'))
    
    # ========== НОВОЕ: Приоритеты по аудио ==========
    
    # 5. Низкая энергия речи (высокий приоритет!)
    if energy_score > 0:  # Только если есть аудио данные
        if energy_score < 40:
            priorities.append(('breathing', 3, 'Очень низкая энергия речи'))
            priorities.append(('intonation', 3, 'Монотонная речь'))
        elif energy_score < 60:
            priorities.append(('intonation', 2, 'Средняя энергия, нужна работа над интонацией'))
    
    # 6. Тихий голос
    if avg_volume > 0 and avg_volume < 30:
        priorities.append(('breathing', 3, 'Очень тихий голос'))
    elif avg_volume > 0 and avg_volume < 50:
        priorities.append(('breathing', 2, 'Тихий голос'))
    
    # 7. Монотонная интонация
    if pitch_variance > 0 and pitch_variance < 200:
        priorities.append(('intonation', 2, 'Монотонная интонация'))
    
    # Сортируем по приоритету (от большего к меньшему)
    priorities.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Определены приоритеты: {priorities}")
    
    # Подбираем упражнения по приоритетам
    exercises_added = 0
    for category, priority, description in priorities:
        if exercises_added >= limit:
            break
        
        # Ищем упражнения этой категории
        category_exercises = Exercise.query.filter_by(category=category).all()
        
        if not category_exercises:
            logger.warning(f"Нет упражнений для категории '{category}'")
            continue
        
        # Добавляем упражнения (сначала для начинающих, потом сложнее)
        for difficulty in ['beginner', 'intermediate', 'advanced']:
            if exercises_added >= limit:
                break
            
            for exercise in category_exercises:
                if exercise.difficulty == difficulty and exercise not in selected:
                    selected.append(exercise)
                    exercises_added += 1
                    logger.info(f"Добавлено упражнение: {exercise.title} ({exercise.category}, {exercise.difficulty})")
                    break
    
    # Если упражнений мало, добавляем общие (дикция, дыхание, практика)
    if exercises_added < limit:
        general_categories = ['diction', 'practice']
        for cat in general_categories:
            if exercises_added >= limit:
                break
            
            general_exercises = Exercise.query.filter_by(category=cat).limit(2).all()
            for exercise in general_exercises:
                if exercise not in selected and exercises_added < limit:
                    selected.append(exercise)
                    exercises_added += 1
    
    logger.info(f"Итого подобрано {len(selected)} упражнений")
    return selected



def generate_ai_training_plan(transcript: str, metrics: Dict[str, Any], exercises: List[Exercise]) -> str:
    """
    Генерация персонализированного плана тренировок через GigaChat
    
    Args:
        transcript: Текст транскрипции выступления
        metrics: Метрики анализа
        exercises: Список подобранных упражнений
    
    Returns:
        Текст плана тренировок от AI
    """
    
    # Проверяем доступность GigaChat
    if not config.SEND_TO_GIGACHAT or not config.GIGACHAT_API_KEY:
        logger.warning("GigaChat отключен, возвращаем стандартный план")
        return generate_fallback_plan(metrics, exercises)
    
    try:
        # Формируем список упражнений для промпта
        exercises_list = "\n".join([
            f"{i+1}. **{ex.title}** ({ex.duration_minutes} мин, {ex.difficulty})\n   Описание: {ex.description}"
            for i, ex in enumerate(exercises)
        ])
        
        # Сокращаем транскрипт для экономии токенов
        short_transcript = transcript[:1000] + "..." if len(transcript) > 1000 else transcript
        
        # Формируем промпт
        prompt = f"""Ты — профессиональный тренер по публичным выступлениям.

На основе анализа выступления создай персонализированный план тренировок на ОДНУ НЕДЕЛЮ.

МЕТРИКИ ВЫСТУПЛЕНИЯ:
• Темп речи: {metrics.get('avg_tempo', 0):.1f} слов/сек (норма: 3-4)
• Паузы (>1 сек): {metrics.get('pauses_count', 0)}
• Слова-паразиты: {metrics.get('filler_words_count', 0)}
• Повторы: {metrics.get('repetitions_count', 0)}
• Длительность: {metrics.get('total_duration', 0):.1f} сек

ОТРЫВОК ИЗ ВЫСТУПЛЕНИЯ:
{short_transcript}

ДОСТУПНЫЕ УПРАЖНЕНИЯ:
{exercises_list}

ЗАДАНИЕ:
Создай мотивирующий план тренировок на 7 дней. Для каждого дня:
1. Укажи 2-3 упражнения из списка выше (по номерам)
2. Дай краткий совет (1-2 предложения)
3. Используй эмодзи для наглядности

ФОРМАТ ОТВЕТА:
# 🎯 Твой план тренировок на неделю

## 📊 Главная цель
[Сформулируй главную цель на основе метрик - 1 предложение]

## 📅 Недельный план

**День 1: [Название]**
- Упражнения: №1, №2
- Совет: [краткий совет]

**День 2: [Название]**
...

## 💪 Мотивация
[Завершающее мотивационное сообщение - 2-3 предложения]

ВАЖНО: Будь конкретным, используй номера упражнений, сохраняй позитивный тон!
"""
        
        # Отправляем запрос в GigaChat через существующий analyzer
        logger.info("Генерация плана через GigaChat...")
        
        # ПРЯМЫЙ вызов GigaChat БЕЗ analyzer
        

        system_msg = Messages(
            role=MessagesRole.SYSTEM, 
            content="Ты — тренер по публичным выступлениям. Создай план тренировок на 7 дней строго по формату ниже. Используй НОМЕРА упражнений из списка. Будь позитивным и мотивирующим."
        )

        user_msg = Messages(
            role=MessagesRole.USER, 
            content=prompt
        )

        chat_request = Chat(
            messages=[system_msg, user_msg],
            temperature=0.3,
            max_tokens=2000
        )

        ai_plan = analyzer.client.chat(chat_request).choices[0].message.content.strip()

        
        logger.info("[SUCCESS] Training plan from GigaChat received")
        return ai_plan
        
    except Exception as e:
        logger.error(f"Ошибка генерации плана через AI: {e}")
        return generate_fallback_plan(metrics, exercises)


def generate_fallback_plan(metrics: Dict[str, Any], exercises: List[Exercise]) -> str:
    """
    Генерация стандартного плана без AI (fallback)
    
    Args:
        metrics: Метрики анализа
        exercises: Список упражнений
    
    Returns:
        Текст стандартного плана
    """
    
    # Определяем главную проблему
    main_problem = "общее улучшение навыков"
    if metrics.get('avg_tempo', 0) > 5:
        main_problem = "снижение темпа речи"
    elif metrics.get('filler_words_count', 0) > 10:
        main_problem = "избавление от слов-паразитов"
    elif metrics.get('pauses_count', 0) > 10:
        main_problem = "контроль пауз"
    
    plan = f"""# 🎯 Твой план тренировок на неделю

## 📊 Главная цель
Твоя основная задача на эту неделю — **{main_problem}**.

## 📅 Недельный план

"""
    
    # Распределяем упражнения по дням
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    
    for i, day in enumerate(days):
        plan += f"**День {i+1}: {day}**\n"
        
        # Выбираем 2 упражнения для этого дня
        day_exercises = exercises[i*2:(i+2)*2] if len(exercises) > i*2 else exercises[-2:]
        
        if day_exercises:
            plan += "- Упражнения:\n"
            for ex in day_exercises:
                plan += f"  - *{ex.title}* ({ex.duration_minutes} мин)\n"
            plan += f"- Время: ~{sum(ex.duration_minutes for ex in day_exercises)} минут\n\n"
        else:
            plan += "- Отдых и повторение пройденного\n\n"
    
    plan += """## 💪 Мотивация

Помни: каждый день тренировок приближает тебя к мастерству! 
Регулярность важнее интенсивности. Даже 10 минут в день дают результат.
Продолжай в том же духе! 🚀
"""
    
    return plan


def get_user_progress_for_analysis(user_id: int, analysis_id: int) -> List[UserProgress]:
    """
    Получить прогресс пользователя по упражнениям для конкретного анализа
    
    Args:
        user_id: ID пользователя
        analysis_id: ID анализа
    
    Returns:
        Список записей прогресса
    """
    try:
        progress = UserProgress.query.filter_by(
            user_id=user_id,
            analysis_id=analysis_id
        ).all()
        return progress
    except Exception as e:
        logger.error(f"Ошибка получения прогресса: {e}")
        return []


def mark_exercise_completed(user_id: int, analysis_id: int, exercise_id: int, notes: str = None) -> bool:
    """
    Отметить упражнение как выполненное
    
    Args:
        user_id: ID пользователя
        analysis_id: ID анализа
        exercise_id: ID упражнения
        notes: Заметки пользователя (опционально)
    
    Returns:
        True если успешно, False если ошибка
    """
    try:
        # Проверяем, не отмечено ли уже
        existing = UserProgress.query.filter_by(
            user_id=user_id,
            analysis_id=analysis_id,
            exercise_id=exercise_id
        ).first()
        
        if existing:
            logger.info(f"Упражнение {exercise_id} уже отмечено как выполненное")
            return True
        
        # Создаем новую запись
        progress = UserProgress(
            user_id=user_id,
            analysis_id=analysis_id,
            exercise_id=exercise_id,
            notes=notes
        )
        
        db.session.add(progress)
        db.session.commit()
        
        logger.info(f"[SUCCESS] Exercise {exercise_id} marked complete for user {user_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка отметки упражнения: {e}")
        return False
