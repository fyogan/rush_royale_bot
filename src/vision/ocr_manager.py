import cv2
import numpy as np
import pytesseract
import re
import os
from typing import Optional
from src.utils.logger import log

class OCRManager:
    def __init__(self, config: dict):
        self.config = config
        self.bbox = self.config["ocr_mana_bounding_box"]
        
        # Windows işletim sistemi için Tesseract varsayılan kurulum yollarını kontrol et ve bağla
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                log.info(f"[OCR] Tesseract binary found and mapped to: {path}")
                break

    def extract_mana(self, frame: np.ndarray) -> int:
        if frame is None:
            return 0
        try:
            crop = frame[self.bbox["y1"]:self.bbox["y2"], self.bbox["x1"]:self.bbox["x2"]]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (0, 0), fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            cleaned_text = re.sub(r'\D', '', text.strip())
            
            if cleaned_text:
                mana_value = int(cleaned_text)
                log.info(f"[OCR] Processed Mana Bounding Box. Raw text: '{text.strip()}' -> Parsed Integer: {mana_value}")
                return mana_value
            
            log.warning("[OCR] Digit extraction sequence failed or area returned non-numeric values. Defaulting to 0.")
            return 0
        except Exception as e:
            log.error(f"[OCR] Tesseract dynamic exception context: {str(e)}. (Check if Tesseract is installed correctly on Windows)")
            return 0