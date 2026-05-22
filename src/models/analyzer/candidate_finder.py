from typing import List, Tuple
import numpy as np
from numba import njit
from .utils import _db_diff, _norm


@njit(cache=True)
def _find_candidate_pairs(
    chroma: np.ndarray,
    power_db: np.ndarray,
    beats: np.ndarray,
    min_loop_duration: int,
    max_loop_duration: int,
) -> List[Tuple[int, int, float, float]]:
    """Generates a list of all valid candidate loop pairs using combinations of beat indices,
    by comparing the notes using the chroma spectrogram and their loudness difference

    Args:
        chroma (np.ndarray): The chroma spectrogram
        power_db (np.ndarray): The power spectrogram in dB
        beats (np.ndarray): The frame indices of detected beats
        min_loop_duration (int): Minimum loop duration (in frames)
        max_loop_duration (int): Maximum loop duration (in frames)

    Returns:
        List[Tuple[int, int, float, float]]: A list of tuples containing each candidate loop pair data in the following format (loop_start, loop_end, note_distance, loudness_difference)
    """
    candidate_pairs = []

    # Magic constants
    ## Mainly found through trial and error,
    ## higher values typically result in the inclusion of musically unrelated beats/notes
    ACCEPTABLE_NOTE_DEVIATION = 0.0875
    ## Since the _db_diff comparison is takes a perceptually weighted power_db frame,
    ## the difference should be imperceptible (ideally, close to 0)
    ## Based on trial and error, values higher than ~0.5 have a perceptible
    ## difference in loudness
    ACCEPTABLE_LOUDNESS_DIFFERENCE = 0.5

    deviation = _norm(chroma[..., beats] * ACCEPTABLE_NOTE_DEVIATION)

    for idx, loop_end in enumerate(beats):
        for loop_start in beats:
            loop_length = loop_end - loop_start
            if loop_length < min_loop_duration:
                break
            if loop_length > max_loop_duration:
                continue
            note_distance = _norm(chroma[..., loop_end] - chroma[..., loop_start])

            if note_distance <= deviation[idx]:
                loudness_difference = _db_diff(
                    power_db[..., loop_end], power_db[..., loop_start]
                )
                loop_pair = (
                    int(loop_start),
                    int(loop_end),
                    note_distance,
                    loudness_difference,
                )
                if loudness_difference <= ACCEPTABLE_LOUDNESS_DIFFERENCE:
                    candidate_pairs.append(loop_pair)

    return candidate_pairs
