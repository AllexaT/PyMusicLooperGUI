from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class ExportWidget(QGroupBox):
    exportRequested = pyqtSignal()

    def __init__(self, translations):
        super().__init__(translations.get("export_group", "Export"))
        self.tr_lang = translations
        self.init_ui()

    def init_ui(self):
        export_layout = QHBoxLayout()
        export_btn = QPushButton(self.tr_lang.get("export_btn", "Export"))
        export_btn.clicked.connect(self.exportRequested.emit)
        export_layout.addWidget(export_btn)
        self.setLayout(export_layout)
