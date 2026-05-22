import os
import sys
import shutil
import locale
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from infrastructure.i18n import TRANSLATIONS

def setup_ffmpeg():
    """檢查 FFmpeg 是否可用，按以下順序：
    1. 檢查系統 PATH
    2. 檢查工作目錄下的 ffmpeg 資料夾
    3. 都找不到時提供下載連結
    """
    # 1. 先檢查系統 PATH
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')
    
    if ffmpeg_path and ffprobe_path:
        return True
        
    # 2. 檢查工作目錄下的 ffmpeg 資料夾
    current_dir = os.path.dirname(os.path.dirname(__file__)) # Pointing to src
    ffmpeg_dir = os.path.join(current_dir, "ffmpeg", "bin")
    
    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
    
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        # 將 FFmpeg 路徑加入環境變數
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
        return True
    
    return False

def show_ffmpeg_error():
    """Display FFmpeg error message and ask whether to open download page"""
    # 取得系統語言設定
    try:
        current_locale = locale.getlocale()[0]
        is_chinese = current_locale and any(
            current_locale.lower().startswith(loc) 
            for loc in ['zh', 'zh_tw', 'zh_hk', 'zh_cn', 'zh_sg', 'zh_mo', 'chinese (traditional)_taiwan']
        )
    except:
        is_chinese = False

    # 根據語言選擇錯誤訊息
    locale_code = 'zh_TW' if is_chinese else 'en'
    translations = TRANSLATIONS.get(locale_code, TRANSLATIONS['en'])
    error_msg = translations.get("ffmpeg_error_msg", "FFmpeg was not found. Please install it.")
    title = translations.get("error", "Error")

    # 顯示詢問對話框
    reply = QMessageBox.question(
        None,
        title,
        error_msg,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes  # 預設選項
    )
    
    # 如果使用者選擇是，則開啟下載頁面
    if reply == QMessageBox.StandardButton.Yes:
        QDesktopServices.openUrl(QUrl("https://ffmpeg.org/download.html"))
    
    # 直接結束程式
    sys.exit(1)
