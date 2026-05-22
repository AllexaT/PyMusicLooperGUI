"""Contains the core MusicLooper class that can be
used for programmatic access to the CLI's main features."""

from typing import List, Optional

import numpy as np

from models.analyzer import find_best_loop_points
from models.loop_pair import LoopPair
from models.audio import MLAudio
from services.playback import PlaybackHandler
from infrastructure.memory_utils import MemoryAnalyzer


class MusicLooper:
    """High-level API access to PyMusicLooper's main functions."""
    def __init__(self, filepath: str):
        """Initializes the MusicLooper object with the provided audio track.

        Args:
            filepath (str): path to the audio track to use.
        """
        self.mlaudio = MLAudio(filepath=filepath)

    def find_loop_pairs(
        self,
        min_duration_multiplier: float = 0.35,
        min_loop_duration: Optional[float] = None,
        max_loop_duration: Optional[float] = None,
        approx_loop_start: Optional[float] = None,
        approx_loop_end: Optional[float] = None,
        brute_force: bool = False,
        disable_pruning: bool = False,
        score_weights: dict = None,
        memory_decision_callback=None,
        lang='zh_TW',
    ) -> List[LoopPair]:
        """Finds the best loop points for the track, according to the parameters specified.

        Args:
            min_duration_multiplier (float, optional): The minimum duration of a loop as a multiplier of track duration. Defaults to 0.35.
            min_loop_duration (float, optional): The minimum duration of a loop (in seconds). Defaults to None.
            max_loop_duration (float, optional): The maximum duration of a loop (in seconds). Defaults to None.
            approx_loop_start (float, optional): The approximate location of the desired loop start (in seconds). If specified, must specify approx_loop_end as well. Defaults to None.
            approx_loop_end (float, optional): The approximate location of the desired loop end (in seconds). If specified, must specify approx_loop_start as well. Defaults to None.
            brute_force (bool, optional): Checks the entire track instead of the detected beats (disclaimer: runtime may be significantly longer). Defaults to False.
            disable_pruning (bool, optional): Returns all the candidate loop points without filtering. Defaults to False.
            score_weights (dict, optional): Custom score weights for each score type.
        
        Raises:
            LoopNotFoundError: raised in case no loops were found

        Returns:
            List[LoopPair]: A list of `LoopPair` objects containing the loop points related data. See the `LoopPair` class for more info.
        """
        # === 新增：記憶體預估與決策 ===
        analyzer = MemoryAnalyzer(silent=True, lang=lang)
        audio_length_sec = self.mlaudio.total_duration
        sample_rate = self.mlaudio.rate
        n_channels = self.mlaudio.n_channels
        mem_info = analyzer.estimate_memory_requirement(audio_length_sec, sample_rate, n_channels)
        strategy = analyzer.recommend_strategy(mem_info)
        
        if strategy['risk_level'] in ["高", "中"]:
            if memory_decision_callback:
                user_choice = memory_decision_callback(mem_info, strategy)
                if user_choice == "1":
                    return ["ORIGINAL_SCORE_ONLY"]
                elif user_choice == "2":
                    return ["SMART_BATCH_ANALYSIS"]
                else:
                    return ["CANCEL"]
            else:
                # 如果沒有回調函數，預設使用智能分批分析
                return ["SMART_BATCH_ANALYSIS"]
        
        # === 原本的完整分析 ===
        return find_best_loop_points(
            mlaudio=self.mlaudio,
            min_duration_multiplier=min_duration_multiplier,
            min_loop_duration=min_loop_duration,
            max_loop_duration=max_loop_duration,
            approx_loop_start=approx_loop_start,
            approx_loop_end=approx_loop_end,
            brute_force=brute_force,
            disable_pruning=disable_pruning,
            score_weights=score_weights
        )

    @property
    def filename(self) -> str:
        return self.mlaudio.filename

    @property
    def filepath(self) -> str:
        return self.mlaudio.filepath

    def samples_to_frames(self, samples: int) -> int:
        return self.mlaudio.samples_to_frames(samples)
    
    def samples_to_seconds(self, samples: int) -> float:
        return self.mlaudio.samples_to_seconds(samples)

    def frames_to_samples(self, frame: int) -> int:
        return self.mlaudio.frames_to_samples(frame)

    def seconds_to_frames(self, seconds: float) -> int:
        return self.mlaudio.seconds_to_frames(seconds)

    def seconds_to_samples(self, seconds: float) -> int:
        return self.mlaudio.seconds_to_samples(seconds)

    def frames_to_ftime(self, frame: int) -> str:
        return self.mlaudio.frames_to_ftime(frame)
    
    def samples_to_ftime(self, samples: int) -> str:
        return self.mlaudio.samples_to_ftime(samples)

    def play_looping(self, loop_start: int, loop_end: int, start_from: int = 0):
        """Plays an audio file with a loop active at the points specified

        Args:
            loop_start (int): Index of the loop start (in samples)
            loop_end (int): Index of the loop end (in samples)
            start_from (int, optional): Index of the sample point to start from. Defaults to 0.
        """
        playback_handler = PlaybackHandler()
        playback_handler.play_looping(
            self.mlaudio.playback_audio,
            self.mlaudio.rate,
            self.mlaudio.n_channels,
            loop_start,
            loop_end,
            start_from,
        )

