import librosa
import numpy as np
from datetime import timedelta

def analyze_audio_features(audio_path, segments):
    """
    Анализирует аудио и возвращает:
    - Временные метки
    - Громкость (RMS) 
    - Интонацию (спектральный центройд)
    - Метрики для оценки
    """
    y, sr = librosa.load(audio_path)
    
    # Длительность аудио
    duration = librosa.get_duration(y=y, sr=sr)
    
    # Сегменты по времени (в секундах)
    start_times = [seg.start for seg in segments]
    end_times = [seg.end for seg in segments]
    
    # Параметры для анализа
    hop_length = 512
    n_fft = 2048
    
    # Вычисление STFT
    D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
    
    # Громкость (RMS)
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop_length)[0]
    
    # Спектральный центройд
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length)[0]
    
    # Время для каждого фрейма
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
    
    # Сопоставление с сегментами
    segment_rms = []
    segment_centroids = []
    
    for start, end in zip(start_times, end_times):
        mask = (times >= start) & (times <= end)
        if mask.any():
            avg_rms = np.mean(rms[mask])
            avg_centroid = np.mean(spectral_centroids[mask])
        else:
            avg_rms = 0
            avg_centroid = 0
        
        segment_rms.append(float(avg_rms))
        segment_centroids.append(float(avg_centroid))
    
    # ========== НОВЫЕ МЕТРИКИ ==========
    
    # 1. Средняя громкость (нормализуем до 0-100)
    avg_volume = float(np.mean(segment_rms) * 100) if segment_rms else 0
    
    # 2. Вариация громкости (насколько прыгает)
    volume_variance = float(np.std(segment_rms) * 100) if len(segment_rms) > 1 else 0
    
    # 3. Средняя тональность (нормализуем)
    avg_pitch = float(np.mean(segment_centroids)) if segment_centroids else 0
    
    # 4. Вариация тональности (показатель монотонности)
    pitch_variance = float(np.std(segment_centroids)) if len(segment_centroids) > 1 else 0
    
    # 5. ЭНЕРГИЯ РЕЧИ (0-100)
    # Формула: громкость (40%) + вариация тональности (60%)
    # Высокая вариация = эмоциональная речь
    normalized_pitch_var = min(pitch_variance / 1000, 1.0) * 100  # нормализуем
    energy_score = (avg_volume * 0.4) + (normalized_pitch_var * 0.6)
    energy_score = min(max(energy_score, 0), 100)  # ограничиваем 0-100
    
    return {
        'start_times': start_times,
        'segment_rms': segment_rms,
        'segment_centroids': segment_centroids,
        'avg_volume': round(avg_volume, 1),
        'volume_variance': round(volume_variance, 1),
        'avg_pitch': round(avg_pitch, 1),
        'pitch_variance': round(pitch_variance, 1),
        'energy_score': round(energy_score, 1)
    }
