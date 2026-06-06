"""
Adaptive Engine - Örnek Uygulamalar ve Kullanım Senaryoları

Bu dosya practical örnekler gösteriyor.
"""

# ========================================================================
# SENARYO 1: EARLY GAME - AGGRESSIVE SUMMON
# ========================================================================

def scenario_early_aggressive():
    """
    Oyun başladığında:
    - Aggressive summon rush (20-25 summon)
    - Minimal merge
    - Mana threshold düşük
    """
    print("=== EARLY GAME AGGRESSIVE ===")
    
    config = {
        "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}
    }
    
    board_manager = MockBoardManager()
    adb_manager = MockADBManager()
    
    from src.bot.adaptive_engine import AdaptiveDecisionEngine
    
    engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
    engine.battle_start_time = time.time()  # Şimdi başladı
    
    # Simülasyon: 5 frame
    for frame_idx in range(5):
        mana = 150 + frame_idx * 20
        
        # Board state örneği
        board_state = {
            "empty_slots": 8 + frame_idx,
            "card_count": 7 - frame_idx,
            "avg_rank": 1.0,
            "high_rank_count": 0,
            "duplicate_pairs": 0
        }
        
        action = engine.decide_action(board_state, mana, frame=None)
        print(f"Frame {frame_idx}: Action={action}, Mana={mana}")
        
        # Early game = Summon rush yapılacak


# ========================================================================
# SENARYO 2: MID GAME - BALANCED
# ========================================================================

def scenario_mid_balanced():
    """
    Oyun ortasında:
    - Merge odaklı
    - Summon daha az
    - Mana threshold orta
    """
    print("\n=== MID GAME BALANCED ===")
    
    config = {
        "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}
    }
    
    board_manager = MockBoardManager()
    adb_manager = MockADBManager()
    
    from src.bot.adaptive_engine import AdaptiveDecisionEngine
    
    engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
    engine.battle_start_time = time.time() - 60  # 60 saniye önce başladı = MID GAME
    
    # Simülasyon
    for frame_idx in range(5):
        mana = 200 + frame_idx * 30
        
        # Tahtada birleştirilecek kartlar var
        board_state = {
            "empty_slots": 2,
            "card_count": 13,
            "avg_rank": 1.5,
            "high_rank_count": 2,
            "duplicate_pairs": 2  # 2 merge pair var!
        }
        
        action = engine.decide_action(board_state, mana, frame=None)
        print(f"Frame {frame_idx}: Action={action}, Mana={mana}, Duplicate Pairs={board_state['duplicate_pairs']}")


# ========================================================================
# SENARYO 3: LATE GAME - SURVIVAL MODE
# ========================================================================

def scenario_late_survival():
    """
    Oyunun sonuna yakın:
    - Agresif merge
    - Minimum summon
    - Yüksek mana threshold upgrade
    """
    print("\n=== LATE GAME SURVIVAL ===")
    
    config = {
        "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}
    }
    
    board_manager = MockBoardManager()
    adb_manager = MockADBManager()
    
    from src.bot.adaptive_engine import AdaptiveDecisionEngine
    
    engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
    engine.battle_start_time = time.time() - 120  # 120 saniye = LATE GAME
    
    # Simülasyon
    for frame_idx in range(5):
        mana = 500 + frame_idx * 50
        
        board_state = {
            "empty_slots": 0,  # Tahta dolu!
            "card_count": 15,  # MAX
            "avg_rank": 2.0,
            "high_rank_count": 5,
            "duplicate_pairs": 3  # Merge merge merge!
        }
        
        action = engine.decide_action(board_state, mana, frame=None)
        print(f"Frame {frame_idx}: Action={action}, Mana={mana}, Empty Slots={board_state['empty_slots']}")
        
        # Late game = Merge'ü tercih etmeli


# ========================================================================
# SENARYO 4: STUCK BOARD DETECTION
# ========================================================================

def scenario_stuck_recovery():
    """
    Tahta değişmiyorsa recovery modu
    """
    print("\n=== STUCK BOARD RECOVERY ===")
    
    config = {
        "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}
    }
    
    board_manager = MockBoardManager()
    adb_manager = MockADBManager()
    
    from src.bot.adaptive_engine import AdaptiveDecisionEngine
    
    engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
    engine.battle_start_time = time.time()
    
    # Aynı board state 15 kez
    same_state = {
        "empty_slots": 2,
        "card_count": 13,
        "avg_rank": 1.5,
        "high_rank_count": 2,
        "duplicate_pairs": 0
    }
    
    for frame_idx in range(15):
        is_stuck = engine.is_board_stuck(same_state)
        print(f"Frame {frame_idx}: Stuck={is_stuck}")
        
        if is_stuck:
            print("⚠️  Board is stuck! Triggering recovery...")
            break


# ========================================================================
# SENARYO 5: PERFORMANCE ADAPTATION
# ========================================================================

def scenario_performance_learning():
    """
    Merge başarısına göre delay'ı dinamik olarak ayarla
    """
    print("\n=== PERFORMANCE ADAPTATION ===")
    
    config = {
        "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}
    }
    
    board_manager = MockBoardManager()
    adb_manager = MockADBManager()
    
    from src.bot.adaptive_engine import AdaptiveDecisionEngine, ActionResult
    
    engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
    engine.battle_start_time = time.time()
    
    # Merge başarısız 8 kez, başarılı 2 kez → 20% success rate
    print("\nSimülasyon: Başarısız merge'ler")
    for i in range(8):
        result = ActionResult(
            action_type="merge",
            timestamp=time.time(),
            success=False,  # BAŞARISISIZ!
            duration_ms=100.0,
            board_state_before=10,
            board_state_after=10,
            mana_before=200,
            mana_after=200
        )
        engine.metrics.record_action(result)
    
    # 2 başarılı
    for i in range(2):
        result = ActionResult(
            action_type="merge",
            timestamp=time.time(),
            success=True,  # BAŞARILI
            duration_ms=150.0,
            board_state_before=10,
            board_state_after=9,
            mana_before=200,
            mana_after=200
        )
        engine.metrics.record_action(result)
    
    merge_success_rate = engine.metrics.get_success_rate("merge")
    print(f"Merge success rate: {merge_success_rate:.1%}")
    
    # Strategy güncelle
    original_delay = engine.merge_delay
    engine.update_phase_strategy()
    
    print(f"Original merge delay: {original_delay:.3f}s")
    print(f"Adapted merge delay: {engine.merge_delay:.3f}s")
    
    if merge_success_rate < 0.70:
        print("✅ Delay INCREASED (çünkü başarı oranı düşük)")
        assert engine.merge_delay > original_delay


# ========================================================================
# MOCK CLASSES (TEST İÇİN)
# ========================================================================

class MockBoardManager:
    def __init__(self):
        self.memory = {}
    
    def update_board(self, frame):
        pass
    
    def get_cell_coordinates(self, cell_name):
        return (100, 100)


class MockADBManager:
    def tap(self, x, y):
        pass
    
    def swipe(self, x1, y1, x2, y2, duration):
        pass


# ========================================================================
# RUN EXAMPLES
# ========================================================================

if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("ADAPTIVE ENGINE - USAGE SCENARIOS")
    print("=" * 60)
    
    scenario_early_aggressive()
    scenario_mid_balanced()
    scenario_late_survival()
    scenario_stuck_recovery()
    scenario_performance_learning()
    
    print("\n" + "=" * 60)
    print("Bütün senaryolar başarıyla tamamlandı! ✅")
    print("=" * 60)
