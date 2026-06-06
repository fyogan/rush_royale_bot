import threading
import time
import cv2
import numpy as np
import customtkinter as ctk
from src.adb.adb_manager import ADBManager
from src.state.state_machine import StateMachine, BotState
from src.vision.vision_manager import VisionManager
from src.vision.ocr_manager import OCRManager
from src.bot.board_manager import BoardManager
from src.bot.adaptive_engine import AdaptiveDecisionEngine
from src.bot.recovery_manager import RecoveryManager
from src.utils.logger import log

class BotGUIManager(ctk.CTk):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.title("Rush Royale Ultimate Control Panel")
        self.geometry("550x510")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.adb = ADBManager(config["adb_host"], config["adb_port"], config["package_name"])
        self.vision = VisionManager(config)
        self.ocr = OCRManager(config)
        self.state_machine = StateMachine(self.vision)
        self.board = BoardManager(config, self.vision)
        self.decision = AdaptiveDecisionEngine(config, self.board, self.adb)
        self.recovery = RecoveryManager(self.adb, self.state_machine)
        
        self.bot_running = False
        self.bot_thread: threading.Thread = None
        self.consecutive_stalls = 0
        self.last_metrics_update = time.time()
        
        self.create_widgets()

    def create_widgets(self):
        self.title_label = ctk.CTkLabel(self, text="RUSH ROYALE AUTOMATION SYSTEM", font=("Segoe UI", 18, "bold"), text_color="#3A86FF")
        self.title_label.pack(pady=12)
        
        self.btn_organize = ctk.CTkButton(self, text="FOTOGRAFLARI OTOMATIK ETIKETLE", font=("Segoe UI", 12, "bold"), fg_color="#2B2D42", hover_color="#8D99AE", command=self.action_organize_dataset)
        self.btn_organize.pack(pady=5, fill="x", padx=30)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=5)

        self.btn_connect = ctk.CTkButton(self.btn_frame, text="Connect ADB", font=("Segoe UI", 12, "bold"), fg_color="#FFB703", hover_color="#FB8500", text_color="#1A1A1A", command=self.action_connect)
        self.btn_connect.grid(row=0, column=0, padx=8)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="RUN BOT", font=("Segoe UI", 12, "bold"), fg_color="#2A9D8F", hover_color="#264653", command=self.action_start)
        self.btn_start.grid(row=0, column=1, padx=8)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="HALT", font=("Segoe UI", 12, "bold"), fg_color="#E63946", hover_color="#A81D27", command=self.action_stop)
        self.btn_stop.grid(row=0, column=2, padx=8)

        self.btn_scrape = ctk.CTkButton(self, text="VERI TOPLAMAYI BASLAT", font=("Segoe UI", 12, "bold"), fg_color="#D35400", hover_color="#E67E22", command=self.action_start_scraping)
        self.btn_scrape.pack(pady=8, fill="x", padx=30)

        self.btn_force_restart = ctk.CTkButton(self, text="OYUNU MANUEL YENIDEN BASLAT (TEST)", font=("Segoe UI", 12, "bold"), fg_color="#8E44AD", hover_color="#9B59B6", command=self.action_manual_restart)
        self.btn_force_restart.pack(pady=5, fill="x", padx=30)

        self.status_frame = ctk.CTkFrame(self, border_width=2, border_color="#3A86FF", fg_color="#1E1E24")
        self.status_frame.pack(pady=10, fill="x", padx=30)

        self.lbl_state = ctk.CTkLabel(self.status_frame, text="Engine Status: IDLE / DISCONNECTED", font=("Segoe UI", 14, "bold"), text_color="#E0E1DD")
        self.lbl_state.pack(pady=12)

        # ============ NEW: ADAPTIVE METRICS PANEL ============
        self.analytics_frame = ctk.CTkFrame(self, border_width=2, border_color="#27AE60", fg_color="#1A1A1A")
        self.analytics_frame.pack(pady=5, fill="x", padx=30)

        self.lbl_analytics_title = ctk.CTkLabel(
            self.analytics_frame, 
            text="📊 Adaptive Metrics", 
            font=("Segoe UI", 12, "bold"), 
            text_color="#27AE60"
        )
        self.lbl_analytics_title.pack(pady=5)

        self.lbl_metrics = ctk.CTkLabel(
            self.analytics_frame,
            text="Efficiency: 0% | Merge: 0% | Summon: 0%",
            font=("Segoe UI", 10),
            text_color="#E0E1DD",
            justify="left"
        )
        self.lbl_metrics.pack(pady=5)

        self.log_label = ctk.CTkLabel(self, text="Real-time Execution Telemetry Output:", font=("Segoe UI", 11, "italic"), text_color="#8D99AE")
        self.log_label.pack(anchor="w", padx=35)

        self.txt_log = ctk.CTkTextbox(self, width=480, height=180, font=("Consolas", 11), fg_color="#0F0F12", text_color="#00F5D4", border_width=1, border_color="#2B2D42")
        self.txt_log.pack(pady=5)

    def write_log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def update_metrics_display(self):
        """Metrikleri GUI'ye yazır"""
        if self.decision:
            stats = self.decision.get_session_stats()
            metric_text = (
                f"Efficiency: {stats['overall_efficiency']:.1%} | "
                f"Merge SR: {stats['merge_success_rate']:.1%} | "
                f"Summon SR: {stats['summon_success_rate']:.1%} | "
                f"Merge Delay: {stats['current_merge_delay']:.2f}s"
            )
            self.lbl_metrics.configure(text=metric_text)

    def action_connect(self):
        if self.adb.connect():
            self.write_log("[ADB STATUS] Link online.")
            self.lbl_state.configure(text="Engine Status: ADB CONNECTED", text_color="#00F5D4")
        else:
            self.write_log("[ADB STATUS] Failed.")

    def action_start(self):
        if not self.bot_running:
            self.bot_running = True
            threading.Thread(target=self.bot_loop, daemon=True).start()
            self.write_log("[SYSTEM] Bot started.")
            self.lbl_state.configure(text="Engine Status: ACTIVE", text_color="#2A9D8F")

    def action_stop(self):
        self.bot_running = False
        self.write_log("[SYSTEM] Bot stopped.")
        self.lbl_state.configure(text="Engine Status: HALTED", text_color="#FFB703")

    def action_organize_dataset(self):
        try:
            from src.bot.dataset_organizer import build_and_rename_dataset
            build_and_rename_dataset(self.config, self.vision)
            self.write_log("[ORGANIZER] Task complete.")
        except Exception as e:
            self.write_log(f"[ERROR] {str(e)}")

    def action_start_scraping(self):
        if self.bot_running: return
        self.btn_scrape.configure(state="disabled", text="TOPLANIYOR...")
        def run():
            try:
                from src.bot.dataset_scraper import start_scraping
                start_scraping(self.config, self.adb, 300, 3)
                self.after(0, lambda: self.write_log("[SCRAPER] Tamamlandi."))
            finally:
                self.after(0, lambda: self.btn_scrape.configure(state="normal", text="VERI TOPLAMAYI BASLAT"))
        threading.Thread(target=run, daemon=True).start()

    def action_manual_restart(self):
        try:
            self.recovery.handle_recovery(2) 
            self.write_log("[TEST] Restart tetiklendi.")
        except Exception as e:
            self.write_log(f"[ERROR] {str(e)}")

    def bot_loop(self):
        last_state = None
        state_start_time = time.time()
        self.last_metrics_update = time.time()
        
        while self.bot_running:
            try:
                frame = self.adb.take_screenshot()
                if frame is None:
                    time.sleep(1.0)
                    continue

                # ============ METRICS UPDATE ============
                if time.time() - self.last_metrics_update > 5.0:
                    self.after(0, self.update_metrics_display)
                    self.last_metrics_update = time.time()

                if self.state_machine.check_ad_coordinates_for_recovery(frame):
                    self.recovery.handle_recovery(1)
                    time.sleep(1.0)
                    continue

                state, confidence = self.state_machine.update_state(frame)
                
                # Global Timeout Kontrolü (120sn)
                if state == BotState.BATTLE:
                    state_start_time = time.time()
                elif state == last_state and (time.time() - state_start_time) > 120.0:
                    self.recovery.handle_recovery(2)
                    state_start_time = time.time()
                last_state = state

                # ============ ADAPTIVE ENGINE - BATTLE ============
                if state == BotState.BATTLE:
                    mana = self.ocr.extract_mana(frame)
                    self.decision.execute_battle_logic(mana, frame)

                # ============ MAIN MENU ============
                elif state == BotState.MAIN_MENU:
                    matched, _, loc = self.vision.template_matching(frame, "battle.png", 0.70)
                    if matched:
                        self.adb.tap(loc[0], loc[1])
                        # ============ RESET BATTLE STATE ============
                        self.decision.reset_battle_state()
                        time.sleep(2.5)
                        self.adb.tap(910, 710)

                # ============ PVP MENU ============
                elif state == BotState.PVP_MENU:
                    steps = [("pve1.png", (910, 710)), ("pve2.png", (1543, 54)), ("pve3.png", (1546, 54)), 
                             ("pve4.png", (1558, 41)), ("pve7.png", (836, 680)), ("pve8.png", (800, 328)), ("pve9.png", (883, 314))]
                    for asset, pos in steps:
                        matched, _, _ = self.vision.template_matching(frame, asset, 0.70)
                        if matched:
                            self.adb.tap(pos[0], pos[1])
                            time.sleep(1.5 if asset == "pve8.png" else 1.0)
                            break

                # ============ BATTLE END ============
                elif state == BotState.END:
                    matched, _, loc = self.vision.template_matching(frame, "matchend1.png", 0.65)
                    if matched:
                        self.adb.tap(loc[0], loc[1])
                        # ============ SAVE METRICS ============
                        self.decision.save_metrics()
                        stats = self.decision.get_session_stats()
                        self.write_log(f"[SESSION] {stats['total_actions']} actions | Efficiency: {stats['overall_efficiency']:.1%}")
                    time.sleep(1.5)
                    self.adb.tap(885, 510)

                # ============ AD STATE ============
                elif state == BotState.AD:
                    matched, _, _ = self.vision.template_matching(frame, "ad7.png", 0.65)
                    if matched:
                        self.adb.tap(77, 52)
                    else:
                        self.adb.tap(1550, 50)
                    time.sleep(2.0)

                time.sleep(0.2)
            except Exception as e:
                log.error(f"[CRASH] {str(e)}")
                time.sleep(2.0)
