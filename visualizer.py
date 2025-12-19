# -*- coding: utf-8 -*-
# visualizer.py - Улучшенная версия с красивыми графиками

import matplotlib
matplotlib.use('Agg')  # Для серверного использования
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter
from typing import Optional, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Настройка стиля
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 150

def generate_plots(results, output_folder, progress_callback=None):
    """
    Генерация всех графиков на основе результатов анализа
    
    Args:
        results: Объект AnalysisResults или словарь с результатами
        output_folder: Папка для сохранения графиков
        progress_callback: Функция обратного вызова для обновления прогресса
    """
    def update_progress(percent, message):
        if progress_callback:
            progress_callback(percent, message)
    
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Очищаем старые графики
    for old_plot in output_folder.glob('*.png'):
        try:
            old_plot.unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить старый график {old_plot}: {e}")
    
    # График 1: Темп речи
    update_progress(2, 'Создание графика темпа речи...')
    try:
        _plot_tempo_enhanced(results, output_folder)  # ← ИСПРАВЛЕНО!
    except Exception as e:
        logger.error(f"Ошибка создания графика темпа: {e}")
    
    # График 2: Слова-паразиты
    update_progress(4, 'Создание графика слов-паразитов...')
    try:
        _plot_filler_words_enhanced(results, output_folder)  # ← ИСПРАВЛЕНО!
    except Exception as e:
        logger.error(f"Ошибка создания графика слов-паразитов: {e}")
    
    # График 3: Паузы
    update_progress(6, 'Создание графика пауз...')
    try:
        if hasattr(results, 'pauses') and results.pauses:
            _plot_pauses_enhanced(results, output_folder)  # ← ИСПРАВЛЕНО!
    except Exception as e:
        logger.error(f"Ошибка создания графика пауз: {e}")
    
    # График 4: Сводка
    update_progress(8, 'Создание сводного графика...')
    try:
        _plot_summary_enhanced(results, output_folder)  # ← ИСПРАВЛЕНО!
    except Exception as e:
        logger.error(f"Ошибка создания сводного графика: {e}")
    
    # ========== НОВЫЕ ГРАФИКИ: АУДИО ==========
    
    audio_features = results.audio_features if hasattr(results, 'audio_features') else None
    
    if audio_features:
        # График 5: Громкость
        update_progress(10, 'Создание графика громкости...')
        try:
            plot_volume_over_time(audio_features, output_folder)
        except Exception as e:
            logger.error(f"Ошибка создания графика громкости: {e}")
        
        # График 6: Интонация
        update_progress(11, 'Создание графика интонации...')
        try:
            plot_pitch_over_time(audio_features, output_folder)
        except Exception as e:
            logger.error(f"Ошибка создания графика интонации: {e}")
        
        # График 7: Тепловая карта энергии
        update_progress(12, 'Создание тепловой карты...')
        try:
            plot_energy_heatmap(audio_features, output_folder)
        except Exception as e:
            logger.error(f"Ошибка создания тепловой карты: {e}")
    else:
        logger.info("Аудио данные отсутствуют, пропускаем аудио графики")
    
    update_progress(12, 'Все графики созданы')
    logger.info(f"Графики сохранены в {output_folder}")




def _plot_tempo_enhanced(analysis_results, output_path):
    """Улучшенный график темпа речи"""
    segments = analysis_results.segments
    speed_issues = analysis_results.speed_issues
    
    if not segments:
        return
    
    times = [seg.start for seg in segments]
    speeds = [seg.words_per_second for seg in segments]
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Градиентная заливка в зависимости от скорости
    colors = ['#2ecc71' if s <= 5 else '#e74c3c' for s in speeds]
    
    # Линейный график с точками
    line = ax.plot(times, speeds, 
                   color='#3498db', linewidth=2.5, 
                   label=f'Темп речи (средний: {analysis_results.avg_tempo:.1f} слов/сек)',
                   marker='o', markersize=5, markerfacecolor='white', markeredgewidth=2)
    
    # Заливка под линией
    ax.fill_between(times, speeds, alpha=0.2, color='#3498db')
    
    # Референсные линии
    ax.axhline(y=analysis_results.avg_tempo, color='#9b59b6', linestyle='--', 
              alpha=0.7, linewidth=2, label=f'Средний темп')
    
    from config import config
    ax.axhline(y=config.SPEED_THRESHOLD, color='#e74c3c', linestyle=':', 
              alpha=0.6, linewidth=2, label=f'Порог быстрой речи ({config.SPEED_THRESHOLD} слов/сек)')
    
    ax.axhline(y=3.5, color='#2ecc71', linestyle=':', 
              alpha=0.6, linewidth=2, label='Оптимальный темп (3.5 слов/сек)')
    
    # Отметки проблемных участков
    for issue in speed_issues:
        ax.axvspan(issue['time'], issue['time'] + 1, alpha=0.1, color='red')
    
    # Оформление
    ax.set_title('📊 Темп речи по времени выступления', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Время (секунды)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Слова в секунду', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right', framealpha=0.95, edgecolor='gray')
    
    # Статистика в углу
    stats_text = (f'Всего сегментов: {len(segments)}\n'
                 f'Макс. темп: {max(speeds):.1f} слов/сек\n'
                 f'Мин. темп: {min(speeds):.1f} слов/сек')
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='gray')
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=props, family='monospace')
    
    plt.tight_layout()
    plt.savefig(output_path / 'tempo_plot.png', bbox_inches='tight', facecolor='white')
    plt.close()


def _plot_filler_words_enhanced(analysis_results, output_path):
    """Улучшенный график слов-паразитов"""
    
    if not analysis_results.filler_words:
        # Красивый график для случая отсутствия филлеров
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, '[SUCCESS] No filler words detected!\n\nGreat work!', 
               ha='center', va='center', fontsize=16, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8, edgecolor='green', linewidth=2))
        ax.set_title('💬 Анализ слов-паразитов', fontsize=14, fontweight='bold')
        ax.axis('off')
        plt.savefig(output_path / 'filler_plot.png', bbox_inches='tight', facecolor='white')
        plt.close()
        return
    
    # Подсчет частоты
    filler_counts = Counter([fw.word for fw in analysis_results.filler_words])
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Левый график - топ слов
    words = list(filler_counts.keys())[:10]
    counts = [filler_counts[w] for w in words]
    
    # Сортировка
    sorted_indices = np.argsort(counts)
    words = [words[i] for i in sorted_indices]
    counts = [counts[i] for i in sorted_indices]
    
    # Градиентные цвета
    colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(words)))
    
    bars = ax1.barh(words, counts, color=colors, edgecolor='black', linewidth=0.7)
    
    # Значения на столбцах
    for bar, count in zip(bars, counts):
        ax1.text(bar.get_width() + max(counts)*0.01, bar.get_y() + bar.get_height()/2,
                f'{count}', va='center', fontweight='bold', fontsize=10)
    
    ax1.set_xlabel('Количество использований', fontsize=11, fontweight='bold')
    ax1.set_title(f'💬 Топ-10 слов-паразитов', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='x', linestyle='--')
    
    # Правый график - распределение по времени
    filler_times = [f.segment_start for f in analysis_results.filler_words]
    
    n, bins, patches = ax2.hist(filler_times, bins=20, color='#e74c3c', 
                                 alpha=0.7, edgecolor='black', linewidth=0.7)
    
    # Градиентная окраска столбцов
    for i, patch in enumerate(patches):
        patch.set_facecolor(plt.cm.Reds(0.4 + 0.5 * (i / len(patches))))
    
    ax2.set_xlabel('Время в видео (секунды)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Количество слов-паразитов', fontsize=11, fontweight='bold')
    ax2.set_title('📈 Распределение во времени', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Статистика
    stats_text = (f'Всего: {len(analysis_results.filler_words)}\n'
                 f'Уникальных: {len(filler_counts)}')
    props = dict(boxstyle='round', facecolor='mistyrose', alpha=0.9, edgecolor='#e74c3c')
    ax2.text(0.98, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props, family='monospace')
    
    plt.suptitle(f'Анализ слов-паразитов (всего: {len(analysis_results.filler_words)})', 
                fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path / 'filler_plot.png', bbox_inches='tight', facecolor='white')
    plt.close()


def _plot_pauses_enhanced(analysis_results, output_path):
    """Улучшенный график пауз"""
    pauses = analysis_results.pauses
    pause_times = [pause.start for pause in pauses]
    pause_durations = [pause.duration for pause in pauses]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Левый график - гистограмма
    n, bins, patches = ax1.hist(pause_durations, bins=20, color='#e67e22', 
                                alpha=0.7, edgecolor='black', linewidth=0.7)
    
    # Градиентная окраска
    for i, patch in enumerate(patches):
        patch.set_facecolor(plt.cm.Oranges(0.4 + 0.5 * (i / len(patches))))
    
    avg_pause = np.mean(pause_durations)
    ax1.axvline(x=avg_pause, color='black', linestyle='--', linewidth=2,
               label=f'Среднее: {avg_pause:.2f} сек')
    
    ax1.set_xlabel('Длительность паузы (секунды)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Количество', fontsize=11, fontweight='bold')
    ax1.set_title('📊 Распределение длительности пауз', fontsize=12, fontweight='bold')
    ax1.legend(framealpha=0.95, edgecolor='gray')
    ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # Правый график - scatter по времени
    scatter = ax2.scatter(pause_times, pause_durations, 
                         c=pause_durations, cmap='YlOrRd', 
                         s=120, alpha=0.7, edgecolors='black', linewidth=0.7)
    
    from config import config
    ax2.axhline(y=config.PAUSE_THRESHOLD, color='red', linestyle='--', 
               alpha=0.7, linewidth=2, label=f'Порог ({config.PAUSE_THRESHOLD} сек)')
    
    ax2.set_xlabel('Время выступления (секунды)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Длительность паузы (секунды)', fontsize=11, fontweight='bold')
    ax2.set_title('⏸️ Паузы по времени выступления', fontsize=12, fontweight='bold')
    ax2.legend(framealpha=0.95, edgecolor='gray')
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax2, pad=0.02)
    cbar.set_label('Длительность (сек)', rotation=270, labelpad=20, fontweight='bold')
    
    # Статистика
    stats_text = (f'Всего пауз: {len(pauses)}\n'
                 f'Средняя: {avg_pause:.2f} сек\n'
                 f'Макс: {max(pause_durations):.2f} сек')
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.9, edgecolor='#e67e22')
    ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=10,
            verticalalignment='top', bbox=props, family='monospace')
    
    plt.suptitle(f'Анализ пауз (всего: {len(pauses)})', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path / 'pauses_plot.png', bbox_inches='tight', facecolor='white')
    plt.close()


def _plot_summary_enhanced(analysis_results, output_path):
    """Улучшенный сводный график"""
    metrics = analysis_results.to_dict()
    
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. Основные метрики (верх, на всю ширину)
    ax1 = fig.add_subplot(gs[0, :])
    
    metric_names = ['Темп речи', 'Паузы', 'Филлеры', 'Повторы']
    metric_values = [
        metrics['avg_tempo'],
        metrics['pauses_count'],
        metrics['filler_words_count'],
        metrics['repetitions_count']
    ]
    colors = ['#3498db', '#e67e22', '#e74c3c', '#f39c12']
    
    bars = ax1.bar(metric_names, metric_values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
    
    # Значения на столбцах
    for bar, value in zip(bars, metric_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax1.set_ylabel('Значение', fontsize=11, fontweight='bold')
    ax1.set_title('📊 Основные метрики выступления', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    # 2. Pie chart - проблемы (левый нижний)
    ax2 = fig.add_subplot(gs[1, 0])
    
    problems = {
        'Быстрый темп': 1 if metrics['avg_tempo'] > 5 else 0,
        'Много пауз': 1 if metrics['pauses_count'] > 5 else 0,
        'Филлеры': 1 if metrics['filler_words_count'] > 7 else 0,
        'Повторы': 1 if metrics['repetitions_count'] > 3 else 0
    }
    
    problem_values = [v for v in problems.values() if v > 0]
    problem_labels = [k for k, v in problems.items() if v > 0]
    
    if problem_values:
        colors_pie = ['#e74c3c', '#f39c12', '#3498db', '#9b59b6'][:len(problem_values)]
        ax2.pie(problem_values, labels=problem_labels, autopct='%1.0f%%',
               colors=colors_pie, startangle=90, textprops={'fontweight': 'bold'})
        ax2.set_title('[WARNING] Issues detected', fontsize=11, fontweight='bold')
    else:
        ax2.text(0.5, 0.5, '[OK]\nNo issues\ndetected!', 
                ha='center', va='center', fontsize=12, fontweight='bold', color='green')
        ax2.set_title('[WARNING] Issues detected', fontsize=11, fontweight='bold')
        ax2.axis('off')
    
    # 3. Общая оценка (центр нижний)
    ax3 = fig.add_subplot(gs[1, 1])
    
    score = 10
    if metrics['avg_tempo'] > 5 or metrics['avg_tempo'] < 2:
        score -= 2
    if metrics['pauses_count'] > 10:
        score -= 2
    elif metrics['pauses_count'] > 5:
        score -= 1
    if metrics['filler_words_count'] > 15:
        score -= 3
    elif metrics['filler_words_count'] > 7:
        score -= 1
    if metrics['repetitions_count'] > 5:
        score -= 1
    
    score = max(0, score)
    
    # Gauge chart
    theta = np.linspace(0, np.pi, 100)
    colors_gauge = plt.cm.RdYlGn(np.linspace(0, 1, 100))
    
    for i in range(99):
        ax3.fill_between([theta[i], theta[i+1]], 0, 1, 
                        color=colors_gauge[i], alpha=0.8)
    
    # Стрелка
    angle = np.pi * (1 - score / 10)
    ax3.arrow(0, 0, 0.7 * np.cos(angle), 0.7 * np.sin(angle),
             head_width=0.12, head_length=0.12, fc='black', ec='black', linewidth=3)
    
    ax3.text(0, -0.35, f'{score}/10', ha='center', va='center', 
            fontsize=28, fontweight='bold', family='monospace')
    
    ax3.set_xlim(-1.2, 1.2)
    ax3.set_ylim(-0.5, 1.2)
    ax3.axis('off')
    ax3.set_title('⭐ Общая оценка', fontsize=11, fontweight='bold')
    
    # 4. Статистика (правый нижний)
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.axis('off')
    
    stats_text = (
        f"📊 СТАТИСТИКА\n"
        f"{'='*25}\n\n"
        f"⏱️  Длительность:\n    {metrics['total_duration']:.1f} сек\n\n"
        f"📝  Всего слов:\n    {metrics['total_words']}\n\n"
        f"🎯  Средний темп:\n    {metrics['avg_tempo']:.1f} слов/сек\n\n"
        f"⏸️  Паузы (>1 сек):\n    {metrics['pauses_count']}\n\n"
        f"💬  Слова-паразиты:\n    {metrics['filler_words_count']}\n\n"
        f"🔄  Повторы:\n    {metrics['repetitions_count']}"
    )
    
    props = dict(boxstyle='round', facecolor='lightblue', alpha=0.9, edgecolor='#3498db', linewidth=2)
    ax4.text(0.1, 0.95, stats_text, transform=ax4.transAxes, fontsize=9,
            verticalalignment='top', bbox=props, family='monospace')
    
    # 5. Рекомендации (нижний ряд, на всю ширину)
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('off')
    
    recommendations = []
    if metrics['avg_tempo'] > 5:
        recommendations.append("🎯 Снизьте темп речи - говорите спокойнее")
    elif metrics['avg_tempo'] < 2:
        recommendations.append("🎯 Увеличьте темп речи - добавьте динамики")
    
    if metrics['pauses_count'] > 8:
        recommendations.append("⏸️ Сократите длинные паузы - работайте над плавностью")
    
    if metrics['filler_words_count'] > 10:
        recommendations.append("💬 Избавляйтесь от слов-паразитов - практикуйте осознанность")
    
    if metrics['repetitions_count'] > 5:
        recommendations.append("🔄 Избегайте повторов - расширяйте словарный запас")
    
    if not recommendations:
        recommendations.append("⭐ Отличное выступление! Продолжайте в том же духе!")
        recommendations.append("💪 Все показатели в норме!")
    
    rec_text = "💡 РЕКОМЕНДАЦИИ\n" + "="*60 + "\n\n" + "\n\n".join(f"  {r}" for r in recommendations)
    
    props = dict(boxstyle='round', facecolor='#fff3cd', alpha=0.95, edgecolor='#f39c12', linewidth=2)
    ax5.text(0.5, 0.5, rec_text, transform=ax5.transAxes, fontsize=10,
            verticalalignment='center', horizontalalignment='center', bbox=props, family='monospace')
    
    plt.suptitle('📈 СВОДКА АНАЛИЗА ВЫСТУПЛЕНИЯ', fontsize=16, fontweight='bold', y=0.98)
    plt.savefig(output_path / 'summary_plot.png', bbox_inches='tight', facecolor='white')
    plt.close()



# ========== НОВЫЕ ФУНКЦИИ ДЛЯ АУДИО ГРАФИКОВ ==========

def plot_volume_over_time(audio_features, output_folder):
    """
    График громкости речи по времени
    
    Args:
        audio_features: Словарь с аудио данными
        output_folder: Папка для сохранения графика
    """
    if not audio_features or 'segment_rms' not in audio_features:
        logger.warning("Нет данных о громкости для графика")
        return
    
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    start_times = audio_features.get('start_times', [])
    segment_rms = audio_features.get('segment_rms', [])
    
    if not start_times or not segment_rms:
        logger.warning("Пустые данные громкости")
        return
    
    # Конвертируем в проценты для наглядности
    volume_percent = [rms * 100 for rms in segment_rms]
    
    plt.figure(figsize=(12, 5))
    plt.plot(start_times, volume_percent, linewidth=2, color='#3498db', label='Громкость')
    plt.fill_between(start_times, volume_percent, alpha=0.3, color='#3498db')
    
    # Линии порогов
    plt.axhline(y=30, color='#e74c3c', linestyle='--', linewidth=1, alpha=0.5, label='Слишком тихо')
    plt.axhline(y=70, color='#2ecc71', linestyle='--', linewidth=1, alpha=0.5, label='Оптимально')
    
    plt.xlabel('Время (секунды)', fontsize=12)
    plt.ylabel('Громкость (%)', fontsize=12)
    plt.title('📊 Громкость речи на протяжении выступления', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = output_folder / 'volume.png'
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    logger.info(f"График громкости сохранён: {output_path}")


def plot_pitch_over_time(audio_features, output_folder):
    """
    График интонации (тональности) речи по времени
    
    Args:
        audio_features: Словарь с аудио данными
        output_folder: Папка для сохранения графика
    """
    if not audio_features or 'segment_centroids' not in audio_features:
        logger.warning("Нет данных об интонации для графика")
        return
    
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    start_times = audio_features.get('start_times', [])
    segment_centroids = audio_features.get('segment_centroids', [])
    
    if not start_times or not segment_centroids:
        logger.warning("Пустые данные интонации")
        return
    
    plt.figure(figsize=(12, 5))
    plt.plot(start_times, segment_centroids, linewidth=2, color='#9b59b6', label='Высота голоса')
    plt.fill_between(start_times, segment_centroids, alpha=0.3, color='#9b59b6')
    
    # Средняя линия
    avg_pitch = sum(segment_centroids) / len(segment_centroids) if segment_centroids else 0
    plt.axhline(y=avg_pitch, color='#34495e', linestyle='--', linewidth=1, alpha=0.5, label=f'Среднее: {avg_pitch:.0f} Hz')
    
    plt.xlabel('Время (секунды)', fontsize=12)
    plt.ylabel('Частота (Hz)', fontsize=12)
    plt.title('🎵 Интонация речи (вариация высоты голоса)', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = output_folder / 'pitch.png'
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    logger.info(f"График интонации сохранён: {output_path}")


def plot_energy_heatmap(audio_features, output_folder):
    """
    Тепловая карта энергии речи (комбинация громкости и интонации)
    
    Args:
        audio_features: Словарь с аудио данными
        output_folder: Папка для сохранения графика
    """
    if not audio_features or 'segment_rms' not in audio_features or 'segment_centroids' not in audio_features:
        logger.warning("Нет данных для тепловой карты")
        return
    
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    start_times = audio_features.get('start_times', [])
    segment_rms = audio_features.get('segment_rms', [])
    segment_centroids = audio_features.get('segment_centroids', [])
    
    if not start_times or not segment_rms or not segment_centroids:
        logger.warning("Пустые данные для тепловой карты")
        return
    
    # Нормализуем данные для расчёта энергии
    rms_normalized = [(rms - min(segment_rms)) / (max(segment_rms) - min(segment_rms)) if max(segment_rms) > min(segment_rms) else 0.5 
                      for rms in segment_rms]
    
    centroids_normalized = [(c - min(segment_centroids)) / (max(segment_centroids) - min(segment_centroids)) if max(segment_centroids) > min(segment_centroids) else 0.5 
                            for c in segment_centroids]
    
    # Энергия = громкость (40%) + вариация интонации (60%)
    energy = [(rms * 0.4 + cent * 0.6) * 100 for rms, cent in zip(rms_normalized, centroids_normalized)]
    
    # Создаём цветовую карту
    colors = []
    for e in energy:
        if e < 40:
            colors.append('#e74c3c')  # Красный (низкая энергия)
        elif e < 60:
            colors.append('#f39c12')  # Оранжевый (средняя)
        else:
            colors.append('#2ecc71')  # Зелёный (высокая)
    
    plt.figure(figsize=(14, 3))
    plt.bar(start_times, [1]*len(start_times), width=max(start_times)/len(start_times) if start_times else 1, 
            color=colors, edgecolor='none')
    
    plt.xlabel('Время (секунды)', fontsize=12)
    plt.ylabel('', fontsize=12)
    plt.title('🔥 Тепловая карта энергии речи (красный=низкая, зелёный=высокая)', fontsize=14, fontweight='bold')
    plt.yticks([])  # Скрываем ось Y
    plt.grid(False)
    plt.tight_layout()
    
    output_path = output_folder / 'energy_heatmap.png'
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Тепловая карта энергии сохранена: {output_path}")

