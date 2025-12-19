# Полностью переписанный ai_presenter_coach.py с заменой Whisper на AssemblyAI
# --- Импорты ---
import assemblyai as aai
import torch
from datetime import timedelta
import ffmpeg
from gigachat_analyzer import analyzer
from collections import Counter
import re
import os
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from visualizer import generate_plots
from audio_analyzer import analyze_audio_features
from config import config

# Логирование
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Структуры данных ---
@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: List[str]

    @property
    def duration(self):
        return self.end - self.start

    @property
    def word_count(self):
        return len(self.words)

    @property
    def words_per_second(self):
        return self.word_count / self.duration if self.duration > 0 else 0

@dataclass
class Pause:
    start: float
    end: float
    duration: float

    def to_dict(self):
        return {
            "start": str(timedelta(seconds=self.start)),
            "end": str(timedelta(seconds=self.end)),
            "duration": round(self.duration, 2)
        }

@dataclass
class FillerWord:
    word: str
    segment_index: int
    segment_start: float
    context: str

@dataclass
class Repetition:
    word: str
    count: int
    occurrences: List[float]

@dataclass
class AnalysisResults:
    segments: List[Segment]
    pauses: List[Pause]
    filler_words: List[FillerWord]
    repetitions: List[Repetition]
    avg_tempo: float
    speed_issues: List[Dict]
    audio_features: Optional[Dict]
    total_duration: float
    total_words: int

    def to_dict(self):
        return {
            "avg_tempo": round(self.avg_tempo, 2),
            "total_duration": round(self.total_duration, 2),
            "total_words": self.total_words,
            "pauses_count": len(self.pauses),
            "filler_words_count": len(self.filler_words),
            "repetitions_count": len(self.repetitions),
            "speed_issues_count": len(self.speed_issues),
        }

# --- Загрузка слов-паразитов ---
def load_filler_words(path="filler_words.txt"):
    file = Path(path)
    if not file.exists():
        file.write_text("ну\nэто\nвот\nкак бы\nтипа\nкороче", encoding="utf-8")
        logger.warning("Создан файл filler_words.txt")
    return set(w.strip().lower() for w in file.read_text(encoding="utf-8").splitlines() if w.strip())

# --- Извлечение аудио ---
def extract_audio_from_video(video, audio):
    try:
        Path(audio).parent.mkdir(exist_ok=True, parents=True)
        (
            ffmpeg
            .input(video)
            .output(audio, acodec="pcm_s16le", ac=1, ar="16k")
            .overwrite_output()
            .run()
        )
        return True
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return False


load_dotenv()
# --- Транскрибация через AssemblyAI ---
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


def transcribe_audio_with_timestamps(audio_path):
    logger.info(f"AssemblyAI: начало транскрибации {audio_path}")

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(
        audio_path,
        config=aai.TranscriptionConfig(
            language_code="ru",
            speaker_labels=False,
            punctuate=True,
            format_text=True,
        )
    )

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(transcript.error)

    full_text = transcript.text
    segments = []
    formatted = []

    current_text = ""
    current_start = None
    current_end = None

    for w in transcript.words:
        word = w.text
        start = w.start / 1000
        end = w.end / 1000

        if current_start is None:
            current_start = start

        current_end = end
        current_text += " " + word

        if word.endswith(('.', '!', '?', '…')):
            words = re.findall(r"\b\w+\b", current_text.lower())
            seg = Segment(current_start, current_end, current_text.strip(), words)
            segments.append(seg)
            t = str(timedelta(seconds=int(current_start)))
            formatted.append(f"[{t}] {seg.text}")
            current_text = ""
            current_start = None
            current_end = None

    if current_text.strip():
        words = re.findall(r"\b\w+\b", current_text.lower())
        seg = Segment(current_start, current_end, current_text.strip(), words)
        segments.append(seg)
        t = str(timedelta(seconds=int(current_start)))
        formatted.append(f"[{t}] {seg.text}")

    return full_text, "\n".join(formatted), segments

# --- Анализ речи ---
def analyze_delivery(segments, filler_words, speed_threshold=config.SPEED_THRESHOLD, pause_threshold=config.PAUSE_THRESHOLD):
    pauses = []
    fillers = []
    repetitions = []
    speed_issues = []

    total_duration = 0
    total_words = 0
    all_words = []

    for i, seg in enumerate(segments):
        for f in filler_words:
            if f in seg.text.lower():
                fillers.append(FillerWord(f, i, seg.start, seg.text))

        total_duration += seg.duration
        total_words += seg.word_count
        all_words.extend(seg.words)

        if seg.words_per_second > speed_threshold:
            speed_issues.append({"time": seg.start, "wps": seg.words_per_second, "text": seg.text})

        if i > 0:
            gap = seg.start - segments[i - 1].end
            if gap > pause_threshold:
                pauses.append(Pause(segments[i - 1].end, seg.start, gap))

    c = Counter(all_words)
    for word, count in c.items():
        if count > config.REPETITION_THRESHOLD:
            occ = []
            for seg in segments:
                if word in seg.words:
                    occ.append(seg.start)
            repetitions.append(Repetition(word, count, occ))

    avg_tempo = total_words / total_duration if total_duration else 0

    return AnalysisResults(
        segments, pauses, fillers, repetitions,
        avg_tempo, speed_issues, None, total_duration, total_words
    )

# --- Сохранение результатов ---
def save_results(transcript, transcript_ts, results, audio_features, video_name):
    """
    Сохранение результатов анализа
    ВНИМАНИЕ: Теперь сохраняем только транскрипты и графики в файлы,
    основные данные будут в БД
    """
    import time
    from pathlib import Path
    
    stamp = int(time.time())
    
    # Создаем папку для результатов этого анализа
    results_dir = Path(config.RESULTS_FOLDER) / f"{stamp}_{video_name}"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем транскрипты (для бэкапа)
    (results_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
    (results_dir / "transcript_with_timestamps.txt").write_text(transcript_ts, encoding="utf-8")
    
    # Формируем данные для возврата (будут сохранены в БД)
    data = {
        "metrics": results.to_dict(),
        "pauses": [p.to_dict() for p in results.pauses],
        "filler_words": [
            {"word": f.word, "time": f.segment_start, "context": f.context} 
            for f in results.filler_words
        ],
        "repetitions": [
            {"word": r.word, "count": r.count, "occ": r.occurrences} 
            for r in results.repetitions
        ]
    }
    
    # Сохраняем JSON для бэкапа
    (results_dir / "analysis_results.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), 
        encoding="utf-8"
    )
    
    logger.info(f"Результаты сохранены в {results_dir}")
    
    # Возвращаем путь к папке для использования в app.py
    return str(results_dir)


# --- Основная функция ---
def analyze_video(video_path, use_saved=False, progress_callback=None, scenario=None):
    """
    Главная функция анализа видео
    
    Args:
        video_path: путь к видео файлу
        use_saved: использовать сохраненные данные (для тестирования)
        progress_callback: функция для обновления прогресса (progress, message)
        scenario: информация о сценарии выступления (dict с 'type' и 'text')
    """
    
    def update_progress(progress: int, message: str):
        """Обновить прогресс если callback задан"""
        if progress_callback:
            progress_callback(progress, message)
        logger.info(f"Прогресс: {progress}% - {message}")
    
    video = Path(video_path)
    audio = Path(config.AUDIO_FOLDER) / f"{video.stem}.wav"
    filler_words = load_filler_words()
    
    # Шаг 1: Извлечение аудио (10-25%)
    update_progress(10, 'Извлечение аудио из видео...')
    if not extract_audio_from_video(str(video), str(audio)):
        raise RuntimeError("Не удалось извлечь аудио")
    update_progress(25, 'Аудио успешно извлечено')
    
    # Шаг 2: Транскрипция (25-55%)
    update_progress(30, 'Распознавание речи через AssemblyAI...')
    transcript, transcript_ts, segments = transcribe_audio_with_timestamps(str(audio))
    update_progress(55, 'Речь успешно распознана')
    
    # Шаг 3: Анализ метрик (55-70%)
    update_progress(60, 'Анализ темпа речи и пауз...')
    results = analyze_delivery(segments, filler_words)
    update_progress(70, 'Базовый анализ завершен')
    
    # Шаг 4: Анализ аудио (70-75%)
    update_progress(72, 'Анализ аудио характеристик...')
    try:
        features = analyze_audio_features(str(audio), segments)
        results.audio_features = features
        logger.info(f"[AUDIO] Данные получены: {features}")
        update_progress(75, 'Аудио анализ завершен')
    except Exception as e:
        logger.warning(f"Анализ аудио не выполнен: {e}")
        update_progress(75, 'Аудио анализ пропущен')
    
    # Шаг 5: Генерация графиков (75-90%)
    update_progress(78, 'Создание графика темпа речи...')
    generate_plots(results, config.PLOTS_FOLDER, progress_callback=lambda p, m: update_progress(78 + p, m))
    update_progress(90, 'Все графики созданы')
    
    # Шаг 6: GigaChat анализ (90-95%)
    update_progress(92, 'Отправка в GigaChat для анализа...')
    feedback = analyzer.analyze_speech(transcript, results.to_dict(), scenario=scenario) if config.SEND_TO_GIGACHAT else "Gigachat disabled"
    update_progress(95, 'Фидбэк от AI получен')
    
    # Шаг 7: Сохранение (95-98%)
    update_progress(96, 'Сохранение результатов...')
    save_results(transcript, transcript_ts, results, results.audio_features, video.stem)
    Path("feedback_report.txt").write_text(feedback, encoding="utf-8")
    update_progress(98, 'Результаты сохранены')
    
    logger.info("Анализ завершен успешно")
    
    return {
        "transcript": transcript,
        "transcript_with_timestamps": transcript_ts,
        "results": results.to_dict(),
        "feedback": feedback,
        "audio_features": results.audio_features
    }



# --- CLI ---
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--no-gigachat", action="store_true")
    a = p.parse_args()

    if a.no_gigachat:
        config.SEND_TO_GIGACHAT = False

    analyze_video(a.video)
