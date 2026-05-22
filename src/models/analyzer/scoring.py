from typing import Optional
import numpy as np


def _calculate_loop_score(
    b1: int,
    b2: int,
    chroma: np.ndarray,
    test_duration: int,
    weights: Optional[np.ndarray] = None,
) -> float:
    """Calculates the similarity of two sequences given the starting indices `b1` and `b2` for the period of the `test_duration` specified.
        Returns the best score based on the cosine similarity of subsequent (or preceding) notes.

    Args:
        b1 (int): Frame index of the first beat to compare
        b2 (int): Frame index of the second beat to compare
        chroma (np.ndarray): The chroma spectrogram of the audio
        test_duration (int): How many frames along the chroma spectrogram to test.
        weights (np.ndarray, optional): If specified, will provide a weighted average of the note scores according to the weight array provided. Defaults to None.

    Returns:
        float: the weighted average of the cosine similarity of the notes along the tested region
    """
    lookahead_score = _calculate_subseq_beat_similarity(
        b1, b2, chroma, test_duration, weights=weights
    )
    lookbehind_score = _calculate_subseq_beat_similarity(
        b1, b2, chroma, -test_duration, weights=weights[::-1]
    )

    return max(lookahead_score, lookbehind_score)


def _calculate_subseq_beat_similarity(
    b1_start: int,
    b2_start: int,
    chroma: np.ndarray,
    test_end_offset: int,
    weights: Optional[np.ndarray] = None,
) -> float:
    """Calculates the similarity of subsequent notes of the two specified indices (b1_start, b2_start) using cosine similarity

    Args:
        b1_start (int): Starting frame index of the first beat to compare
        b2_start (int): Starting frame index of the second beat to compare
        chroma (np.ndarray): The chroma spectrogram of the audio
        test_end_offset (int): The number of frames to offset from the starting index. If negative, will be testing the preceding frames instead of the subsequent frames.
        weights (np.ndarray, optional): If specified, will provide a weighted average of the note scores according to the weight array provided. Defaults to None.

    Returns:
        float: the weighted average of the cosine similarity of the notes along the tested region
    """
    chroma_len = chroma.shape[-1]
    test_length = abs(test_end_offset)

    if test_end_offset < 0:
        b1_end = b1_start
        b2_end = b2_start
        max_negative_offset = max(test_end_offset, -b1_start, -b2_start)
        b1_start += max_negative_offset
        b2_start += max_negative_offset
        max_offset = abs(max_negative_offset)
    else:
        # clip to chroma len
        b1_end = min(b1_start + test_length, chroma_len)
        b2_end = min(b2_start + test_length, chroma_len)
        # align testing lengths
        max_offset = min(b1_end - b1_start, b2_end - b2_start)
        b1_end, b2_end = (b1_start + max_offset, b2_start + max_offset)

    dot_prod = np.einsum(
        "ij,ij->j", chroma[..., b1_start:b1_end], chroma[..., b2_start:b2_end]
    )
    b1_norm = np.linalg.norm(chroma[..., b1_start:b1_end], axis=0)
    b2_norm = np.linalg.norm(chroma[..., b2_start:b2_end], axis=0)
    denominator = b1_norm * b2_norm
    cosine_sim = np.divide(dot_prod, denominator, out=np.zeros_like(dot_prod), where=denominator != 0)

    if max_offset < test_length:
        return np.average(
            np.pad(cosine_sim, pad_width=(0, test_length - max_offset), mode="constant", constant_values=0),
            weights=weights,
        )
    else:
        return np.average(cosine_sim, weights=weights)


def _weights(length: int, start: int = 100, stop: int = 1):
    return np.geomspace(start, stop, num=length)


def _evaluate_structure_similarity(
    loop_start: int,
    loop_end: int,
    segments: np.ndarray,
    threshold: int = 1000
) -> float:
    """評估迴圈點在音樂結構上的相似度

    Args:
        loop_start (int): 迴圈開始點
        loop_end (int): 迴圈結束點
        segments (np.ndarray): 段落邊界點陣列
        threshold (int, optional): 判定接近段落邊界的閾值. Defaults to 1000.

    Returns:
        float: 結構相似度分數 (0.0 到 1.0)
    """
    similarity_score = 0.0
    
    # 檢查迴圈點是否在合適的段落邊界
    for segment in segments:
        if abs(loop_start - segment) < threshold:
            similarity_score += 0.5
        if abs(loop_end - segment) < threshold:
            similarity_score += 0.5
            
    # 標準化分數到 0-1 範圍
    return min(1.0, similarity_score)


def _evaluate_chord_progression(
    loop_start: int,
    loop_end: int,
    chord_labels: list,
    window_size: int = 2
) -> float:
    """更強的和弦進行相似度：比較 loop_start/loop_end 前後的和弦標籤是否一致"""
    start_chord = chord_labels[max(0, loop_start - window_size):loop_start + window_size]
    end_chord = chord_labels[max(0, loop_end - window_size):loop_end + window_size]
    # 只要有重疊的和弦標籤就給高分
    if set(start_chord) & set(end_chord):
        return 1.0
    return 0.0


def _evaluate_mfcc_similarity(
    loop_start: int,
    loop_end: int,
    mfcc: np.ndarray,
    window_size: int = 4
) -> float:
    """評估迴圈點的 MFCC 音色相似度"""
    start_window = mfcc[:, max(0, loop_start - window_size):loop_start]
    end_window = mfcc[:, loop_end:min(mfcc.shape[1], loop_end + window_size)]
    if start_window.shape[1] == 0 or end_window.shape[1] == 0:
        return 0.0
    start_vec = np.mean(start_window, axis=1)
    end_vec = np.mean(end_window, axis=1)
    sim = np.dot(start_vec, end_vec) / (np.linalg.norm(start_vec) * np.linalg.norm(end_vec) + 1e-8)
    return max(0.0, sim)
