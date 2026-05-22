from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from services.playback import PlaybackHandler

class PlayerViewModel(QObject):
    playbackStateChanged = pyqtSignal(bool) # is_playing
    playbackProgress = pyqtSignal(int, int) # current_frame, loop_counter

    def __init__(self):
        super().__init__()
        self.playback_service = PlaybackHandler()
        self.looper = None
        self.current_loop_start = 0
        self.current_loop_end = 0

    def load_looper(self, looper):
        self.looper = looper

    @pyqtSlot(float)
    def set_volume(self, volume: float):
        self.playback_service.set_volume(volume)

    @pyqtSlot(int, int)
    def play_loop(self, loop_start: int, loop_end: int):
        """Start playing the specific loop points."""
        if not self.looper:
            return

        self.current_loop_start = loop_start
        self.current_loop_end = loop_end
        
        def progress_cb(current_frame, loop_counter):
            self.playbackProgress.emit(current_frame, loop_counter)

        if self.playback_service.stream and self.playback_service.is_playing:
            self.playback_service.stop()

        self.playback_service.play_looping(
            self.looper.mlaudio.playback_audio,
            self.looper.mlaudio.rate,
            self.looper.mlaudio.n_channels,
            loop_start,
            loop_end,
            start_from=loop_start,
            progress_callback=progress_cb
        )
        self.playbackStateChanged.emit(True)

    @pyqtSlot()
    def pause(self):
        """Pause playback."""
        self.playback_service.pause()
        self.playbackStateChanged.emit(False)

    @pyqtSlot()
    def resume(self):
        """Resume playback."""
        self.playback_service.resume()
        self.playbackStateChanged.emit(True)

    @pyqtSlot()
    def stop(self):
        """Stop playback."""
        self.playback_service.stop()
        self.playbackStateChanged.emit(False)

    @pyqtSlot(int)
    def seek(self, frame: int):
        """Seek to a specific frame inside the playback."""
        if self.looper and self.playback_service.is_playing:
            was_paused = self.playback_service.is_paused
            self.playback_service.stop()
            self.playback_service.play_looping(
                self.looper.mlaudio.playback_audio,
                self.looper.mlaudio.rate,
                self.looper.mlaudio.n_channels,
                self.current_loop_start,
                self.current_loop_end,
                start_from=frame,
                progress_callback=lambda c, l: self.playbackProgress.emit(c, l)
            )
            if was_paused:
                self.playback_service.pause()
                self.playbackProgress.emit(frame, self.playback_service.loop_counter)
                self.playbackStateChanged.emit(False)
            else:
                self.playbackStateChanged.emit(True)
