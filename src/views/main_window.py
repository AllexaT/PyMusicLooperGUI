import os
import sys
import locale
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox, 
    QProgressDialog, QInputDialog, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QDesktopServices

from infrastructure.i18n import TRANSLATIONS
from services.ffmpeg import setup_ffmpeg, show_ffmpeg_error
from services.youtube import YoutubeDownloader

from viewmodels.main_viewmodel import MainViewModel
from viewmodels.player_viewmodel import PlayerViewModel

from views.components.file_panel import FileSelectionWidget
from views.components.settings import LoopSettingsWidget
from views.components.loop_table import LoopTableWidget
from views.components.controls import PlayerControlWidget
from views.components.export_panel import ExportWidget

class YoutubeDownloadThread(QThread):
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, translations):
        super().__init__()
        self.url = url
        self.tr = translations
        self.is_cancelled = False

    def run(self):
        try:
            downloader = YoutubeDownloader(
                self.url,
                output_path=None,
                progress_callback=self.on_progress,
                cancel_check=lambda: self.is_cancelled
            )
            if hasattr(downloader, 'filepath') and downloader.filepath:
                self.finished.emit(downloader.filepath)
            else:
                self.error.emit(self.tr.get("youtube_cancelled_or_failed", "Download cancelled or failed"))

        except Exception as e:
            self.error.emit(str(e))

    def on_progress(self, percent, status):
        self.progress.emit(percent, status)

    def cancel(self):
        self.is_cancelled = True

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        # 1. Load System Settings & Verify Setup
        try:
            current_locale = locale.getlocale()[0]
            is_chinese = current_locale and any(
                current_locale.lower().startswith(loc) 
                for loc in ['zh', 'zh_tw', 'zh_hk', 'zh_cn', 'zh_sg', 'zh_mo', 'chinese (traditional)_taiwan']
            )
        except:
            is_chinese = False

        self.locale_code = 'zh_TW' if is_chinese else 'en'
        self.tr_lang = TRANSLATIONS.get(self.locale_code, TRANSLATIONS['en'])

        if not setup_ffmpeg():
            show_ffmpeg_error()

        # 2. Init ViewModels
        self.main_vm = MainViewModel()
        self.player_vm = PlayerViewModel()
        self.download_thread = None

        self.init_ui()
        self.bind_viewmodels()

    def init_ui(self):
        self.setWindowTitle(self.tr_lang.get("window_title", "MusicLooper"))
        self.resize(327, 500)
        self.setMinimumWidth(327)
        self.setMaximumWidth(327)

        # Main Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Subcomponents
        self.file_panel = FileSelectionWidget(self.tr_lang)
        self.settings_panel = LoopSettingsWidget(self.tr_lang)
        self.loop_table = LoopTableWidget(self.tr_lang)
        self.controls_panel = PlayerControlWidget(self.tr_lang)
        self.export_panel = ExportWidget(self.tr_lang)

        layout.addWidget(self.file_panel)
        layout.addWidget(self.settings_panel)
        layout.addWidget(self.loop_table)
        layout.addWidget(self.controls_panel)
        layout.addWidget(self.export_panel)

        # Wire UI interactions to slots
        self.file_panel.fileSelected.connect(self.on_file_selected)
        self.file_panel.youtubeDownloadRequested.connect(self.start_youtube_download)
        self.settings_panel.settingsChanged.connect(self.on_settings_changed)
        
        self.loop_table.loopSelected.connect(self.on_loop_selected)

        self.controls_panel.playRequested.connect(self.on_play_requested)
        self.controls_panel.pauseRequested.connect(self.player_vm.pause)
        self.controls_panel.stopRequested.connect(self.player_vm.stop)
        self.controls_panel.seekRequested.connect(self.on_seek_requested)
        self.controls_panel.volumeChanged.connect(self.player_vm.set_volume)

        self.export_panel.exportRequested.connect(self.export_audio)

    def bind_viewmodels(self):
        # Bind Analysis updates to UI
        self.main_vm.analysisStarted.connect(self.on_analysis_started)
        self.main_vm.analysisProgress.connect(self.update_analysis_progress)
        self.main_vm.analysisStatus.connect(self.update_analysis_status)
        self.main_vm.analysisFinished.connect(self.on_analysis_finished)
        self.main_vm.analysisError.connect(self.show_error)
        self.main_vm.memoryDecisionRequested.connect(self.on_memory_decision_requested)

        # Bind Player updates to UI
        self.player_vm.playbackStateChanged.connect(self.controls_panel.update_state)
        self.player_vm.playbackProgress.connect(self.on_playback_progress)

    def show_error(self, message: str):
        QMessageBox.critical(self, self.tr_lang.get("error", "Error"), message)

    @pyqtSlot(dict, dict)
    def on_memory_decision_requested(self, mem_info: dict, strategy: dict):
        if hasattr(self, 'analysis_progress_dialog'):
            self.analysis_progress_dialog.hide()

        from views.components.memory_dialog import MemoryDecisionDialog
        dialog = MemoryDecisionDialog(self, mem_info, strategy, self.tr_lang)
        dialog.exec()
        
        choice = dialog.get_choice()
        
        self.main_vm.set_memory_decision(choice)

        if choice != "" and hasattr(self, 'analysis_progress_dialog'):
            self.analysis_progress_dialog.show()

    def closeEvent(self, event):
        self.player_vm.stop()
        event.accept()

    # --- Actions / Slots ---
    def on_file_selected(self, filepath: str):
        self.start_analysis()

    def start_youtube_download(self, url: str):
        self.download_progress = QProgressDialog(
            self.tr_lang.get("initializing", "Initializing..."),
            self.tr_lang.get("cancel", "Cancel"), 
            0, 100, self
        )
        self.download_progress.setWindowTitle(self.tr_lang.get("downloading_title", "Downloading"))
        self.download_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.download_progress.canceled.connect(self.cancel_download)

        self.download_thread = YoutubeDownloadThread(url, self.tr_lang)
        self.download_thread.progress.connect(self.update_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def update_download_progress(self, progress, status):
        if hasattr(self, 'download_progress'):
            self.download_progress.setValue(int(progress))
            self.download_progress.setLabelText(status)

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()

    def on_download_finished(self, filepath):
        self.file_panel.set_file_path(filepath)
        self.start_analysis()

    def on_download_error(self, error_msg):
        if hasattr(self, 'download_progress'):
            self.download_progress.cancel()
        if "cancelled" not in error_msg.lower():
            self.show_error(error_msg)

    def start_analysis(self):
        filepath = self.file_panel.get_file_path()
        if not filepath:
            self.show_error(self.tr_lang.get("select_file", "Please select a file."))
            return

        self.player_vm.stop()
        
        self.main_vm.start_analysis(
            filepath,
            self.settings_panel.get_min_duration(),
            self.settings_panel.get_score_weights(),
            self.locale_code
        )

    def on_analysis_started(self):
        self.analysis_progress_dialog = QProgressDialog(
            self.tr_lang.get("analyzing", "Analyzing..."), 
            None, 0, 100, self
        )
        self.analysis_progress_dialog.setWindowTitle(self.tr_lang.get("processing", "Processing"))
        self.analysis_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.analysis_progress_dialog.setMinimumDuration(0)
        self.analysis_progress_dialog.setValue(0)
        self.loop_table.clear_table()

    def update_analysis_progress(self, progress: int):
        if hasattr(self, 'analysis_progress_dialog'):
            self.analysis_progress_dialog.setValue(progress)

    def update_analysis_status(self, status: str):
        if hasattr(self, 'analysis_progress_dialog'):
            self.analysis_progress_dialog.setLabelText(status)

    def on_analysis_finished(self, loops, looper):
        if hasattr(self, 'analysis_progress_dialog'):
            self.analysis_progress_dialog.close()
            
        self.player_vm.load_looper(looper)
        self.all_loops = loops
        self.on_settings_changed()

    def on_settings_changed(self):
        if not hasattr(self, 'all_loops') or not self.all_loops:
            return

        score_weights = self.settings_panel.get_score_weights()
        for loop in self.all_loops:
            loop.score = (
                score_weights['original'] * getattr(loop, 'original_score', 0) +
                score_weights['structure'] * getattr(loop, 'structure_score', 0) +
                score_weights['chord'] * getattr(loop, 'chord_score', 0) +
                score_weights['mfcc'] * getattr(loop, 'mfcc_score', 0)
            )

        sorted_loops = sorted(enumerate(self.all_loops), key=lambda x: x[1].score, reverse=True)
        self.loop_table.populate(sorted_loops, self.main_vm.looper)

    def on_loop_selected(self, index: int):
        self.player_vm.stop()
        self.on_play_requested()

    def get_selected_loop(self):
        selected_items = self.loop_table.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        item = self.loop_table.item(row, 0)
        orig_index = item.data(Qt.ItemDataRole.UserRole)
        return self.all_loops[orig_index]

    def on_play_requested(self):
        if self.player_vm.playback_service.is_playing and self.player_vm.playback_service.is_paused:
            self.player_vm.resume()
            return

        if not self.main_vm.looper:
            self.show_error(self.tr_lang.get("analyze_first", "Analyze first"))
            return
            
        loop = self.get_selected_loop()
        if not loop:
            self.show_error(self.tr_lang.get("select_loop", "Select loop"))
            return
            
        row = self.loop_table.selectedItems()[0].row()
        title_fmt = self.tr_lang.get("export_playing_title", "MusicLooper - Playing #{}")
        self.setWindowTitle(title_fmt.format(row))
        
        start_seconds = self.main_vm.looper.samples_to_seconds(loop.loop_start)
        end_seconds = self.main_vm.looper.samples_to_seconds(loop.loop_end)
        self.controls_panel.update_progress(0, "00:00", self.format_time(end_seconds - start_seconds))
            
        self.player_vm.play_loop(loop.loop_start, loop.loop_end)

    def on_seek_requested(self, percent: int):
        if not self.main_vm.looper: return
        loop_start = self.player_vm.current_loop_start
        loop_end = self.player_vm.current_loop_end
        if loop_start == 0 and loop_end == 0: return
        
        start_seconds = self.main_vm.looper.samples_to_seconds(loop_start)
        end_seconds = self.main_vm.looper.samples_to_seconds(loop_end)
        duration = end_seconds - start_seconds
        
        position = start_seconds + (duration * percent / 100)
        frame = self.main_vm.looper.seconds_to_samples(position)
        self.player_vm.seek(frame)

    def on_playback_progress(self, frame, loop_count):
        if not self.main_vm.looper: return
        loop_start = self.player_vm.current_loop_start
        loop_end = self.player_vm.current_loop_end
        if loop_start == 0 and loop_end == 0: return

        start_seconds = self.main_vm.looper.samples_to_seconds(loop_start)
        end_seconds = self.main_vm.looper.samples_to_seconds(loop_end)
        current_time = (frame - loop_start) / self.main_vm.looper.mlaudio.rate
        total_time = end_seconds - start_seconds
        
        if current_time >= 0 and total_time > 0:
            percent = min(100, int((current_time / total_time) * 100))
            self.controls_panel.update_progress(
                percent, 
                self.format_time(current_time), 
                self.format_time(total_time)
            )

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def export_audio(self):
        loop = self.get_selected_loop()
        if not loop or not self.main_vm.looper:
            self.show_error(self.tr_lang.get("select_loop_first", "Please select a loop first"))
            return
            
        output_dir = QFileDialog.getExistingDirectory(
            self, 
            self.tr_lang.get("select_output", "Select Export Directory")
        )
        if not output_dir:
            return
            
        try:
            self.main_vm.looper.export(loop.loop_start, loop.loop_end, format="WAV", output_dir=output_dir)
            msg = self.tr_lang.get("export_success", "Export complete")
            QMessageBox.information(self, self.tr_lang.get("success", "Success"), f"{msg}\n{output_dir}")
        except Exception as e:
            self.show_error(str(e))
