import os
import cv2
import numpy as np
from typing import Dict, Tuple
from src.vision.vision_manager import VisionManager
from src.utils.logger import log

class BotState:
    LOADING = "STATE_LOADING"
    MAIN_MENU = "STATE_MAIN_MENU"
    PVP_MENU = "STATE_PVP_MENU"
    SEARCH = "STATE_SEARCH"
    AD = "STATE_AD"
    BATTLE = "STATE_BATTLE"
    END = "STATE_END"

class StateMachine:
    def __init__(self, vision_manager: VisionManager):
        self.vision = vision_manager
        self.current_state = BotState.MAIN_MENU
        self.confidences: Dict[str, float] = {
            BotState.LOADING: 0.0,
            BotState.MAIN_MENU: 0.0,
            BotState.PVP_MENU: 0.0,
            BotState.SEARCH: 0.0,
            BotState.AD: 0.0,
            BotState.BATTLE: 0.0,
            BotState.END: 0.0
        }

    def update_state(self, frame: np.ndarray) -> Tuple[str, float]:
        if frame is None:
            return self.current_state, self.confidences[self.current_state]

        # Güven puanlarını sıfırla
        for state in self.confidences:
            self.confidences[state] = 0.0

        # =========================================================================
        # 🚀 1. İSTER: KESİN REKLAM ŞABLONLARI İLE ERKEN TEŞHİS KONTROLÜ (BYPASS)
        # =========================================================================
        h, w, _ = frame.shape
        force_ad_state = False

        # Yeni Eklenen: ad7.png kriter kontrolü
        is_ad7, ad7_val, _ = self.vision.template_matching(frame, "ad7.png", 0.65)
        if is_ad7:
            self.confidences[BotState.AD] = ad7_val * 100
            force_ad_state = True
            log.info(f"[AD IDENTIFIER] ad7.png matched on view. Score: {ad7_val*100:.1f}%")

        # Yeni Eklenen: ad8.png kriter kontrolü
        if not force_ad_state:
            is_ad8, ad8_val, _ = self.vision.template_matching(frame, "ad8.png", 0.65)
            if is_ad8:
                self.confidences[BotState.AD] = ad8_val * 100
                force_ad_state = True
                log.info(f"[AD IDENTIFIER] ad8.png matched on view. Score: {ad8_val*100:.1f}%")

        # Yeni Eklenen: ad9.png kriter kontrolü
        if not force_ad_state:
            is_ad9, ad9_val, _ = self.vision.template_matching(frame, "ad9.png", 0.65)
            if is_ad9:
                self.confidences[BotState.AD] = ad9_val * 100
                force_ad_state = True
                log.info(f"[AD IDENTIFIER] ad9.png matched on view. Score: {ad9_val*100:.1f}%")

        # adspeaker.png kontrolü (Sol Üst Köşe - Merkez 28, 45)
        if not force_ad_state and h >= 95 and w >= 80:
            crop_speaker = frame[0:100, 0:80]
            found_speaker, s_val, _ = self.vision.template_matching(crop_speaker, "adspeaker.png", 0.65)
            if found_speaker:
                self.confidences[BotState.AD] = s_val * 100
                force_ad_state = True
                log.info(f"[AD IDENTIFIER] adspeaker.png matched at corner area (28, 45). Score: {s_val*100:.1f}%")

        # ad6.png kontrolü (Sağ Üst Köşe - Merkez 1558, 46)
        if not force_ad_state and h >= 100 and w >= 1600:
            crop_ad6 = frame[0:100, 1500:1600]
            found_ad6, a6_val, _ = self.vision.template_matching(crop_ad6, "ad6.png", 0.65)
            if found_ad6:
                self.confidences[BotState.AD] = a6_val * 100
                force_ad_state = True
                log.info(f"[AD IDENTIFIER] ad6.png matched at corner area (1558, 46). Score: {a6_val*100:.1f}%")

        # Eğer reklam teşhisi kesinleştiyse alt lobi hatlarını hiç tarama
        if force_ad_state:
            highest_state = BotState.AD
            highest_value = self.confidences[BotState.AD]
        else:
            # =========================================================================
            # STANDART DURUM TARAMA HATTI
            # =========================================================================
            # 1. STATE_LOADING
            is_loading, l_val, _ = self.vision.template_matching(frame, "loadingscreen.png", 0.75)
            if is_loading: 
                self.confidences[BotState.LOADING] = l_val * 100

            # 2. STATE_MAIN_MENU
            m1, v1, _ = self.vision.template_matching(frame, "mainscreengold.png", 0.65)
            m2, v2, _ = self.vision.template_matching(frame, "mainscreengem.png", 0.65)
            m3, v3, _ = self.vision.template_matching(frame, "mainscreen.png", 0.65)
            if m1 or m2 or m3:
                self.confidences[BotState.MAIN_MENU] = max([v1, v2, v3]) * 100

            # 3. STATE_BATTLE
            b1, bv1, _ = self.vision.template_matching(frame, "summon.png", 0.65)
            b2, bv2, _ = self.vision.template_matching(frame, "cantsummon.png", 0.65)
            b3, bv3, _ = self.vision.template_matching(frame, "skillnotready.png", 0.65)
            b4, bv4, _ = self.vision.template_matching(frame, "skillready.png", 0.65)
            if b1 or b2 or b3 or b4:
                self.confidences[BotState.BATTLE] = max([bv1, bv2, bv3, bv4]) * 100

            # 4. STATE_SEARCH
            s1, sv1, _ = self.vision.template_matching(frame, "pve10.png", 0.65)
            s2, sv2, _ = self.vision.template_matching(frame, "wait.png", 0.65)
            if s1 or s2:
                self.confidences[BotState.SEARCH] = max(sv1, sv2) * 100

            # 5. STATE_PVP_MENU
            pv_assets = ["pve1.png", "pve2.png", "pve3.png", "pve4.png", "pve5.png", "pve6.png", "pve7.png", "pve8.png", "pve9.png"]
            max_pv_val = 0.0
            for p_ast in pv_assets:
                p_found, p_val, _ = self.vision.template_matching(frame, p_ast, 0.70)
                if p_found and p_val > max_pv_val:
                    max_pv_val = p_val
            if max_pv_val > 0.0:
                self.confidences[BotState.PVP_MENU] = max_pv_val * 100

            # 6. STATE_END
            e1, ev1, _ = self.vision.template_matching(frame, "matchend.png", 0.75)
            e2, ev2, _ = self.vision.template_matching(frame, "matchend2.png", 0.75)
            e3, ev3, _ = self.vision.template_matching(frame, "matchend3.png", 0.75)
            if (e1 or e2 or e3) and self.confidences[BotState.PVP_MENU] == 0.0:
                self.confidences[BotState.END] = max([ev1, ev2, ev3]) * 100

            # En yüksek güven puanına sahip ana durumu belirle
            highest_state = max(self.confidences, key=lambda k: self.confidences[k])
            highest_value = self.confidences[highest_state]

            # 7. STATE_AD - ALT KORUMA VE VARSAYILAN ANOMALİ MANTIĞI
            if highest_value < 25.0:
                self.confidences[BotState.AD] = 30.0
                highest_state = BotState.AD
                highest_value = 30.0

        # Telemetri Loglama Metrisi
        log.info(f"[STATE ANALYSIS] State winner vector: {highest_state} ({highest_value:.1f}%) | BATTLE: {self.confidences[BotState.BATTLE]:.1f}% | PVP_MENU: {self.confidences[BotState.PVP_MENU]:.1f}% | END: {self.confidences[BotState.END]:.1f}%")

        if highest_value > 25.0:
            if self.current_state != highest_state:
                log.info(f"[STATE TRANSITION] Pipeline verified state change: {self.current_state} -> {highest_state}")
                self.current_state = highest_state
        
        return self.current_state, self.confidences[self.current_state]

    def check_ad_coordinates_for_recovery(self, frame: np.ndarray) -> bool:
        if frame is None: return False
        h, w, _ = frame.shape
        
        if h >= 1550 and w >= 400:
            crop1 = frame[1450:1550, 300:400]
            found1, _, _ = self.vision.template_matching(crop1, "ad1.png", 0.65)
            if found1: return True

        if h >= 1040 and w >= 500:
            crop2 = frame[940:1040, 400:500]
            found2, _, _ = self.vision.template_matching(crop2, "ad2.png", 0.65)
            if found2: return True

        if h >= 785 and w >= 500:
            crop3 = frame[685:785, 400:500]
            found3, _, _ = self.vision.template_matching(crop3, "ad3.png", 0.65)
            if found3: return True

        if h >= 125 and w >= 1560:
            crop5 = frame[25:125, 1470:1570]
            found5, _, _ = self.vision.template_matching(crop5, "ad5.png", 0.65)
            if found5: return True

        return False