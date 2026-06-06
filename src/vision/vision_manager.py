import os
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List
from src.utils.logger import log

class VisionManager:
    def __init__(self, config: dict, assets_dir: str = "assets"):
        self.config = config
        self.assets_dir = assets_dir
        self.templates: Dict[str, np.ndarray] = {}
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.akaze = cv2.AKAZE_create()
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.load_templates()

    def load_templates(self):
        if not os.path.exists(self.assets_dir):
            os.makedirs(self.assets_dir)
            log.warning(f"Assets directory '{self.assets_dir}' was missing, created empty directory.")
            
        required_assets = [
            "mainscreen.png", "mainscreengold.png", "mainscreengem.png", "battle.png",
            "pve1.png", "pve2.png", "pve3.png", "pve4.png", "pve5.png", "pve6.png",
            "pve7.png", "pve8.png", "pve9.png", "pve10.png", "pve11.png", "wait.png",
            "ad.png", "summon.png", "cantsummon.png", "skillready.png", "skillnotready.png",
            "heroskillready.png", "heroskillnotready.png", "bruiserrankup.png", "dryad.png",
            "harlequin.png", "mime.png", "trapper.png", "bruiser1.png", "bruiser2.png",
            "empty1.png", "empty2.png", "empty3.png", "rank1.png", "rank2.png",
            "rank3.png", "rank4.png", "rank5.png", "matchend.png", "matchend2.png",
            "matchend3.png", "loadingscreen.png"
        ]
        
        for asset in required_assets:
            path = os.path.join(self.assets_dir, asset)
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    self.templates[asset] = img
                else:
                    log.error(f"Could not decode asset: {asset}")
            else:
                log.warning(f"Asset target reference missing from directory: {asset}")

    def template_matching(self, target: np.ndarray, template_name: str, threshold: float = 0.75) -> Tuple[bool, float, Tuple[int, int]]:
        if template_name not in self.templates or target is None:
            return False, 0.0, (0, 0)
        
        tpl = self.templates[template_name]
        
        # Boyut koruması: Eğer template target'tan büyükse resize et
        if target.shape[0] < tpl.shape[0] or target.shape[1] < tpl.shape[1]:
            tpl = cv2.resize(tpl, (target.shape[1], target.shape[0]))
            
        res = cv2.matchTemplate(target, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= threshold:
            h, w, _ = tpl.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return True, float(max_val), (center_x, center_y)
        return False, float(max_val), (0, 0)

    def feature_matching(self, target: np.ndarray, template_name: str, algorithm: str = "ORB") -> Tuple[bool, float]:
        if template_name not in self.templates or target is None:
            return False, 0.0
            
        tpl = self.templates[template_name]
        gray_tpl = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        gray_tgt = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
        
        alg = self.orb if algorithm == "ORB" else self.akaze
        kp1, des1 = alg.detectAndCompute(gray_tpl, None)
        kp2, des2 = alg.detectAndCompute(gray_tgt, None)
        
        if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
            return False, 0.0
            
        matches = self.matcher.match(des1, des2)
        if not matches:
            return False, 0.0
            
        good_matches = [m for m in matches if m.distance < 45]
        ratio = len(good_matches) / max(len(matches), 1)
        return ratio > 0.15, float(ratio)

    def detect_rank(self, cell_img: np.ndarray) -> int:
        if cell_img is None:
            return 1
        gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        star_count = 0
        for cnt in contours:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            area = cv2.contourArea(cnt)
            if 30 < area < 400:
                if len(approx) >= 4:
                    star_count += 1
                    
        for r in range(1, 6):
            matched, val, _ = self.template_matching(cell_img, f"rank{r}.png", threshold=0.70)
            if matched:
                return r
                
        if 1 <= star_count <= 5:
            return star_count
        return 1