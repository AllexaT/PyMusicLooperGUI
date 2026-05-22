from typing import Tuple, Dict
import librosa
import numpy as np

from models.audio import MLAudio
from infrastructure.exceptions import LoopNotFoundError
from .utils import _softmax


def _analyze_audio(
    mlaudio: MLAudio, skip_beat_analysis=False
) -> Tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    """Performs the main audio analysis required

    Args:
        mlaudio (MLAudio): the MLAudio object to perform analysis on
        skip_beat_analysis (bool, optional): Skips beat analysis if true and returns None for bpm and beats. Defaults to False.

    Returns:
        Tuple[np.ndarray, np.ndarray, float, np.ndarray]: a tuple containing the (chroma spectrogram, power spectrogram in dB, tempo/bpm, frame indices of detected beats)
    """
    S = librosa.core.stft(y=mlaudio.audio)
    S_power = np.abs(S) ** 2
    S_weighed = librosa.core.perceptual_weighting(
        S=S_power, frequencies=librosa.fft_frequencies(sr=mlaudio.rate)
    )
    mel_spectrogram = librosa.feature.melspectrogram(
        S=S_weighed, sr=mlaudio.rate, n_mels=128, fmax=8000
    )
    chroma = librosa.feature.chroma_stft(S=S_power)
    power_db = librosa.power_to_db(S_weighed, ref=np.median)

    if skip_beat_analysis:
        return chroma, power_db, None, None

    try:
        onset_env = librosa.onset.onset_strength(S=mel_spectrogram)

        pulse = librosa.beat.plp(onset_envelope=onset_env)
        beats_plp = np.flatnonzero(librosa.util.localmax(pulse))
        bpm, beats = librosa.beat.beat_track(onset_envelope=onset_env)

        beats = np.union1d(beats, beats_plp)
        beats = np.sort(beats)

        if isinstance(bpm, np.ndarray):
            bpm = bpm[0]
    except Exception as e:
        raise LoopNotFoundError(f"Beat analysis failed for \"{mlaudio.filename}\". Cannot continue.") from e

    return chroma, power_db, bpm, beats


def analyze_music_structure(mlaudio: MLAudio) -> Dict:
    """分析音樂的基本結構，找出重複段落和主題部分

    Args:
        mlaudio (MLAudio): MLAudio 物件，包含音訊數據

    Returns:
        Dict: 包含音樂結構分析結果的字典，包括：
            - segments: 音樂段落的邊界點
            - similarity_matrix: 自相似矩陣
            - chord_features: 和弦特徵
            - chord_labels: 和弦標籤序列
            - mfcc: MFCC特徵
    """
    # 計算梅爾頻譜圖
    S = librosa.feature.melspectrogram(
        y=mlaudio.audio, 
        sr=mlaudio.rate,
        n_mels=128,
        fmax=8000
    )
    
    # 計算音樂的自相似矩陣
    similarity_matrix = librosa.segment.recurrence_matrix(
        S,
        mode='affinity',
        sym=True
    )
    
    # 使用 librosa 的 laplacian segmentation 找出段落
    segments = librosa.segment.agglomerative(S, k=8)
    
    # 計算和弦特徵
    chromagram = librosa.feature.chroma_cqt(
        y=mlaudio.audio, 
        sr=mlaudio.rate
    )
    chord_features = np.sum(chromagram, axis=1)
    
    # 新增：和弦標籤序列
    chord_labels = _detect_chord_labels(chromagram, mlaudio.rate)
    
    # 新增MFCC特徵
    mfcc = librosa.feature.mfcc(
        y=mlaudio.audio,
        sr=mlaudio.rate,
        n_mfcc=13,
        hop_length=512
    )
    
    return {
        'segments': segments,
        'similarity_matrix': similarity_matrix,
        'chord_features': chord_features,
        'chord_labels': chord_labels,
        'mfcc': mfcc
    }


def _detect_chord_labels(chromagram, sr):
    maj_template = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0])
    min_template = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0])
    templates = []
    labels = []
    for i in range(12):
        templates.append(np.roll(maj_template, i))
        labels.append(librosa.midi_to_note(60 + i, unicode=False)[:-1] + ':maj')
    for i in range(12):
        templates.append(np.roll(min_template, i))
        labels.append(librosa.midi_to_note(60 + i, unicode=False)[:-1] + ':min')
    templates = np.stack(templates)
    scores = np.dot(templates, chromagram)
    scores = _softmax(scores, axis=0)  # 修正：轉為機率分布
    transition_matrix = np.ones((24, 24)) / 24
    path = librosa.sequence.viterbi(scores, transition_matrix)
    chord_labels = [labels[i] for i in path]
    return chord_labels
