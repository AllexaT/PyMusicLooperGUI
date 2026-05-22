import os
from math import ceil
from typing import Optional, Union

import lazy_loader as lazy
import numpy as np

soundfile = lazy.load("soundfile")

class LoopExporter:
    """Handles audio file exporting and track extending functionalities."""
    
    def __init__(self, mlaudio):
        """Initializes the LoopExporter with an MLAudio object.
        
        Args:
            mlaudio: The MLAudio object containing the track data.
        """
        self.mlaudio = mlaudio

    def export(
        self,
        loop_start: int,
        loop_end: int,
        format: str = "WAV",
        output_dir: Optional[str] = None
    ):
        """Exports the audio into three files: intro, loop and outro."""
        if output_dir is not None:
            out_path = os.path.join(output_dir, self.mlaudio.filename)
        else:
            out_path = os.path.abspath(self.mlaudio.filepath)

        soundfile.write(
            f"{out_path}-intro.{format.lower()}",
            self.mlaudio.playback_audio[:loop_start],
            self.mlaudio.rate,
            format=format,
        )
        soundfile.write(
            f"{out_path}-loop.{format.lower()}",
            self.mlaudio.playback_audio[loop_start:loop_end],
            self.mlaudio.rate,
            format=format,
        )
        soundfile.write(
            f"{out_path}-outro.{format.lower()}",
            self.mlaudio.playback_audio[loop_end:],
            self.mlaudio.rate,
            format=format,
        )

    def extend(
        self,
        loop_start: int,
        loop_end: int,
        extended_length: float,
        fade_length: float = 5,
        disable_fade_out: bool = False,
        format: str = "WAV",
        output_dir: Optional[str] = None,
    ) -> str:
        """Extends the audio by looping to at least the specified length."""
        if output_dir is not None:
            out_path = os.path.join(output_dir, self.mlaudio.filename)
        else:
            out_path = os.path.abspath(self.mlaudio.filepath)

        if extended_length < self.mlaudio.total_duration:
            raise ValueError(
                "Extended length must be greater than the audio's original length."
            )

        intro = self.mlaudio.playback_audio[:loop_start]
        loop = self.mlaudio.playback_audio[loop_start:loop_end]
        outro = self.mlaudio.playback_audio[loop_end:]

        loop_extended_length = self.mlaudio.seconds_to_samples(extended_length) - intro.shape[0]

        if disable_fade_out:
            loop_extended_length -= outro.shape[0]

        loop_factor = loop_extended_length / loop.shape[0]
        left_over_multiplier = loop_factor - int(loop_factor)
        extend_end_idx = loop_start + int(
            (loop_end - loop_start) * left_over_multiplier
        )

        final_loop = self.mlaudio.playback_audio[loop_start:extend_end_idx].copy()
        if disable_fade_out:
            final_loop = loop
        else:
            samples_to_fade = min(
                self.mlaudio.seconds_to_samples(fade_length), final_loop.shape[0]
            )
            final_loop[-samples_to_fade:] = (
                final_loop[-samples_to_fade:]
                * np.linspace(1, 0, samples_to_fade)[:, np.newaxis]
            )

        extended_loop_length = final_loop.shape[0] + (
            loop.shape[0] * (int(loop_factor))
        )
        extended_audio_length = (
            intro.shape[0]
            + extended_loop_length
            + (outro.shape[0] if disable_fade_out else 0)
        )
        total_length_seconds = self.mlaudio.samples_to_seconds(extended_audio_length)
        duration_sec = ceil(total_length_seconds%60)
        duration_mins = int(total_length_seconds//60)
        if duration_sec == 60:
            duration_sec = 0
            duration_mins += 1
        extended_audio_length_fmt = (
            f"{duration_mins:d}m{duration_sec:02d}s"
        )
        output_file_path = (
            f"{out_path}-extended-{extended_audio_length_fmt}.{format.lower()}"
        )

        with soundfile.SoundFile(
            output_file_path,
            mode="w",
            samplerate=self.mlaudio.rate,
            channels=self.mlaudio.n_channels,
            format=format,
        ) as sf:
            dtype = str(self.mlaudio.playback_audio.dtype)
            sf.buffer_write(intro.tobytes(order="C"), dtype)
            for _ in range(int(loop_factor)):
                sf.buffer_write(loop.tobytes(order="C"), dtype)
            sf.buffer_write(final_loop.tobytes(order="C"), dtype)
            if disable_fade_out:
                sf.buffer_write(outro.tobytes(order="C"), dtype)
        return output_file_path

    def export_txt(
        self,
        loop_start: Union[int, float, str],
        loop_end: Union[str, int, float, str],
        txt_name: str = "loops",
        output_dir: Optional[str] = None
    ):
        """Exports the given loop points to a text file named `loop.txt`."""
        if output_dir is not None:
            out_path = os.path.join(output_dir, f"{txt_name}.txt")
        else:
            out_path = os.path.join(os.path.dirname(self.mlaudio.filepath), f"{txt_name}.txt")

        with open(out_path, "a") as file:
            file.write(f"{loop_start} {loop_end} {self.mlaudio.filename}\n")
