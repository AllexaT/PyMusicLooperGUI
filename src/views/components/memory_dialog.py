from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

class MemoryDecisionDialog(QDialog):
    def __init__(self, parent, mem_info: dict, strategy: dict, tr_lang: dict):
        super().__init__(parent)
        self.tr_lang = tr_lang
        self.mem_info = mem_info
        self.strategy = strategy
        self.choice = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.tr_lang.get("memory_log_title", "記憶體使用情況警告"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 標題區
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxWarning)
        icon_label.setPixmap(icon.pixmap(32, 32))
        
        title_label = QLabel(self.tr_lang.get("memory_log_title", "記憶體使用情況"))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 分隔線
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line1)

        # 記憶體數據區
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        def add_info_row(label_text, value_text, is_warning=False):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            val = QLabel(value_text)
            if is_warning:
                val.setStyleSheet("color: #ff5555; font-weight: bold;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            info_layout.addLayout(row)

        estimated_mb = f"{self.mem_info['estimated_memory']:.2f} MB"
        available_mb = f"{self.mem_info['available_memory']:.2f} MB"
        total_mb = f"{self.mem_info['total_memory']:.2f} MB"
        current_pct = f"{self.mem_info['current_usage']:.1f}%"
        predicted_pct = f"{self.mem_info['usage_percentage']:.1f}%"
        
        will_exceed = self.mem_info['will_exceed']

        add_info_row(self.tr_lang.get("memory_lbl_estimated", "預計需要的記憶體:"), estimated_mb, will_exceed)
        add_info_row(self.tr_lang.get("memory_lbl_available", "目前可用記憶體:"), available_mb)
        add_info_row(self.tr_lang.get("memory_lbl_total", "系統總記憶體:"), total_mb)
        add_info_row(self.tr_lang.get("memory_lbl_current_usage", "目前記憶體使用率:"), current_pct)
        add_info_row(self.tr_lang.get("memory_lbl_predicted_usage", "分析後預計使用率:"), predicted_pct, will_exceed)
        
        layout.addLayout(info_layout)

        # 分隔線
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line2)

        # 策略建議區
        strategy_layout = QVBoxLayout()
        strategy_title = QLabel(self.tr_lang.get("strategy_suggestion_title", "分析策略建議"))
        strategy_title.setFont(title_font)
        strategy_layout.addWidget(strategy_title)

        is_high_risk = self.mem_info['will_exceed']
        is_medium_risk = not is_high_risk and self.mem_info['usage_percentage'] > 70
        is_batch_recommended = is_high_risk or is_medium_risk

        risk_row = QHBoxLayout()
        risk_lbl = QLabel(self.tr_lang.get("memory_lbl_risk", "風險等級:"))
        risk_val = QLabel(self.strategy['risk_level'])
        if is_high_risk:
            risk_val.setStyleSheet("color: #ff5555; font-weight: bold;")
        elif is_medium_risk:
            risk_val.setStyleSheet("color: #ffaa00; font-weight: bold;")
        risk_row.addWidget(risk_lbl)
        risk_row.addStretch()
        risk_row.addWidget(risk_val)
        strategy_layout.addLayout(risk_row)

        rec_row = QHBoxLayout()
        rec_lbl = QLabel(self.tr_lang.get("memory_lbl_recommendation", "建議:"))
        rec_val = QLabel(self.strategy['recommendation'])
        rec_row.addWidget(rec_lbl)
        rec_row.addStretch()
        rec_row.addWidget(rec_val)
        strategy_layout.addLayout(rec_row)

        layout.addLayout(strategy_layout)

        # 按鈕區
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_original = QPushButton(self.tr_lang.get("btn_original_score", "只使用 Original Score 分析"))
        btn_batch = QPushButton(self.tr_lang.get("btn_smart_batch", "使用智能分批分析"))
        btn_cancel = QPushButton(self.tr_lang.get("cancel", "取消"))
        
        # 凸顯建議的選項
        if is_batch_recommended:
            btn_batch.setStyleSheet("background-color: #2b5b84; color: white; font-weight: bold; padding: 5px;")
            btn_batch.setDefault(True)
        else:
            btn_original.setStyleSheet("background-color: #2b5b84; color: white; font-weight: bold; padding: 5px;")
            btn_original.setDefault(True)

        btn_original.clicked.connect(lambda: self.make_choice("1"))
        btn_batch.clicked.connect(lambda: self.make_choice("2"))
        btn_cancel.clicked.connect(lambda: self.make_choice(""))

        btn_layout.addWidget(btn_original)
        btn_layout.addWidget(btn_batch)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)

    def make_choice(self, choice):
        self.choice = choice
        self.accept()

    def get_choice(self):
        return self.choice
