from dataclasses import dataclass

@dataclass
class LoopPair:
    """A data class that encapsulates the loop point related data.
    Contains:
        loop_start: int (exact loop start position in samples)
        loop_end: int (exact loop end position in samples)
        note_distance: float
        loudness_difference: float
        structure_score: float
        chord_score: float
        mfcc_score: float
        score: float. Defaults to 0.
    """

    _loop_start_frame_idx: int
    _loop_end_frame_idx: int
    note_distance: float
    loudness_difference: float
    structure_score: float = 0
    chord_score: float = 0
    mfcc_score: float = 0
    score: float = 0
    loop_start: int = 0
    loop_end: int = 0
    original_score: float = 0
