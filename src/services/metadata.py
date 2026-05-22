import os
import shutil
from typing import Optional, Tuple

class AudioTagger:
    """Handles reading and writing metadata tags for audio loop points."""
    
    def __init__(self, mlaudio):
        """Initializes the AudioTagger with an MLAudio object.
        
        Args:
            mlaudio: The MLAudio object containing the track data.
        """
        self.mlaudio = mlaudio

    def _end_tag_is_offset(
        self,
        loop_end_tag: str,
        is_offset: Optional[bool],
    ) -> bool:
        if is_offset is not None:
            return is_offset

        upper_loop_end_tag = loop_end_tag.upper()
        return "LEN" in upper_loop_end_tag or "OFFSET" in upper_loop_end_tag

    def export_tags(
        self,
        loop_start: int,
        loop_end: int,
        loop_start_tag: str,
        loop_end_tag: str,
        is_offset: Optional[bool] = None,
        output_dir: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """Adds metadata tags of loop points to a copy of the source audio file.

        Args:
            loop_start (int): Loop start in samples.
            loop_end (int): Loop end in samples.
            loop_start_tag (str): Name of the loop_start metadata tag.
            loop_end_tag (str): Name of the loop_end metadata tag.
            is_offset (bool, optional): Export second tag as relative length / absolute end. Defaults to auto-detecting based on tag name.
            output_dir (str, optional): Path to the output directory. Defaults to the same directory as the source audio file.
            
        Returns:
            Tuple[str, str, str]: A tuple containing (exported_file_path, loop_start_str, loop_end_str)
        """
        # Workaround for taglib import issues on Apple silicon devices
        # Import taglib only when needed to isolate ImportErrors
        import taglib
            
        if output_dir is None:
            output_dir = os.path.abspath(self.mlaudio.filepath)

        track_name, file_extension = os.path.splitext(self.mlaudio.filename)

        exported_file_path = os.path.join(
            output_dir, f"{track_name}-tagged{file_extension}"
        )
        shutil.copyfile(self.mlaudio.filepath, exported_file_path)

        # Handle LOOPLENGTH tag
        if self._end_tag_is_offset(loop_end_tag, is_offset):
            loop_end = loop_end - loop_start

        with taglib.File(exported_file_path, save_on_exit=True) as audio_file:
            audio_file.tags[loop_start_tag] = [str(loop_start)]
            audio_file.tags[loop_end_tag] = [str(loop_end)]

        return exported_file_path, str(loop_start), str(loop_end)

    def read_tags(
        self,
        loop_start_tag: str,
        loop_end_tag: str,
        is_offset: Optional[bool] = None
    ) -> Tuple[int, int]:
        """Reads the tags provided from the file and returns the read loop points.

        Args:
            loop_start_tag (str): The name of the metadata tag containing the loop_start value
            loop_end_tag (str): The name of the metadata tag containing the loop_end value
            is_offset (bool, optional): Parse second tag as relative length / absolute end. Defaults to auto-detecting based on tag name.

        Returns:
            Tuple[int, int]: A tuple containing (loop_start, loop_end)
        """
        # Workaround for taglib import issues on Apple silicon devices
        # Import taglib only when needed to isolate ImportErrors
        import taglib

        loop_start = None
        loop_end = None

        with taglib.File(self.mlaudio.filepath) as audio_file:
            if loop_start_tag not in audio_file.tags:
                raise ValueError(f"The tag \"{loop_start_tag}\" is not present in the metadata of \"{self.mlaudio.filename}\".")
            if loop_end_tag not in audio_file.tags:
                raise ValueError(f"The tag \"{loop_end_tag}\" is not present in the metadata of \"{self.mlaudio.filename}\".")
            try:
                loop_start = int(audio_file.tags[loop_start_tag][0])
                loop_end = int(audio_file.tags[loop_end_tag][0])
            except Exception as e:
                raise TypeError(
                    "One of the tags provided has invalid (non-integer or empty) values"
                ) from e

        # Re-order the loop points in case
        real_loop_start = min(loop_start, loop_end)
        real_loop_end = max(loop_start, loop_end)

        # Handle LOOPLENGTH tag
        if self._end_tag_is_offset(loop_end_tag, is_offset):
            real_loop_end = real_loop_start + real_loop_end

        return real_loop_start, real_loop_end
