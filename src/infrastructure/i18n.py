import os
import json
from typing import Dict

def load_translations() -> Dict[str, Dict[str, str]]:
    """從 JSON 檔案載入翻譯文字"""
    translations = {}
    current_dir = os.path.dirname(__file__)
    src_dir = os.path.dirname(current_dir)
    languages_dir = os.path.join(src_dir, "languages")
    
    # 確保語言目錄存在
    if not os.path.exists(languages_dir):
        os.makedirs(languages_dir)
    
    # 讀取所有 JSON 檔案
    for filename in os.listdir(languages_dir):
        if filename.endswith('.json'):
            language_code = filename[:-5]  # 移除 .json 副檔名
            with open(os.path.join(languages_dir, filename), 'r', encoding='utf-8') as f:
                translations[language_code] = json.load(f)
    
    return translations

# 載入翻譯文字
TRANSLATIONS = load_translations()

# 如果沒有找到任何翻譯檔案，使用預設的英文翻譯
if not TRANSLATIONS:
    TRANSLATIONS = {
        "en": {
            "window_title": "MusicLooper",
            "error": "Error",
            "ffmpeg_error_msg": "FFmpeg was not found. Download it now?"
        }
    }
