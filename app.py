# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import re
import threading
import time
import json
from pathlib import Path
import logging
from werkzeug.utils import secure_filename
import markdown  # Для конвертации Markdown в HTML

from ai_presenter_coach import analyze_video
from config import config

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = os.urandom(24)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

tasks = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def markdown_to_html(text):
    """Конвертирует Markdown в безопасный HTML с улучшенной поддержкой кастомных форматов"""
    if not text:
        return ""
    
    try:
        # Улучшенная обработка кастомного формата (сохранение нумерации и структуры)
        # Сначала защищаем нумерацию и специальные символы
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Если строка начинается с цифры и точки (нумерация критериев)
            if re.match(r'^\d+\.\s+', line):
                # Обернем в div для сохранения структуры
                line = f'<div class="criteria-item">{line}</div>'
            # Если строка начинается с "оценивается:" или "шкала оценки:"
            elif line.strip().startswith('оценивается:') or line.strip().startswith('шкала оценки:'):
                line = f'<div class="criteria-section">{line}</div>'
            # Если строка начинается с "•" (подпункты)
            elif line.strip().startswith('•'):
                line = f'<div class="subpoint">{line}</div>'
            
            processed_lines.append(line)
        
        processed_text = '\n'.join(processed_lines)
        
        # Конвертируем Markdown в HTML
        html = markdown.markdown(
            processed_text, 
            extensions=['extra', 'tables', 'nl2br', 'fenced_code'],
            output_format='html5'
        )
        
        # Добавляем стили для лучшего отображения
        html = html.replace('<h1>', '<h1 class="mt-4 mb-3">')
        html = html.replace('<h2>', '<h2 class="mt-3 mb-2">')
        html = html.replace('<h3>', '<h3 class="mt-2 mb-2">')
        
        # Специальные стили для кастомного формата
        html = html.replace('<div class="criteria-item">', '<div class="criteria-item mb-3 p-3 border-start border-4 border-primary">')
        html = html.replace('<div class="criteria-section">', '<div class="criteria-section mb-2 fw-bold">')
        html = html.replace('<div class="subpoint">', '<div class="subpoint ms-4 mb-1">')
        
        # Обработка разделителей
        html = html.replace('--- ТЕХНИЧЕСКИЕ МЕТРИКИ РЕЧИ ---', 
                          '<hr class="my-4"><h3 class="text-warning">🎤 Технические метрики речи</h3>')
        html = html.replace('--- ОБЩИЕ ВЫВОДЫ И РЕКОМЕНДАЦИИ ---',
                          '<hr class="my-4"><h3 class="text-success">💡 Общие выводы и рекомендации</h3>')
        
        # Улучшаем отображение оценок
        html = re.sub(r'ОЦЕНКА:\s*(\d+)/10', 
                     r'<div class="alert alert-info mt-2"><strong>ОЦЕНКА: \1/10</strong></div>', 
                     html)
        
        # Улучшаем отображение комментариев к подпунктам
        html = html.replace(' - ОЦЕНКА: ХОРОШО', ' - <span class="text-success">✅ ХОРОШО</span>')
        html = html.replace(' - ОЦЕНКА: СРЕДНЕ', ' - <span class="text-warning">⚠️ СРЕДНЕ</span>')
        html = html.replace(' - ОЦЕНКА: ПЛОХО', ' - <span class="text-danger">❌ ПЛОХО</span>')
        
        return html
        
    except Exception as e:
        logger.error(f"Ошибка конвертации Markdown: {e}")
        # Возвращаем простой HTML, если конвертация не удалась
        return f'<div class="feedback-content">{text.replace(chr(10), "<br>")}</div>'

def update_task_progress(task_id, progress, message=""):
    """Обновляет прогресс задачи"""
    if task_id in tasks:
        tasks[task_id]['progress'] = progress
        if message:
            tasks[task_id]['message'] = message
        tasks[task_id]['last_update'] = time.time()

def process_video_task(task_id, video_path, scenario=None):
    """Фоновая задача обработки видео"""
    try:
        update_task_progress(task_id, 10, "Извлечение аудио из видео...")
        
        from ai_presenter_coach import (
            extract_audio_from_video, transcribe_audio_with_timestamps,
            analyze_delivery, load_filler_words, analyze_audio_features,
            generate_plots, save_results, AnalysisResults, Segment
        )
        from gigachat_analyzer import analyzer
        
        # 1. Извлечение аудио
        audio_path = Path(config.AUDIO_FOLDER) / f"{Path(video_path).stem}.wav"
        if not extract_audio_from_video(video_path, str(audio_path)):
            raise RuntimeError("Не удалось извлечь аудио")
        
        update_task_progress(task_id, 25, "Транскрибация речи...")
        
        # 2. Транскрибация
        transcript, transcript_with_ts, segments = transcribe_audio_with_timestamps(str(audio_path))
        
        update_task_progress(task_id, 40, "Анализ манеры речи...")
        
        # 3. Анализ речи
        filler_words = load_filler_words()
        results = analyze_delivery(segments, filler_words, config.SPEED_THRESHOLD)
        
        update_task_progress(task_id, 55, "Анализ аудио-характеристик...")
        
        # 4. Анализ аудио
        try:
            audio_features = analyze_audio_features(str(audio_path), segments)
            results.audio_features = audio_features
        except Exception as e:
            logger.warning(f"Не удалось проанализировать аудио: {e}")
            results.audio_features = None
        
        update_task_progress(task_id, 70, "Генерация графиков...")
        
        # 5. Графики
        generate_plots(results, output_dir=config.PLOTS_FOLDER)
        
        update_task_progress(task_id, 85, "Анализ структуры выступления...")
        
        # 6. Фидбэк от GigaChat с анализом структуры
        feedback = ""
        if config.SEND_TO_GIGACHAT and config.GIGACHAT_API_KEY and config.GIGACHAT_API_KEY != "ваш_ключ_здесь":
            try:
                feedback = analyzer.analyze_speech(transcript, results.to_dict(), scenario)
            except Exception as e:
                logger.error(f"Ошибка получения фидбэка: {e}")
                feedback = analyzer._get_fallback_feedback(results.to_dict())
        else:
            feedback = analyzer._get_fallback_feedback(results.to_dict())
        
        update_task_progress(task_id, 95, "Сохранение результатов...")
        
        # 7. Сохранение результатов
        video_name = Path(video_path).stem
        save_results(transcript, transcript_with_ts, results, results.audio_features, video_name)
        
        # 8. Сохранение фидбэка
        feedback_path = Path("feedback_report.txt")
        feedback_path.write_text(feedback, encoding="utf-8")
        
        # Обновляем задачу
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['results'] = {
            'transcript': transcript,
            'transcript_with_ts': transcript_with_ts,
            'results': results.to_dict(),
            'feedback': feedback,
            'scenario': scenario
        }
        tasks[task_id]['completed_at'] = time.time()
        
        logger.info(f"✅ Задача {task_id} успешно завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки задачи {task_id}: {e}")
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = str(e)
        tasks[task_id]['progress'] = 100

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Сохраняем файл
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Создаем задачу
    task_id = str(int(time.time() * 1000))
    tasks[task_id] = {
        'filename': filename,
        'filepath': filepath,
        'status': 'pending',
        'progress': 0,
        'message': 'Ожидание начала обработки...',
        'created_at': time.time(),
        'last_update': time.time(),
        'results': None,
        'error': None
    }
    # Сохраняем сценарий анализа
    scenario_type = request.form.get('scenario_type') if request.form else None
    scenario_text = request.form.get('scenario_text') if request.form else None
    tasks[task_id]['scenario'] = {
        'type': scenario_type,
        'text': scenario_text
    }
    
    # Запускаем обработку в фоне
    thread = threading.Thread(
        target=process_video_task,
        args=(task_id, filepath, tasks[task_id].get('scenario')),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'task_id': task_id,
        'message': 'Video uploaded and processing started',
        'redirect': f'/results/{task_id}'
    })

@app.route('/status/<task_id>')
def get_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    # Автоматически удаляем старые завершенные задачи (старше 1 часа)
    if task['status'] in ['completed', 'failed']:
        if time.time() - task.get('completed_at', task['created_at']) > 3600:
            del tasks[task_id]
            return jsonify({'error': 'Task expired'}), 404
    
    return jsonify({
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'message': task.get('message', ''),
        'filename': task['filename'],
        'error': task.get('error'),
        'has_results': task['status'] == 'completed'
    })

@app.route('/results/<task_id>')
def show_results(task_id):
    if task_id not in tasks:
        return render_template('error.html', error='Задача не найдена'), 404
    
    task = tasks[task_id]
    
    if task['status'] == 'pending':
        return render_template('processing.html', 
                             task_id=task_id, 
                             progress=task['progress'],
                             message=task.get('message', 'Обработка...'))
    
    if task['status'] == 'processing':
        return render_template('processing.html', 
                             task_id=task_id, 
                             progress=task['progress'],
                             message=task.get('message', 'Обработка...'))
    
    if task['status'] == 'failed':
        return render_template('error.html', 
                             error=f"Ошибка обработки: {task.get('error', 'Неизвестная ошибка')}"), 400
    
    # Загружаем результаты из задачи
    results = task.get('results')
    if not results:
        return render_template('error.html', error='Результаты не найдены'), 404
    
    # Конвертируем фидбэк из Markdown в HTML
    feedback_html = markdown_to_html(results.get('feedback', ''))
    
    # Ищем графики
    plots_dir = Path(config.PLOTS_FOLDER)
    plots = []
    
    if plots_dir.exists():
        plot_files = list(plots_dir.glob('*.png'))
        plot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for plot_file in plot_files[:6]:
            plots.append(plot_file.name)
    
    return render_template('results.html',
                         transcript=results.get('transcript', ''),
                         transcript_with_ts=results.get('transcript_with_ts', ''),
                         feedback=feedback_html,
                         raw_feedback=results.get('feedback', ''),
                         plots=plots,
                         metrics=results.get('results', {}),
                         scenario=task.get('scenario', {}))

@app.route('/api/analysis/<task_id>')
def get_analysis_data(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        return jsonify({'error': 'Analysis not complete'}), 400
    
    return jsonify(task['results'])

@app.route('/plots/<filename>')
def serve_plot(filename):
    return send_from_directory(config.PLOTS_FOLDER, filename)

@app.route('/history')
def history():
    """История анализов"""
    try:
        results_folder = Path(config.RESULTS_FOLDER)
        
        if not results_folder.exists():
            return render_template('history.html', 
                                 history=[], 
                                 message='История анализов пуста')
        
        results_dirs = list(results_folder.glob("*"))
        if not results_dirs:
            return render_template('history.html', 
                                 history=[], 
                                 message='История анализов пуста')
        
        results_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        history_items = []
        
        for dir_path in results_dirs[:20]:
            json_path = dir_path / "analysis_results.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    metrics = data.get('metrics', {})
                    
                    status_color = 'success'
                    if metrics.get('pauses_count', 0) > 5:
                        status_color = 'warning'
                    if metrics.get('filler_words_count', 0) > 10:
                        status_color = 'danger'
                    
                    history_items.append({
                        'id': dir_path.name,
                        'video_name': data['metadata'].get('video_name', 'Неизвестно'),
                        'date': data['metadata'].get('analysis_date', 'Неизвестно'),
                        'timestamp': data['metadata'].get('timestamp', 0),
                        'metrics': metrics,
                        'status_color': status_color,
                        'duration': f"{metrics.get('total_duration', 0):.0f} сек",
                        'tempo': f"{metrics.get('avg_tempo', 0):.1f}",
                        'pauses': metrics.get('pauses_count', 0),
                        'fillers': metrics.get('filler_words_count', 0),
                        'repetitions': metrics.get('repetitions_count', 0)
                    })
                except Exception as e:
                    logger.error(f"Ошибка загрузки {json_path}: {e}")
                    continue
        
        return render_template('history.html', 
                             history=history_items,
                             total=len(history_items))
        
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        return render_template('error.html', 
                             error=f"Ошибка загрузки истории: {str(e)}"), 500

@app.route('/api/recent')
def get_recent_analyses():
    """API для получения последних анализов"""
    try:
        results_dirs = list(Path(config.RESULTS_FOLDER).glob("*")) if Path(config.RESULTS_FOLDER).exists() else []
        results_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        recent = []
        
        for dir_path in results_dirs[:5]:
            json_path = dir_path / "analysis_results.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        recent.append(data['metrics'])
                except:
                    continue
        
        return jsonify({'recent': recent, 'count': len(recent)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<analysis_id>', methods=['POST'])
def delete_analysis(analysis_id):
    """Удаление анализа из истории"""
    try:
        analysis_path = Path(config.RESULTS_FOLDER) / analysis_id
        if analysis_path.exists():
            import shutil
            shutil.rmtree(analysis_path)
            return jsonify({'success': True, 'message': 'Анализ удален'})
        else:
            return jsonify({'error': 'Анализ не найден'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Создаем необходимые директории
    for folder in [config.UPLOAD_FOLDER, config.PLOTS_FOLDER, 
                   config.AUDIO_FOLDER, config.TRANSCRIPTS_FOLDER, config.RESULTS_FOLDER]:
        Path(folder).mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК AI-ТРЕНЕРА ВЫСТУПЛЕНИЙ")
    logger.info("=" * 50)
    logger.info(f"📁 Папка загрузок: {config.UPLOAD_FOLDER}")
    logger.info(f"📊 Папка графиков: {config.PLOTS_FOLDER}")
    logger.info(f"🎵 Папка аудио: {config.AUDIO_FOLDER}")
    logger.info(f"📝 Папка результатов: {config.RESULTS_FOLDER}")
    logger.info(f"🤖 GigaChat: {'ВКЛ' if config.SEND_TO_GIGACHAT else 'ВЫКЛ'}")
    logger.info("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=config.DEBUG, threaded=True)