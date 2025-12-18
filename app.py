# app.py

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from flask_login import LoginManager, login_required, current_user
import os
import re
import threading
import time
import json
from pathlib import Path
import logging
from werkzeug.utils import secure_filename
import markdown

# Импорты из наших модулей
from ai_presenter_coach import analyze_video
from config import config
from models import db, User, Analysis, AnalysisResult, Exercise, UserProgress
from database import init_db
from auth import auth_bp

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask приложения
app = Flask(__name__)

# Создаем папку instance если её нет (ДО инициализации БД!)
os.makedirs('instance', exist_ok=True)

# Базовые настройки
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = config.SECRET_KEY

# Настройки БД с абсолютным путем для Windows
db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logger.info(f"📍 Путь к БД: {db_path}")
# ===================================================

# Инициализация базы данных
init_db(app)
# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Куда перенаправлять неавторизованных
login_manager.login_message = '🔒 Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'info'

# Регистрация Blueprint для аутентификации
app.register_blueprint(auth_bp)

# Разрешенные расширения видео
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Словарь для отслеживания задач (временное решение, в продакшене использовать Redis)
tasks = {}


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя по ID для Flask-Login"""
    return User.query.get(int(user_id))


def allowed_file(filename):
    """Проверка разрешенного расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def markdown_to_html(text):
    """Конвертирует Markdown в безопасный HTML"""
    if not text:
        return ""
    try:
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            if re.match(r'^\d+\.\s+', line):
                line = f'<div class="criterion-line">{line}</div>'
            processed_lines.append(line)
        
        text = '\n'.join(processed_lines)
        html = markdown.markdown(text, extensions=['extra', 'nl2br'])
        return html
    except Exception as e:
        logger.error(f"Ошибка конвертации Markdown: {e}")
        return text


@app.route('/')
def index():
    """Главная страница"""
    # Показываем index.html (там уже есть логика для авторизованных/неавторизованных)
    return render_template('index.html')



@app.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет пользователя"""
    analyses = Analysis.query.filter_by(user_id=current_user.id)\
                              .order_by(Analysis.created_at.desc())\
                              .limit(5)\
                              .all()
    
    # Считаем количество доступных упражнений
    total_exercises = Exercise.query.count()
    
    return render_template('dashboard.html', 
                         user=current_user,
                         analyses=analyses,
                         total_exercises=total_exercises)



@app.route('/upload')
@login_required
def upload():
    """Загрузка видео - перенаправление на главную"""
    return redirect(url_for('index'))



@app.route('/history')
@login_required
def history():
    """История анализов пользователя"""
    analyses = Analysis.query.filter_by(user_id=current_user.id)\
                              .order_by(Analysis.created_at.desc())\
                              .all()
    
    return render_template('history.html', analyses=analyses)


@app.route('/results/<int:analysis_id>')
@login_required
def results(analysis_id):
    """Просмотр результатов конкретного анализа"""
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Проверка прав доступа
    if analysis.user_id != current_user.id:
        logger.warning(f"Попытка доступа к чужому анализу: user={current_user.id}, analysis={analysis_id}")
        return "Доступ запрещен", 403
    
    result = analysis.result
    
    if not result:
        return "Результаты не найдены", 404
    
    # Получаем метрики
    metrics = result.get_metrics()
    
    # Получаем пути к графикам
    plots = result.get_plots_paths()
    
    # Конвертируем фидбэк из Markdown в HTML
    feedback_html = markdown_to_html(result.feedback)
    
    return render_template('results.html',
                         analysis=analysis,
                         metrics=metrics,
                         plots=plots,
                         feedback=feedback_html,
                         transcript=result.transcript,
                         scenario={'type': analysis.scenario_type, 'text': analysis.scenario_text})


# ============ СТАРЫЕ МАРШРУТЫ (временно оставляем для совместимости) ============

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """Запуск анализа видео"""
    if 'video' not in request.files:
        return jsonify({'error': 'Видео не найдено'}), 400
    
    video_file = request.files['video']
    
    if video_file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not allowed_file(video_file.filename):
        return jsonify({'error': 'Недопустимый формат файла'}), 400
    
    try:
        # Сохраняем файл
        filename = secure_filename(video_file.filename)
        timestamp = str(int(time.time()))
        unique_filename = f"{timestamp}_{filename}"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        video_file.save(video_path)
        
        # Получаем параметры сценария
        scenario_type = request.form.get('scenario', 'academic')
        scenario_text = request.form.get('custom_criteria', '')
        
        # Создаем запись в БД
        analysis = Analysis(
            user_id=current_user.id,
            video_filename=filename,
            video_path=video_path,
            scenario_type=scenario_type,
            scenario_text=scenario_text if scenario_type == 'custom' else None,
            status='processing'
        )
        db.session.add(analysis)
        db.session.commit()
        
        task_id = f"task_{timestamp}"
        tasks[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Начинаем анализ...',
            'analysis_id': analysis.id
        }
        
        # Запускаем анализ в отдельном потоке
        thread = threading.Thread(
            target=process_video_task,
            args=(task_id, video_path, analysis.id, {'type': scenario_type, 'text': scenario_text})
        )
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'redirect': url_for('processing', task_id=task_id)
        })
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке видео: {e}")
        return jsonify({'error': str(e)}), 500


def process_video_task(task_id, video_path, analysis_id, scenario):
    """Обработка видео в фоновом режиме"""
    
    # ВАЖНО: Оборачиваем всё в контекст приложения!
    with app.app_context():
        try:
            tasks[task_id]['progress'] = 10
            tasks[task_id]['message'] = 'Извлечение аудио...'
            
            logger.info(f"Начало обработки видео: {video_path}")
            
            # Запускаем анализ
            # Создаем callback для обновления прогресса
            def progress_callback(progress, message):
                tasks[task_id]['progress'] = progress
                tasks[task_id]['message'] = message
                    
            # Запускаем анализ с callback
            result = analyze_video(video_path, use_saved=False, progress_callback=progress_callback)

            tasks[task_id]['progress'] = 98
            tasks[task_id]['message'] = 'Сохранение в базу данных...'

            
            # Получаем анализ из БД
            analysis = Analysis.query.get(analysis_id)
            
            if not analysis:
                raise Exception("Анализ не найден в БД")
            
            # Создаем результат анализа
            analysis_result = AnalysisResult(
                analysis_id=analysis_id,
                transcript=result.get('transcript', ''),
                transcript_with_timestamps=result.get('transcript_with_timestamps', ''),
                feedback=result.get('feedback', '')
            )
            
            # Сохраняем метрики
            metrics = result.get('results', {})
            if hasattr(metrics, 'to_dict'):
                metrics = metrics.to_dict()
            analysis_result.set_metrics(metrics)
            
            # Сохраняем пути к графикам (относительные пути для HTML)
            plots_folder = Path(config.PLOTS_FOLDER)
            if plots_folder.exists():
                plot_files = list(plots_folder.glob('*.png'))
                # Используем только имена файлов (без полного пути)
                plots = [p.name for p in plot_files]
                analysis_result.set_plots_paths(plots)
                logger.info(f"Найдено {len(plots)} графиков")
            
            # Сохраняем аудио-характеристики если есть
            if 'audio_features' in result and result['audio_features']:
                audio_features = result['audio_features']
                if hasattr(audio_features, 'to_dict'):
                    audio_features = audio_features.to_dict()
                analysis_result.set_audio_features(audio_features)
            
            # Обновляем статус анализа
            analysis.status = 'completed'
            
            # Сохраняем в БД
            db.session.add(analysis_result)
            db.session.commit()
            
            logger.info(f"✅ Анализ {analysis_id} успешно сохранен в БД")
            
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['progress'] = 100
            tasks[task_id]['message'] = 'Анализ завершен!'
            # Передаем только ID, URL сформируем на фронтенде
            tasks[task_id]['analysis_id'] = analysis_id

            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки видео: {e}", exc_info=True)
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = f'Ошибка: {str(e)}'
            
            # Обновляем статус в БД
            try:
                analysis = Analysis.query.get(analysis_id)
                if analysis:
                    analysis.status = 'error'
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"Ошибка обновления статуса в БД: {db_error}")




@app.route('/processing/<task_id>')
@login_required
def processing(task_id):
    """Страница обработки видео"""
    return render_template('processing.html', task_id=task_id)


@app.route('/status/<task_id>')
@login_required
def status(task_id):
    """API для проверки статуса обработки"""
    task = tasks.get(task_id, {'status': 'not_found'})
    return jsonify(task)


@app.route('/static/plots/<filename>')
@login_required
def serve_plot(filename):
    """Отдача графиков"""
    return send_from_directory(config.PLOTS_FOLDER, filename)

@app.route('/analysis/<int:analysis_id>/delete', methods=['POST'])
@login_required
def delete_analysis(analysis_id):
    """Удаление анализа"""
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Проверка прав доступа
    if analysis.user_id != current_user.id:
        logger.warning(f"Попытка удаления чужого анализа: user={current_user.id}, analysis={analysis_id}")
        flash('❌ Доступ запрещен', 'danger')
        return redirect(url_for('history'))
    
    try:
        # Удаляем видео файл если существует
        if analysis.video_path and os.path.exists(analysis.video_path):
            try:
                os.remove(analysis.video_path)
                logger.info(f"Удален видео файл: {analysis.video_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить видео файл: {e}")
        
        # Удаляем связанные графики если есть результат
        if analysis.result:
            plots = analysis.result.get_plots_paths()
            if plots:
                plots_folder = Path(config.PLOTS_FOLDER)
                for plot_name in plots:
                    plot_path = plots_folder / plot_name
                    if plot_path.exists():
                        try:
                            os.remove(plot_path)
                            logger.info(f"Удален график: {plot_name}")
                        except Exception as e:
                            logger.warning(f"Не удалось удалить график {plot_name}: {e}")
        
        # Удаляем связанные записи прогресса
        UserProgress.query.filter_by(analysis_id=analysis_id).delete()
        
        # Удаляем результат анализа (если есть)
        if analysis.result:
            db.session.delete(analysis.result)
        
        # Удаляем сам анализ
        db.session.delete(analysis)
        db.session.commit()
        
        flash('✅ Анализ успешно удален', 'success')
        logger.info(f"Удален анализ {analysis_id} пользователя {current_user.id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка удаления анализа: {e}", exc_info=True)
        flash('❌ Ошибка при удалении анализа', 'danger')
    
    return redirect(url_for('history'))


@app.route('/analysis/<int:analysis_id>/trainer')
@login_required
def trainer(analysis_id):
    """Тренажер для конкретного анализа"""
    from trainer import select_exercises_for_metrics, generate_ai_training_plan, get_user_progress_for_analysis
    
    # Получаем анализ
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Проверка прав доступа
    if analysis.user_id != current_user.id:
        logger.warning(f"Попытка доступа к чужому тренажеру: user={current_user.id}, analysis={analysis_id}")
        flash('❌ Доступ запрещен', 'danger')
        return redirect(url_for('history'))
    
    # Проверяем что анализ завершен
    if analysis.status != 'completed':
        flash('⚠️ Анализ еще не завершен. Дождитесь окончания обработки.', 'warning')
        return redirect(url_for('history'))
    
    # Получаем результаты
    result = analysis.result
    if not result:
        flash('❌ Результаты анализа не найдены', 'danger')
        return redirect(url_for('history'))
    
    # Получаем метрики
    metrics = result.get_metrics()
    
    # Подбираем упражнения
    exercises = select_exercises_for_metrics(metrics, limit=7)
    
    if not exercises:
        flash('⚠️ Не удалось подобрать упражнения. Попробуйте позже.', 'warning')
        return redirect(url_for('results', analysis_id=analysis_id))
    
    # Генерируем план от AI
    try:
        ai_plan = generate_ai_training_plan(
            transcript=result.transcript or "",
            metrics=metrics,
            exercises=exercises
        )
        ai_plan_html = markdown_to_html(ai_plan)
    except Exception as e:
        logger.error(f"Ошибка генерации плана: {e}")
        ai_plan_html = "<p>Не удалось сгенерировать план. Используйте упражнения ниже.</p>"
    
    # Получаем прогресс пользователя
    completed_exercises = get_user_progress_for_analysis(current_user.id, analysis_id)
    completed_ids = [p.exercise_id for p in completed_exercises]
    
    return render_template('trainer.html',
                         analysis=analysis,
                         metrics=metrics,
                         exercises=exercises,
                         ai_plan=ai_plan_html,
                         completed_ids=completed_ids)


@app.route('/exercise/<int:exercise_id>/complete', methods=['POST'])
@login_required
def complete_exercise(exercise_id):
    """Отметить упражнение как выполненное"""
    from trainer import mark_exercise_completed
    
    # Получаем analysis_id из формы
    analysis_id = request.form.get('analysis_id')
    notes = request.form.get('notes', '')
    
    if not analysis_id:
        return jsonify({'success': False, 'error': 'analysis_id не указан'}), 400
    
    try:
        analysis_id = int(analysis_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'Неверный analysis_id'}), 400
    
    # Проверяем что анализ принадлежит пользователю
    analysis = Analysis.query.get(analysis_id)
    if not analysis or analysis.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    # Отмечаем упражнение
    success = mark_exercise_completed(
        user_id=current_user.id,
        analysis_id=analysis_id,
        exercise_id=exercise_id,
        notes=notes
    )
    
    if success:
        return jsonify({'success': True, 'message': '✅ Упражнение отмечено!'})
    else:
        return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    
@app.route('/progress')
@login_required
def progress():
    """Страница прогресса и статистики пользователя"""
    
    # Получаем статистику
    stats = current_user.get_statistics()
    
    # Получаем временную линию для графиков
    timeline = current_user.get_progress_timeline()
    
    # Получаем рекомендации
    suggestions = current_user.get_improvement_suggestions()
    
    # Последние выполненные упражнения
    recent_progress = UserProgress.query.filter_by(user_id=current_user.id)\
                                        .order_by(UserProgress.completed_at.desc())\
                                        .limit(5)\
                                        .all()
    
    return render_template('progress.html',
                         stats=stats,
                         timeline=timeline,
                         suggestions=suggestions,
                         recent_progress=recent_progress)

@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    
    # Получаем статистику
    stats = current_user.get_statistics()
    
    # Последние 5 анализов
    recent_analyses = current_user.analyses.order_by(Analysis.created_at.desc()).limit(5).all()
    
    return render_template('profile.html',
                         stats=stats,
                         recent_analyses=recent_analyses)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Редактирование профиля"""
    from forms import RegistrationForm
    
    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        
        if new_username and len(new_username) >= 2:
            current_user.username = new_username
            db.session.commit()
            flash('✅ Профиль успешно обновлен!', 'success')
            logger.info(f"Пользователь {current_user.id} обновил профиль")
        else:
            flash('❌ Имя должно быть минимум 2 символа', 'danger')
        
        return redirect(url_for('profile'))
    
    return redirect(url_for('profile'))


# ============= ОБРАБОТЧИКИ ОШИБОК =============

@app.errorhandler(404)
def not_found_error(error):
    """Обработка 404 ошибки"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Обработка 500 ошибки"""
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden_error(error):
    """Обработка 403 ошибки"""
    return render_template('errors/403.html'), 403


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
