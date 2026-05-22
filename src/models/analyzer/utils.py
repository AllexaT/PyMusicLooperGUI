import numpy as np
from numba import njit


@njit
def _db_diff(power_db_f1: np.ndarray, power_db_f2: np.ndarray) -> float:
    return np.abs(np.max(power_db_f1) - np.max(power_db_f2))


@njit
def _norm(a: np.ndarray) -> float:
    return np.sqrt(np.sum(np.abs(a) ** 2, axis=0))


def _softmax(x, axis=0):
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / np.sum(e_x, axis=axis, keepdims=True)


@njit(cache=True)
def nearest_zero_crossing(audio: np.ndarray, rate: int, sample_idx: int) -> int:
    """Implementation of Audacity's `At Zero Crossings` feature. https://manual.audacityteam.org/man/select_menu_at_zero_crossings.html
    Description is based on the relevant Audacity manual page, due to identical behaviour.

    Returns the best closest sample point that is at a rising zero crossing point.
    This is a point where a line joining the audio samples rises from left to right and crosses the zero horizontal line that represents silence.
    The shift in audio position is not itself detectable to the ear, but the fact that the joins in the waveform are now of matching height helps avoid clicks in audio.

    This feature does not necessarily find the nearest zero crossing to the current position. It aims to find the crossing where the average amplitude of samples in the vicinity is lowest.

    Args:
        audio (np.ndarray): Numpy array containing the playback audio; must be in the shape `(samples, n_channels)`
        rate (int): Sample rate of the provided audio
        sample_idx (int): The index of the sample point to return the nearest zero crossing of

    Returns:
        int: the index of the best sample point that is at a rising zero crossing point closest to the `sample_idx` provided, returns `sample_idx` if none where found
    """
    # Re-implementation of Audacity's NearestZeroCrossing function in Python
    # https://github.com/audacity/audacity/blob/057bf4ee6f71962cd8ecc6dbccf0852695340758/src/menus/SelectMenus.cpp#L30
    # Original credit goes to the Audacity team and contributors
    n_channels = audio.shape[1]

    # Window is 1/100th of a second
    window_size = int(max(1, rate / 100))

    # Create sample window centered around sample_idx
    offset = window_size // 2
    neg_offset = max(0, sample_idx - offset)
    pos_offset = min(audio.shape[0], sample_idx + offset)
    sample_window = audio[neg_offset:pos_offset]

    # Adjusts the indexing offset in case the left side of sample_idx was clipped
    offset_correction = abs(sample_idx - offset) if sample_idx - offset < 0 else 0

    sample_window_length = sample_window.shape[0]
    dist = np.zeros(sample_window_length)

    for channel in range(n_channels):
        prev = 2.0
        one_dist = sample_window[..., channel].copy()
        for i in range(sample_window_length):
            fdist = np.abs(one_dist[i])
            if prev * one_dist[i] > 0:  # both same sign? No good.
                fdist += 0.4  # No good if same sign.
            elif prev > 0.0:
                fdist += 0.1  # medium penalty for downward crossing.
            prev = one_dist[i]
            one_dist[i] = fdist

        for i in range(sample_window_length):
            dist[i] += one_dist[i]
            dist[i] += 0.1 * abs(i - offset + offset_correction) / (window_size / 2)

    argmin = np.argmin(dist)
    minimum_dist = dist[argmin]

    # If we're worse than 0.2 on average, on one track, then no good.
    if (n_channels == 1) and (minimum_dist > (0.2 * n_channels)):
        return sample_idx
    # If we're worse than 0.6 on average, on multi-track, then no good.
    if (n_channels > 1) and (minimum_dist > (0.6 * n_channels)):
        return sample_idx

    return int(sample_idx + argmin - offset + offset_correction)
