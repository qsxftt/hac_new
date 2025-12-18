import librosa
import numpy as np
from datetime import timedelta

def analyze_audio_features(audio_path, segments):
    """
    Анализирует аудио и возвращает:
    - Временные метки.
    - Громкость (RMS).
    - Интонацию (спектральный центройд).
    """
    y, sr = librosa.load(audio_path)

    # Длительность аудио
    duration = librosa.get_duration(y=y, sr=sr)

    # Сегменты по времени (в секундах)
    start_times = [seg['start'] for seg in segments]
    end_times = [seg['end'] for seg in segments]

    # Параметры для анализа
    hop_length = 512
    n_fft = 2048

    # Вычисление STFT
    D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    # Громкость (RMS) из аудио (не из спектрограммы)
    # librosa.feature.rms принимает аудиосигнал
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
        segment_rms.append(avg_rms)
        segment_centroids.append(avg_centroid)

    return start_times, segment_rms, segment_centroids