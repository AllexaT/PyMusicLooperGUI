from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, Qt
import threading
from models.looper_core import MusicLooper
from infrastructure.i18n import TRANSLATIONS

class AnalysisWorker(QThread):
    progress = pyqtSignal(int)
    statusUpdate = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    memoryDecisionRequested = pyqtSignal(dict, dict)

    def __init__(self, filepath, min_duration_multiplier, score_weights, locale):
        super().__init__()
        self.filepath = filepath
        self.min_duration_multiplier = min_duration_multiplier
        self.score_weights = score_weights
        self.locale = locale
        self.tr = TRANSLATIONS.get(locale, TRANSLATIONS['en'])
        self.looper = None
        self.user_choice = ""
        self.decision_event = threading.Event()

    def memory_callback(self, mem_info, strategy):
        self.user_choice = ""
        self.decision_event.clear()
        self.memoryDecisionRequested.emit(mem_info, strategy)
        self.decision_event.wait()
        return self.user_choice

    def run(self):
        try:
            self.statusUpdate.emit(self.tr.get("loading_audio", "Loading audio..."))
            self.progress.emit(10)
            
            self.looper = MusicLooper(self.filepath)
            
            self.statusUpdate.emit(self.tr.get("analyzing_loops", "Analyzing loops..."))
            self.progress.emit(50)
            
            loops = self.looper.find_loop_pairs(
                min_duration_multiplier=self.min_duration_multiplier,
                score_weights=self.score_weights,
                memory_decision_callback=self.memory_callback,
                lang=self.locale
            )
            
            # Map SMART_BATCH_ANALYSIS / ORIGINAL_SCORE_ONLY to handler.
            if isinstance(loops, list) and len(loops) == 1 and isinstance(loops[0], str):
                from handler import LoopHandler
                handler = LoopHandler(
                    path=self.filepath,
                    min_duration_multiplier=self.min_duration_multiplier
                )
                callbacks = {
                    'status_update': lambda _, s: self.statusUpdate.emit(s),
                    'progress_update': lambda p: self.progress.emit(int(50 + p * 0.5))
                }
                if loops[0] == "ORIGINAL_SCORE_ONLY":
                    self.statusUpdate.emit(self.tr.get("running_original_analysis", "Running original analysis..."))
                    loops = handler.original_score_only_analysis(
                        self.looper.mlaudio, 
                        app_callbacks=callbacks
                    )
                elif loops[0] == "SMART_BATCH_ANALYSIS":
                    loops = handler.smart_batch_analysis(
                        self.looper.mlaudio,
                        app_callbacks=callbacks
                    )
                elif loops[0] == "CANCEL":
                    self.statusUpdate.emit(self.tr.get("analysis_cancelled", "分析已取消"))
                    self.finished.emit([])
                    return
            
            self.progress.emit(100)
            self.statusUpdate.emit(self.tr.get("analysis_complete", "Analysis complete."))
            self.finished.emit(loops)
            
        except Exception as e:
            self.error.emit(str(e))

class MainViewModel(QObject):
    # Signals for View to bind
    analysisStarted = pyqtSignal()
    analysisProgress = pyqtSignal(int)
    analysisStatus = pyqtSignal(str)
    analysisFinished = pyqtSignal(list, object) # loops, looper instance
    analysisError = pyqtSignal(str)
    memoryDecisionRequested = pyqtSignal(dict, dict)

    def __init__(self):
        super().__init__()
        self.current_filepath = ""
        self.looper = None
        self.worker = None

    @pyqtSlot(str, float, dict, str)
    def start_analysis(self, filepath: str, min_duration: float, score_weights: dict, locale: str):
        if self.worker and self.worker.isRunning():
            return
            
        self.current_filepath = filepath
        self.worker = AnalysisWorker(filepath, min_duration, score_weights, locale)
        
        self.worker.progress.connect(self.analysisProgress.emit)
        self.worker.statusUpdate.connect(self.analysisStatus.emit)
        self.worker.memoryDecisionRequested.connect(self.on_worker_memory_decision)
        
        def on_finished(loops):
            self.looper = self.worker.looper
            self.analysisFinished.emit(loops, self.looper)
            
        self.worker.finished.connect(on_finished)
        self.worker.error.connect(self.analysisError.emit)
        self.worker.start()
        
        self.analysisStarted.emit()

    @pyqtSlot(dict, dict)
    def on_worker_memory_decision(self, mem_info, strategy):
        self.memoryDecisionRequested.emit(mem_info, strategy)
        
    def set_memory_decision(self, choice: str):
        if self.worker:
            self.worker.user_choice = choice
            self.worker.decision_event.set()
