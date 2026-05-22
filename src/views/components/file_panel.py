from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal

class FileSelectionWidget(QGroupBox):
    fileSelected = pyqtSignal(str) # Emitted when a file is chosen
    youtubeDownloadRequested = pyqtSignal(str) # Emitted when download clicked

    def __init__(self, translations):
        super().__init__(translations.get("file_group", "File Input"))
        self.tr_lang = translations
        self.init_ui()

    def init_ui(self):
        file_layout = QVBoxLayout()
        
        # Local File Input
        local_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(self.tr_lang.get("audio_path", "Audio Path"))
        browse_btn = QPushButton(self.tr_lang.get("browse_btn", "Browse"))
        browse_btn.clicked.connect(self.browse_file)
        local_layout.addWidget(self.path_edit)
        local_layout.addWidget(browse_btn)

        # YouTube Input
        youtube_layout = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(self.tr_lang.get("youtube_url", "YouTube URL"))
        download_btn = QPushButton(self.tr_lang.get("download_btn", "Download"))
        download_btn.clicked.connect(self.request_download)
        youtube_layout.addWidget(self.url_edit)
        youtube_layout.addWidget(download_btn)

        file_layout.addLayout(local_layout)
        file_layout.addLayout(youtube_layout)
        self.setLayout(file_layout)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            self.tr_lang.get("select_file", "Select File"), 
            "", 
            self.tr_lang.get("audio_files_filter", "Audio Files (*.mp3 *.wav *.ogg *.flac *.opus)")
        )
        if path:
            self.path_edit.setText(path)
            self.fileSelected.emit(path)

    def set_file_path(self, path: str):
        self.path_edit.setText(path)

    def get_file_path(self) -> str:
        return self.path_edit.text()

    def request_download(self):
        url = self.url_edit.text()
        if url:
            self.youtubeDownloadRequested.emit(url)
