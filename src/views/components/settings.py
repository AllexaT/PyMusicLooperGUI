from PyQt6.QtWidgets import QGroupBox, QFormLayout, QHBoxLayout, QDoubleSpinBox, QCheckBox
from PyQt6.QtCore import pyqtSignal

class LoopSettingsWidget(QGroupBox):
    settingsChanged = pyqtSignal() # Emitted when any setting is modified

    def __init__(self, translations):
        super().__init__(translations.get("settings_group", "Settings"))
        self.tr_lang = translations
        self.score_checkboxes = {}
        self.init_ui()

    def init_ui(self):
        settings_layout = QFormLayout()
        
        # Minimum Duration
        self.min_duration = QDoubleSpinBox()
        self.min_duration.setValue(0.35)
        self.min_duration.valueChanged.connect(self.on_settings_changed)
        settings_layout.addRow(self.tr_lang.get("min_duration", "Min Duration"), self.min_duration)
        
        # Scoring Options
        score_hbox = QHBoxLayout()
        for key, label_key in [
            ('structure', "structure"),
            ('chord', "chord"),
            ('mfcc', "mfcc")
        ]:
            cb = QCheckBox(self.tr_lang.get(label_key, label_key.title()))
            cb.setChecked(False)
            cb.setMinimumWidth(65)
            cb.stateChanged.connect(self.on_settings_changed)
            self.score_checkboxes[key] = cb
            score_hbox.addWidget(cb)
            if label_key != "mfcc":
                score_hbox.addSpacing(0)
                
        score_hbox.addStretch(1)
        settings_layout.addRow(self.tr_lang.get("enhancement_options", "Options"), score_hbox)
        self.setLayout(settings_layout)

    def on_settings_changed(self):
        self.settingsChanged.emit()

    def get_min_duration(self) -> float:
        return self.min_duration.value()

    def get_score_weights(self) -> dict:
        score_items = ['structure', 'chord', 'mfcc']
        checked = ['original'] + [k for k in score_items if self.score_checkboxes[k].isChecked()]
        weight = 1.0 / len(checked)
        return {k: (weight if k in checked else 0.0) for k in ['original'] + score_items}
