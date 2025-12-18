# visualizer.py
import matplotlib.pyplot as plt
import numpy as np
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from dataclasses import asdict

logger = logging.getLogger(__name__)

def generate_plots(analysis_results, output_dir="plots"):
    """
    Генерирует графики на основе результатов анализа
    """
    import matplotlib
    matplotlib.use('Agg')  # Для серверного использования
    
    # Создаем директорию
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. График темпа речи
        _plot_tempo(analysis_results, output_path)
        
        # 2. График мусорных слов
        _plot_filler_words(analysis_results, output_path)
        
        # 3. График пауз
        if analysis_results.pauses:
            _plot_pauses(analysis_results, output_path)
        
        # 4. График громкости и интонации
        if analysis_results.audio_features:
            _plot_audio_features(analysis_results, output_path)
        
        # 5. Сводный график
        _plot_summary(analysis_results, output_path)
        
        logger.info(f"Графики сохранены в {output_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации графиков: {e}")
        raise

def _plot_tempo(analysis_results, output_path):
    """График темпа речи по времени"""
    segments = analysis_results.segments
    speed_issues = analysis_results.speed_issues
    
    if not segments:
        return
    
    times = [seg.start for seg in segments]
    speeds = [seg.words_per_second for seg in segments]
    
    plt.figure(figsize=(14, 6))
    
    # Основной график темпа
    plt.plot(times, speeds, 
             label=f'Темп речи (средний: {analysis_results.avg_tempo:.1f} слов/сек)',
             color='#2E86AB', linewidth=2, marker='o', markersize=4)
    
    # Горизонтальная линия среднего значения
    plt.axhline(y=analysis_results.avg_tempo, 
                color='#A23B72', 
                linestyle='--', 
                alpha=0.7,
                label=f'Средний темп')
    
    # Порог быстрой речи
    from config import config
    plt.axhline(y=config.SPEED_THRESHOLD, 
                color='#F18F01', 
                linestyle=':', 
                alpha=0.5,
                label=f'Порог быстрой речи ({config.SPEED_THRESHOLD} слов/сек)')
    
    # Отметки проблемных участков
    for issue in speed_issues:
        plt.axvline(x=issue['time'], 
                   color='#C73E1D', 
                   linestyle='--', 
                   alpha=0.3,
                   linewidth=1)
    
    plt.title('Темп речи по времени', fontsize=14, fontweight='bold')
    plt.xlabel('Время (секунды)', fontsize=12)
    plt.ylabel('Слова в секунду', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(output_path / 'tempo_plot.png', dpi=150, bbox_inches='tight')
    plt.close()

def _plot_filler_words(analysis_results, output_path):
    """График распределения мусорных слов"""
    from collections import Counter
    
    if not analysis_results.filler_words:
        # Создаем пустой график, если нет мусорных слов
        plt.figure(figsize=(10, 4))
        plt.text(0.5, 0.5, 'Мусорные слова не обнаружены! 👍', 
                ha='center', va='center', fontsize=14)
        plt.title('Анализ мусорных слов', fontsize=12)
        plt.axis('off')
        plt.savefig(output_path / 'filler_plot.png', dpi=150, bbox_inches='tight')
        plt.close()
        return
    
    # Подсчитываем частоту слов
    filler_counts = Counter([fw.word for fw in analysis_results.filler_words])
    words = list(filler_counts.keys())
    counts = list(filler_counts.values())
    
    # Сортируем по частоте
    sorted_indices = np.argsort(counts)
    words = [words[i] for i in sorted_indices]
    counts = [counts[i] for i in sorted_indices]
    
    plt.figure(figsize=(12, 6))
    
    bars = plt.barh(words, counts, color='#F18F01', alpha=0.8)
    
    # Добавляем значения на столбцы
    for bar, count in zip(bars, counts):
        plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{count}', va='center', fontsize=10)
    
    plt.title(f'Мусорные слова (всего: {len(analysis_results.filler_words)})', 
              fontsize=14, fontweight='bold')
    plt.xlabel('Количество использований', fontsize=12)
    plt.ylabel('Слова', fontsize=12)
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    
    plt.savefig(output_path / 'filler_plot.png', dpi=150, bbox_inches='tight')
    plt.close()

def _plot_pauses(analysis_results, output_path):
    """График пауз"""
    pauses = analysis_results.pauses
    pause_times = [pause.start for pause in pauses]
    pause_durations = [pause.duration for pause in pauses]
    
    plt.figure(figsize=(14, 6))
    
    # Гистограмма длительностей пауз
    plt.subplot(1, 2, 1)
    if pause_durations:
        plt.hist(pause_durations, bins=20, color='#C73E1D', alpha=0.7, edgecolor='black')
        plt.axvline(x=np.mean(pause_durations), color='black', linestyle='--', 
                   label=f'Среднее: {np.mean(pause_durations):.1f} сек')
    plt.title('Распределение длительностей пауз', fontsize=12)
    plt.xlabel('Длительность (секунды)', fontsize=10)
    plt.ylabel('Количество', fontsize=10)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # График пауз по времени
    plt.subplot(1, 2, 2)
    if pause_times:
        plt.scatter(pause_times, pause_durations, 
                   c=pause_durations, cmap='Reds', 
                   alpha=0.6, s=100, edgecolors='black')
        plt.colorbar(label='Длительность паузы')
    plt.title('Паузы по времени выступления', fontsize=12)
    plt.xlabel('Время выступления (секунды)', fontsize=10)
    plt.ylabel('Длительность паузы (секунды)', fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.suptitle(f'Анализ пауз (всего: {len(pauses)})', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    plt.savefig(output_path / 'pauses_plot.png', dpi=150, bbox_inches='tight')
    plt.close()

def _plot_audio_features(analysis_results, output_path):
    """Графики аудио-характеристик"""
    if not analysis_results.audio_features:
        return
    
    audio_features = analysis_results.audio_features
    
    plt.figure(figsize=(14, 8))
    
    # График громкости
    plt.subplot(2, 1, 1)
    plt.plot(audio_features['times'], audio_features['rms_values'],
             color='#2E86AB', linewidth=2, label='Громкость')
    plt.fill_between(audio_features['times'], 0, audio_features['rms_values'],
                    alpha=0.3, color='#2E86AB')
    plt.title('Громкость речи по времени', fontsize=12)
    plt.xlabel('Время (секунды)', fontsize=10)
    plt.ylabel('RMS (относительная громкость)', fontsize=10)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # График интонации
    plt.subplot(2, 1, 2)
    plt.plot(audio_features['times'], audio_features['centroids'],
             color='#A23B72', linewidth=2, label='Интонация')
    plt.fill_between(audio_features['times'], 0, audio_features['centroids'],
                    alpha=0.3, color='#A23B72')
    plt.title('Интонация по времени (спектральный центроид)', fontsize=12)
    plt.xlabel('Время (секунды)', fontsize=10)
    plt.ylabel('Частота (Гц)', fontsize=10)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.suptitle('Аудио-характеристики речи', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    plt.savefig(output_path / 'audio_features_plot.png', dpi=150, bbox_inches='tight')
    plt.close()

def _plot_summary(analysis_results, output_path):
    """Сводный график с основными метриками"""
    metrics = analysis_results.to_dict()
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Круговая диаграмма проблем
    ax1 = axes[0, 0]
    issues = [
        metrics['pauses_count'],
        metrics['filler_words_count'],
        metrics['repetitions_count'],
        metrics['speed_issues_count']
    ]
    labels = ['Паузы', 'Мусорные слова', 'Повторы', 'Быстрый темп']
    colors = ['#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0']
    
    ax1.pie(issues, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Распределение проблем', fontsize=12)
    
    # 2. Оценка темпа
    ax2 = axes[0, 1]
    tempo_score = max(0, 10 - (metrics['avg_tempo'] - 3) * 2)  # Простая оценка
    ax2.barh(['Темп речи'], [tempo_score], color='#118AB2')
    ax2.set_xlim(0, 10)
    ax2.set_xlabel('Оценка (0-10)', fontsize=10)
    ax2.set_title(f'Оценка темпа: {tempo_score:.1f}/10', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # 3. Основные метрики
    ax3 = axes[1, 0]
    ax3.axis('off')
    summary_text = (
        f"Основные метрики:\n\n"
        f"• Длительность: {metrics['total_duration']:.1f} сек\n"
        f"• Всего слов: {metrics['total_words']}\n"
        f"• Средний темп: {metrics['avg_tempo']:.1f} слов/сек\n"
        f"• Паузы (>1 сек): {metrics['pauses_count']}\n"
        f"• Мусорные слова: {metrics['filler_words_count']}\n"
        f"• Повторы (>3 раз): {metrics['repetitions_count']}"
    )
    ax3.text(0.1, 0.5, summary_text, fontsize=11, 
            verticalalignment='center', fontfamily='monospace')
    
    # 4. Рекомендации
    ax4 = axes[1, 1]
    ax4.axis('off')
    recommendations = []
    
    if metrics['avg_tempo'] > 5:
        recommendations.append("• Снизьте темп речи")
    if metrics['pauses_count'] > 5:
        recommendations.append("• Сократите длинные паузы")
    if metrics['filler_words_count'] > 10:
        recommendations.append("• Уменьшите слова-паразиты")
    if metrics['repetitions_count'] > 3:
        recommendations.append("• Избегайте повторов слов")
    
    if not recommendations:
        recommendations.append("• Отличное выступление!")
        recommendations.append("• Продолжайте в том же духе")
    
    rec_text = "Рекомендации:\n\n" + "\n".join(recommendations)
    ax4.text(0.1, 0.5, rec_text, fontsize=11, 
            verticalalignment='center', fontfamily='monospace', color='#2E86AB')
    
    plt.suptitle('СВОДКА АНАЛИЗА ВЫСТУПЛЕНИЯ', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    plt.savefig(output_path / 'summary_plot.png', dpi=150, bbox_inches='tight')
    plt.close()