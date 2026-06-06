"""
Adaptive Decision Engine - Oyunun dinamik akışına göre kararları optimize eden sistem

Temel Konsept:
1. Performance Tracking: Her aksiyonun sonucunu kaydet
2. Success Rate Calculation: Merge/Summon/Upgrade başarısını ölç
3. Dynamic Parameters: Başarıya göre timing'leri ayarla
4. Context-Aware: Oyun aşamasına (early/mid/late) göre strateji değiştir
5. Learning: Geçmiş dataları kullanarak kararları iyileştir
"""

import time
import json
import os
from collections import deque
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from src.utils.logger import log


class GamePhase(Enum):
    """Oyunun farklı aşamaları"""
    EARLY_GAME = "early"      # 0-30 saniye
    MID_GAME = "mid"          # 30-90 saniye
    LATE_GAME = "late"        # 90+ saniye
    ENDGAME = "endgame"       # Savaş sona yakın


@dataclass
class ActionResult:
    """Bir aksiyonun sonucu"""
    action_type: str        # "summon", "merge", "upgrade"
    timestamp: float
    success: bool
    duration_ms: float
    board_state_before: int  # Tahtadaki kart sayısı
    board_state_after: int
    mana_before: int
    mana_after: int
    confidence: float = 1.0


class AdaptiveMetrics:
    """Sistem performans metriklerini takip eder"""
    
    def __init__(self, window_size=50):
        self.window_size = window_size
        self.action_history: deque = deque(maxlen=window_size)
        self.merge_success_count = 0
        self.summon_success_count = 0
        self.upgrade_success_count = 0
        self.total_actions = 0
        
    def record_action(self, result: ActionResult):
        """Bir aksiyonun sonucunu kaydet"""
        self.action_history.append(result)
        self.total_actions += 1
        
        if result.success:
            if result.action_type == "merge":
                self.merge_success_count += 1
            elif result.action_type == "summon":
                self.summon_success_count += 1
            elif result.action_type == "upgrade":
                self.upgrade_success_count += 1
    
    def get_success_rate(self, action_type: str) -> float:
        """Belirli aksiyon türü için başarı oranı"""
        actions = [a for a in self.action_history if a.action_type == action_type]
        if not actions:
            return 0.5  # Default
        
        success = sum(1 for a in actions if a.success)
        return success / len(actions)
    
    def get_avg_duration(self, action_type: str) -> float:
        """Aksiyonun ortalama süresi (ms)"""
        actions = [a for a in self.action_history if a.action_type == action_type]
        if not actions:
            return 100.0
        
        return sum(a.duration_ms for a in actions) / len(actions)
    
    def get_overall_efficiency(self) -> float:
        """Genel verimlilik (0.0 - 1.0)"""
        if not self.action_history:
            return 0.5
        
        successful = sum(1 for a in self.action_history if a.success)
        return successful / len(self.action_history)


class AdaptiveDecisionEngine:
    """
    Dinamik karar motoru - Oyunun realltime performansına göre ayarlanan bot
    """
    
    def __init__(self, config: dict, board_manager, adb_manager):
        self.config = config
        self.board = board_manager
        self.adb = adb_manager
        
        # ============ METRIKLER ============
        self.metrics = AdaptiveMetrics(window_size=100)
        self.game_start_time = time.time()
        self.battle_start_time = 0
        
        # ============ DİNAMİK PARAMETRELER ============
        # Summon Rush (Oyun başında agresif kart çağırma)
        self.summon_rush_count = 0
        self.summon_rush_limit = 20
        self.last_summon_time = 0
        self.summon_delay = 0.05  # Dinamik olarak ayarlanacak
        
        # Merge (Kart birleştirme)
        self.merge_delay = 0.15  # Dinamik olarak ayarlanacak
        self.merge_enabled = True
        
        # Upgrade (Kart yükseltme)
        self.last_upgrade_time = 0
        self.upgrade_interval = 45  # Dinamik olarak ayarlanacak
        self.upgrade_threshold = 500  # Dinamik olarak ayarlanacak
        
        # ============ STRATEJI PARAMETRELERİ ============
        self.strategy_params = {
            "early": {
                "summon_rush_limit": 25,
                "mana_threshold_summon": 100,
                "merge_priority": False,
                "upgrade_aggressive": False
            },
            "mid": {
                "summon_rush_limit": 15,
                "mana_threshold_summon": 150,
                "merge_priority": True,
                "upgrade_aggressive": True
            },
            "late": {
                "summon_rush_limit": 10,
                "mana_threshold_summon": 200,
                "merge_priority": True,
                "upgrade_aggressive": True
            },
            "endgame": {
                "summon_rush_limit": 0,
                "mana_threshold_summon": 250,
                "merge_priority": True,
                "upgrade_aggressive": False
            }
        }
        
        # ============ ADAPTE PARAMETRELER ============
        self.adaptive_params = self.strategy_params["early"].copy()
        
        # ============ DURUM TAKIBI ============
        self.last_board_state = {}
        self.consecutive_same_board = 0
        self.stuck_threshold = 10  # Kaç frame aynı kalsın stuck sayılsın
        
        log.info("[ADAPTIVE] Adaptive Decision Engine initialized")
    
    # ========================================================================
    # GAME PHASE DETECTION
    # ========================================================================
    
    def get_current_phase(self) -> GamePhase:
        """Oyunun hangi aşamasında olduğunu belirle"""
        elapsed = time.time() - self.battle_start_time
        
        if elapsed < 30:
            return GamePhase.EARLY_GAME
        elif elapsed < 90:
            return GamePhase.MID_GAME
        elif elapsed < 180:
            return GamePhase.LATE_GAME
        else:
            return GamePhase.ENDGAME
    
    def update_phase_strategy(self):
        """Oyun aşamasına göre parametreleri güncelle"""
        phase = self.get_current_phase()
        
        # Bazal stratejiye başarı metriklerine göre adaptasyon ekle
        base_strategy = self.strategy_params[phase.value]
        
        # Merge başarısı düşükse merge delay'i artır
        merge_success = self.metrics.get_success_rate("merge")
        if merge_success < 0.70:
            adjusted_merge_delay = self.merge_delay * 1.2
        elif merge_success > 0.95:
            adjusted_merge_delay = self.merge_delay * 0.9
        else:
            adjusted_merge_delay = self.merge_delay
        
        # Summon başarısı düşükse threshold'u artır
        summon_success = self.metrics.get_success_rate("summon")
        if summon_success < 0.75:
            adjusted_mana_threshold = base_strategy["mana_threshold_summon"] * 1.1
        else:
            adjusted_mana_threshold = base_strategy["mana_threshold_summon"]
        
        # Dinamik parametreleri güncelle
        self.merge_delay = max(0.10, min(0.30, adjusted_merge_delay))
        self.adaptive_params["mana_threshold_summon"] = int(adjusted_mana_threshold)
        self.adaptive_params.update(base_strategy)
        
        log.info(f"[ADAPTIVE-PHASE] {phase.name} | Merge Delay: {self.merge_delay:.2f}s | Success Rate: {self.metrics.get_overall_efficiency():.1%}")
    
    # ========================================================================
    # BOARD STATE ANALYSIS
    # ========================================================================
    
    def analyze_board_state(self, frame) -> Dict:
        """Tahta durumunu analiz et"""
        self.board.update_board(frame)
        
        board_state = {
            "empty_slots": 0,
            "card_count": 0,
            "avg_rank": 0,
            "high_rank_count": 0,
            "duplicate_pairs": 0
        }
        
        ranks = []
        card_positions: Dict[str, List] = {}
        
        for cell, data in self.board.memory.items():
            if data["card"] == "empty":
                board_state["empty_slots"] += 1
            else:
                board_state["card_count"] += 1
                ranks.append(data["rank"])
                
                card_name = data["card"]
                if card_name not in card_positions:
                    card_positions[card_name] = []
                card_positions[card_name].append({
                    "cell": cell,
                    "rank": data["rank"],
                    "confidence": data["confidence_type"]
                })
        
        # Ortalama rank
        if ranks:
            board_state["avg_rank"] = sum(ranks) / len(ranks)
            board_state["high_rank_count"] = sum(1 for r in ranks if r >= 3)
        
        # Merge edebilecek kartların sayısı (aynı tip ve rank)
        for card_type, positions in card_positions.items():
            # Rank'a göre grupla
            by_rank = {}
            for pos in positions:
                rank = pos["rank"]
                if rank not in by_rank:
                    by_rank[rank] = []
                by_rank[rank].append(pos)
            
            # Pairs sayısı
            for rank, items in by_rank.items():
                if len(items) >= 2:
                    board_state["duplicate_pairs"] += len(items) // 2
        
        return board_state
    
    def is_board_stuck(self, current_state: Dict) -> bool:
        """Tahta değişmiyorsa stuck olmuş demektir"""
        if not self.last_board_state:
            self.last_board_state = current_state
            return False
        
        # Durum karşılaştır
        if (current_state["card_count"] == self.last_board_state["card_count"] and
            current_state["empty_slots"] == self.last_board_state["empty_slots"]):
            self.consecutive_same_board += 1
        else:
            self.consecutive_same_board = 0
        
        self.last_board_state = current_state
        
        is_stuck = self.consecutive_same_board >= self.stuck_threshold
        if is_stuck:
            log.warning(f"[ADAPTIVE-STUCK] Board hasn't changed for {self.stuck_threshold} frames!")
        
        return is_stuck
    
    # ========================================================================
    # ACTION EXECUTION
    # ========================================================================
    
    def execute_summon(self, frame) -> bool:
        """Akıllı kart çağırma"""
        action_start = time.time()
        
        # Summon Rush fazi (oyun başında agresif)
        if self.summon_rush_count < self.summon_rush_limit:
            burst_size = min(5, self.summon_rush_limit - self.summon_rush_count)
            
            for _ in range(burst_size):
                self.adb.tap(779, 766)
                self.summon_rush_count += 1
                time.sleep(self.summon_delay)
            
            result = ActionResult(
                action_type="summon",
                timestamp=time.time(),
                success=True,
                duration_ms=(time.time() - action_start) * 1000,
                board_state_before=0,  # TODO: uygun değerler ekle
                board_state_after=0,
                mana_before=0,
                mana_after=0
            )
            self.metrics.record_action(result)
            log.info(f"[SUMMON-RUSH] Executed burst ({self.summon_rush_count}/{self.summon_rush_limit})")
            
            return True
        
        # Normal summon (boş slot varsa)
        return False
    
    def execute_merge(self, frame) -> bool:
        """Akıllı kart birleştirme"""
        action_start = time.time()
        
        board_state = self.analyze_board_state(frame)
        
        if board_state["empty_slots"] > 0 or board_state["duplicate_pairs"] == 0:
            return False
        
        # En iyi merge kombinasyon bul
        best_merge = self.find_best_merge_combination()
        
        if not best_merge:
            return False
        
        cell_a, cell_b, card_type, rank = best_merge
        loc_a = self.board.get_cell_coordinates(cell_a)
        loc_b = self.board.get_cell_coordinates(cell_b)
        
        # Merge'ü gerçekleştir
        self.adb.swipe(loc_a[0], loc_a[1], loc_b[0], loc_b[1], int(self.merge_delay * 1000))
        time.sleep(self.merge_delay)
        
        result = ActionResult(
            action_type="merge",
            timestamp=time.time(),
            success=True,
            duration_ms=(time.time() - action_start) * 1000,
            board_state_before=board_state["card_count"],
            board_state_after=board_state["card_count"] - 1,
            mana_before=0,
            mana_after=0
        )
        self.metrics.record_action(result)
        
        log.info(f"[MERGE] {card_type} R{rank}: {cell_a} → {cell_b}")
        return True
    
    def execute_upgrade(self, mana: int) -> bool:
        """Akıllı kart yükseltme"""
        action_start = time.time()
        current_time = time.time()
        
        # Upgrade interval'ını kontrol et
        if current_time - self.last_upgrade_time < self.upgrade_interval:
            return False
        
        # Mana threshold'unu kontrol et
        if mana < self.upgrade_threshold:
            return False
        
        # Upgrade'ı gerçekleştir
        self.adb.tap(592, 840)
        self.last_upgrade_time = current_time
        
        result = ActionResult(
            action_type="upgrade",
            timestamp=time.time(),
            success=True,
            duration_ms=(time.time() - action_start) * 1000,
            board_state_before=0,
            board_state_after=0,
            mana_before=mana,
            mana_after=mana - self.upgrade_threshold
        )
        self.metrics.record_action(result)
        
        log.info(f"[UPGRADE] Executed at mana={mana}")
        return True
    
    # ========================================================================
    # DECISION LOGIC
    # ========================================================================
    
    def find_best_merge_combination(self) -> Optional[Tuple]:
        """
        Merge yapmak için en iyi kombinasyonu bul
        Prioritize: Highest rank → Highest type value
        """
        card_by_type_rank: Dict[Tuple, List] = {}
        
        for cell, data in self.board.memory.items():
            if data["card"] == "empty":
                continue
            
            key = (data["card"], data["rank"])
            if key not in card_by_type_rank:
                card_by_type_rank[key] = []
            
            card_by_type_rank[key].append(cell)
        
        # Merge edilebilecek kombinasyonları bul (2+ aynı tip/rank)
        mergeable = [(k, v) for k, v in card_by_type_rank.items() if len(v) >= 2]
        
        if not mergeable:
            return None
        
        # Rank'e göre öncelik (yüksek rank önce)
        mergeable.sort(key=lambda x: x[0][1], reverse=True)
        
        best = mergeable[0]
        card_type, rank = best[0]
        cells = best[1]
        
        return (cells[0], cells[1], card_type, rank)
    
    def decide_action(self, board_state: Dict, mana: int, frame) -> str:
        """
        Hangi aksiyonu yapacağını karara ver
        Returns: "summon", "merge", "upgrade", "wait"
        """
        
        # Stuck kontrolü
        if self.is_board_stuck(board_state):
            log.warning("[ADAPTIVE-DECISION] Board is stuck, forcing merge attempt")
            return "merge"
        
        # Oyun aşamasına göre strateji güncelle
        self.update_phase_strategy()
        
        # Aksiyonların dinamik sırasını belirle
        action_scores = {
            "summon": 0.0,
            "merge": 0.0,
            "upgrade": 0.0
        }
        
        # SUMMON SCORE
        if board_state["empty_slots"] > 0 and mana >= self.adaptive_params.get("mana_threshold_summon", 150):
            action_scores["summon"] = 10.0
            if self.metrics.get_success_rate("summon") > 0.8:
                action_scores["summon"] += 3.0
        
        # MERGE SCORE
        if board_state["duplicate_pairs"] > 0:
            action_scores["merge"] = 8.0
            if board_state["empty_slots"] == 0:  # Tahta dolu
                action_scores["merge"] += 5.0
            if self.metrics.get_success_rate("merge") > 0.85:
                action_scores["merge"] += 2.0
        
        # UPGRADE SCORE
        if mana > self.upgrade_threshold:
            action_scores["upgrade"] = 5.0
            if self.adaptive_params.get("upgrade_aggressive", False):
                action_scores["upgrade"] += 3.0
        
        # En yüksek skora sahip aksiyonu seç
        best_action = max(action_scores, key=action_scores.get)
        
        if action_scores[best_action] <= 0:
            return "wait"
        
        log.debug(f"[DECISION] Scores: {action_scores} → Best: {best_action}")
        return best_action
    
    def execute_battle_logic(self, mana: int, frame) -> bool:
        """Ana karar döngüsü"""
        
        # İlk savaş başlangıcı
        if self.battle_start_time == 0:
            self.battle_start_time = time.time()
            log.info("[ADAPTIVE] Battle started, initializing metrics")
        
        # Tahta durumunu analiz et
        board_state = self.analyze_board_state(frame)
        
        # Güvenli mana değeri
        if mana is None or mana <= 0:
            mana = 100
        
        # Karar al
        action = self.decide_action(board_state, mana, frame)
        
        # Aksiyonu gerçekleştir
        if action == "summon":
            return self.execute_summon(frame)
        elif action == "merge":
            return self.execute_merge(frame)
        elif action == "upgrade":
            return self.execute_upgrade(mana)
        
        return False
    
    def reset_battle_state(self):
        """Yeni bir savaş başladığında resetle"""
        self.summon_rush_count = 0
        self.battle_start_time = 0
        self.last_upgrade_time = 0
        self.consecutive_same_board = 0
        self.last_board_state = {}
        log.info("[ADAPTIVE] Battle state reset for new match")
    
    # ========================================================================
    # ANALYTICS & PERSISTENCE
    # ========================================================================
    
    def get_session_stats(self) -> Dict:
        """Session istatistiklerini al"""
        return {
            "total_actions": self.metrics.total_actions,
            "overall_efficiency": self.metrics.get_overall_efficiency(),
            "merge_success_rate": self.metrics.get_success_rate("merge"),
            "summon_success_rate": self.metrics.get_success_rate("summon"),
            "upgrade_success_rate": self.metrics.get_success_rate("upgrade"),
            "avg_merge_duration_ms": self.metrics.get_avg_duration("merge"),
            "current_merge_delay": self.merge_delay,
            "current_upgrade_interval": self.upgrade_interval,
        }
    
    def save_metrics(self, filepath: str = "adaptive_metrics.json"):
        """Metrikleri kaydet"""
        stats = self.get_session_stats()
        
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        
        log.info(f"[ADAPTIVE] Metrics saved to {filepath}")
