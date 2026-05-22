from typing import List, Dict
import numpy as np

from models.audio import MLAudio
from models.loop_pair import LoopPair

from .scoring import (
    _calculate_loop_score,
    _evaluate_structure_similarity,
    _evaluate_chord_progression,
    _evaluate_mfcc_similarity,
    _weights
)

def _assess_and_filter_loop_pairs(
    mlaudio: MLAudio,
    chroma: np.ndarray,
    bpm: float,
    candidate_pairs: List[LoopPair],
    structure_info: Dict,
    disable_pruning: bool = False,
    score_weights: dict = None,
) -> List[LoopPair]:
    """Assigns the scores to each loop pair and prunes the list of candidate loop pairs

    Args:
        mlaudio (MLAudio): MLAudio object of the track being analyzed
        chroma (np.ndarray): The chroma spectrogram
        bpm (float): The estimated bpm/tempo of the track
        candidate_pairs (List[LoopPair]): The list of candidate loop pairs found
        structure_info (Dict): The music structure analysis information
        disable_pruning (bool, optional): Returns all the candidate loop points without filtering. Defaults to False.
        score_weights (dict, optional): The weights for the advanced scoring. Defaults to None.

    Returns:
        List[LoopPair]: A scored and filtered list of valid loop candidate pairs
    """
    beats_per_second = bpm / 60
    num_test_beats = 12
    seconds_to_test = num_test_beats / beats_per_second
    test_offset = mlaudio.samples_to_frames(int(seconds_to_test * mlaudio.rate))

    if test_offset > chroma.shape[-1]:
        test_offset = chroma.shape[-1] // 4

    if len(candidate_pairs) >= 100 and not disable_pruning:
        pruned_candidate_pairs = _prune_candidates(candidate_pairs)
    else:
        pruned_candidate_pairs = candidate_pairs

    weights = _weights(test_offset, start=max(2, test_offset // num_test_beats), stop=1)

    # 預先計算所有分數
    for pair in pruned_candidate_pairs:
        # 原始分數
        original_score = _calculate_loop_score(
            int(pair._loop_start_frame_idx),
            int(pair._loop_end_frame_idx),
            chroma,
            test_duration=test_offset,
            weights=weights,
        )
        pair.original_score = original_score
        # 結構分數
        structure_score = _evaluate_structure_similarity(
            int(pair._loop_start_frame_idx),
            int(pair._loop_end_frame_idx),
            structure_info['segments']
        )
        pair.structure_score = structure_score
        # 和弦分數
        chord_score = _evaluate_chord_progression(
            int(pair._loop_start_frame_idx),
            int(pair._loop_end_frame_idx),
            structure_info['chord_labels'],
        )
        pair.chord_score = chord_score
        # MFCC分數
        mfcc_score = _evaluate_mfcc_similarity(
            int(pair._loop_start_frame_idx),
            int(pair._loop_end_frame_idx),
            structure_info['mfcc']
        )
        pair.mfcc_score = mfcc_score
        # 預設分數為原始分數
        pair.score = original_score
    # 預設排序為原始分數
    pruned_candidate_pairs = sorted(
        pruned_candidate_pairs, reverse=True, key=lambda x: x.score
    )
    return pruned_candidate_pairs


def _prune_candidates(
    candidate_pairs: List[LoopPair],
    keep_top_notes: float = 75,
    keep_top_loudness: float = 50,
    acceptable_loudness=0.25,
) -> List[LoopPair]:
    db_diff_array = np.array([pair.loudness_difference for pair in candidate_pairs])
    note_dist_array = np.array([pair.note_distance for pair in candidate_pairs])

    # Minimum value used to avoid issues with tracks with lots of silence
    epsilon = 1e-3
    min_adjusted_db_diff_array = db_diff_array[db_diff_array > epsilon]
    min_adjusted_note_dist_array = note_dist_array[note_dist_array > epsilon]

    # Avoid index errors by having at least 3 elements when performing percentile-based pruning
    # Otherwise, skip by setting the value to the highest available
    if min_adjusted_db_diff_array.size > 3:
        db_threshold = np.percentile(
            min_adjusted_db_diff_array, keep_top_loudness
        )
    else:
        db_threshold = np.max(db_diff_array)

    if min_adjusted_note_dist_array.size > 3:
        note_dist_threshold = np.percentile(
            min_adjusted_note_dist_array, keep_top_notes
        )
    else:
        note_dist_threshold = np.max(note_dist_array)

    # Lower values are better
    indices_that_meet_cond = np.flatnonzero(
        (db_diff_array <= max(acceptable_loudness, db_threshold)) & (note_dist_array <= note_dist_threshold)
    )
    return [candidate_pairs[idx] for idx in indices_that_meet_cond]


def _prioritize_duration(pair_list: List[LoopPair]) -> List[LoopPair]:
    db_diff_array = np.array([pair.loudness_difference for pair in pair_list])
    db_threshold = np.median(db_diff_array)

    duration_argmax = 0
    duration_max = 0

    score_array = np.array([pair.score for pair in pair_list])
    score_threshold = np.percentile(score_array, 90)

    # Must be a negligible difference from the top score
    score_threshold = max(score_threshold, pair_list[0].score - 1e-4)

    # Since pair_list is already sorted
    # Break the loop if the condition is not met
    for idx, pair in enumerate(pair_list):
        if pair.score < score_threshold:
            break
        duration = pair.loop_end - pair.loop_start
        if duration > duration_max and pair.loudness_difference <= db_threshold:
            duration_max, duration_argmax = duration, idx

    if duration_argmax:
        pair_list.insert(0, pair_list.pop(duration_argmax))
