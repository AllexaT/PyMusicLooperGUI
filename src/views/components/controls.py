from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QStyle
from PyQt6.QtCore import Qt, pyqtSignal

class PlayerControlWidget(QGroupBox):
    playRequested = pyqtSignal()
    pauseRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    seekRequested = pyqtSignal(int) # progress percentage 0-100
    volumeChanged = pyqtSignal(float) # volume 0.0-1.0

    def __init__(self, translations):
        super().__init__(translations.get("playback_group", "Playback"))
        self.tr_lang = translations
        self.is_playing = False
        self.slider_was_playing = False
        self.init_ui()

    def init_ui(self):
        playback_layout = QVBoxLayout()
        
        # Time controls
        time_layout = QHBoxLayout()
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(24, 24)
        self.play_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.pause_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self.play_btn.setIcon(self.play_icon)
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.current_time_label = QLabel("00:00")
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 100)
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        self.time_slider.sliderReleased.connect(self.on_slider_released)
        self.total_time_label = QLabel("00:00")
        
        time_layout.addWidget(self.play_btn)
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.time_slider)
        time_layout.addWidget(self.total_time_label)
        playback_layout.addLayout(time_layout)
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_label = QLabel(self.tr_lang.get("volume", "Volume"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(10)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.volume_value = QLabel("10%")
        
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value)
        playback_layout.addLayout(volume_layout)
        
        self.setLayout(playback_layout)

    def on_volume_changed(self, value):
        self.volume_value.setText(f"{value}%")
        self.volumeChanged.emit(value / 100.0)

    def toggle_playback(self):
        if self.is_playing:
            self.pauseRequested.emit()
        else:
            self.playRequested.emit()

    def update_state(self, playing: bool):
        self.is_playing = playing
        self.play_btn.setIcon(self.pause_icon if playing else self.play_icon)

    def update_progress(self, percent: int, current_str: str, total_str: str):
        if not self.time_slider.isSliderDown():
            self.time_slider.blockSignals(True)
            self.time_slider.setValue(percent)
            self.time_slider.blockSignals(False)
        self.current_time_label.setText(current_str)
        self.total_time_label.setText(total_str)

    def on_slider_pressed(self):
        self.slider_was_playing = self.is_playing
        if self.is_playing:
            self.pauseRequested.emit()

    def on_slider_released(self):
        self.seekRequested.emit(self.time_slider.value())
        if self.slider_was_playing:
            self.playRequested.emit()

    def reset(self):
        self.time_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.update_state(False)
