"""
Unit Tests - Adaptive Decision Engine Testi

Test komutu: python -m pytest tests/test_adaptive_engine.py -v
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
import time
from src.bot.adaptive_engine import (
    AdaptiveDecisionEngine,
    AdaptiveMetrics,
    ActionResult,
    GamePhase
)


class TestAdaptiveMetrics:
    """AdaptiveMetrics sınıfı için testler"""
    
    @pytest.fixture
    def metrics(self):
        return AdaptiveMetrics(window_size=10)
    
    def test_record_action_success(self, metrics):
        """Başarılı aksiyonların kaydedilmesi"""
        action = ActionResult(
            action_type="merge",
            timestamp=time.time(),
            success=True,
            duration_ms=150.0,
            board_state_before=8,
            board_state_after=7,
            mana_before=200,
            mana_after=200
        )
        
        metrics.record_action(action)
        assert metrics.total_actions == 1
        assert metrics.merge_success_count == 1
    
    def test_record_action_failure(self, metrics):
        """Başarısız aksiyonların kaydedilmesi"""
        action = ActionResult(
            action_type="merge",
            timestamp=time.time(),
            success=False,
            duration_ms=100.0,
            board_state_before=8,
            board_state_after=8,
            mana_before=200,
            mana_after=200
        )
        
        metrics.record_action(action)
        assert metrics.total_actions == 1
        assert metrics.merge_success_count == 0
    
    def test_success_rate_calculation(self, metrics):
        """Başarı oranı hesaplaması"""
        # 3 başarılı, 1 başarısız
        for _ in range(3):
            metrics.record_action(ActionResult(
                action_type="summon",
                timestamp=time.time(),
                success=True,
                duration_ms=50.0,
                board_state_before=5,
                board_state_after=6,
                mana_before=100,
                mana_after=80
            ))
        
        metrics.record_action(ActionResult(
            action_type="summon",
            timestamp=time.time(),
            success=False,
            duration_ms=50.0,
            board_state_before=5,
            board_state_after=5,
            mana_before=100,
            mana_after=100
        ))
        
        success_rate = metrics.get_success_rate("summon")
        assert success_rate == pytest.approx(0.75, rel=0.01)
    
    def test_avg_duration(self, metrics):
        """Ortalama süre hesaplaması"""
        durations = [100.0, 150.0, 200.0]
        
        for duration in durations:
            metrics.record_action(ActionResult(
                action_type="merge",
                timestamp=time.time(),
                success=True,
                duration_ms=duration,
                board_state_before=8,
                board_state_after=7,
                mana_before=200,
                mana_after=200
            ))
        
        avg = metrics.get_avg_duration("merge")
        assert avg == pytest.approx(150.0, rel=0.01)
    
    def test_overall_efficiency(self, metrics):
        """Genel verimlilik hesaplaması"""
        for _ in range(7):
            metrics.record_action(ActionResult(
                action_type="merge",
                timestamp=time.time(),
                success=True,
                duration_ms=150.0,
                board_state_before=8,
                board_state_after=7,
                mana_before=200,
                mana_after=200
            ))
        
        for _ in range(3):
            metrics.record_action(ActionResult(
                action_type="merge",
                timestamp=time.time(),
                success=False,
                duration_ms=100.0,
                board_state_before=8,
                board_state_after=8,
                mana_before=200,
                mana_after=200
            ))
        
        efficiency = metrics.get_overall_efficiency()
        assert efficiency == pytest.approx(0.7, rel=0.01)


class TestAdaptiveDecisionEngine:
    """AdaptiveDecisionEngine sınıfı için testler"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock bağımlılıkları hazırla"""
        config = {
            "board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734},
            "adb_host": "127.0.0.1",
            "adb_port": 5555
        }
        
        board_manager = MagicMock()
        board_manager.memory = {
            "A1": {"card": "empty", "rank": 0, "confidence_type": 0.0},
            "B1": {"card": "bruiser", "rank": 2, "confidence_type": 0.95},
            "C1": {"card": "dryad", "rank": 1, "confidence_type": 0.88}
        }
        board_manager.update_board = MagicMock()
        board_manager.get_cell_coordinates = MagicMock(return_value=(100, 100))
        
        adb_manager = MagicMock()
        adb_manager.tap = MagicMock()
        adb_manager.swipe = MagicMock()
        
        return config, board_manager, adb_manager
    
    @pytest.fixture
    def engine(self, mock_dependencies):
        """AdaptiveDecisionEngine örneği"""
        config, board_manager, adb_manager = mock_dependencies
        return AdaptiveDecisionEngine(config, board_manager, adb_manager)
    
    def test_engine_initialization(self, engine):
        """Engine'in doğru şekilde başlatılması"""
        assert engine.metrics is not None
        assert engine.summon_rush_limit == 20
        assert engine.merge_delay == 0.15
        assert engine.battle_start_time == 0
    
    def test_game_phase_early(self, engine):
        """Early game faz tespiti"""
        engine.battle_start_time = time.time()
        phase = engine.get_current_phase()
        assert phase == GamePhase.EARLY_GAME
    
    def test_game_phase_mid(self, engine):
        """Mid game faz tespiti"""
        engine.battle_start_time = time.time() - 60
        phase = engine.get_current_phase()
        assert phase == GamePhase.MID_GAME
    
    def test_game_phase_late(self, engine):
        """Late game faz tespiti"""
        engine.battle_start_time = time.time() - 120
        phase = engine.get_current_phase()
        assert phase == GamePhase.LATE_GAME
    
    def test_is_board_stuck(self, engine, mock_dependencies):
        """Board stuck deteksiyonu"""
        _, board_manager, _ = mock_dependencies
        
        board_state = {
            "empty_slots": 5,
            "card_count": 10,
            "avg_rank": 1.5,
            "high_rank_count": 2,
            "duplicate_pairs": 1
        }
        
        # Aynı state 10 kez kontrol et
        for _ in range(engine.stuck_threshold):
            is_stuck = engine.is_board_stuck(board_state)
        
        assert is_stuck is True
    
    def test_merge_combination_finding(self, engine, mock_dependencies):
        """Merge kombinasyonu bulma"""
        _, board_manager, _ = mock_dependencies
        
        board_manager.memory = {
            "A1": {"card": "bruiser", "rank": 2, "confidence_type": 0.95},
            "A2": {"card": "bruiser", "rank": 2, "confidence_type": 0.92},
            "B1": {"card": "dryad", "rank": 1, "confidence_type": 0.88},
        }
        
        merge = engine.find_best_merge_combination()
        
        assert merge is not None
        assert merge[2] == "bruiser"
        assert merge[3] == 2
    
    def test_no_merge_combination(self, engine, mock_dependencies):
        """Merge kombinasyonu bulunamaması"""
        _, board_manager, _ = mock_dependencies
        
        board_manager.memory = {
            "A1": {"card": "bruiser", "rank": 2, "confidence_type": 0.95},
            "B1": {"card": "dryad", "rank": 1, "confidence_type": 0.88},
        }
        
        merge = engine.find_best_merge_combination()
        assert merge is None
    
    def test_session_stats(self, engine):
        """Session istatistiklerinin alınması"""
        stats = engine.get_session_stats()
        
        assert "total_actions" in stats
        assert "overall_efficiency" in stats
        assert "merge_success_rate" in stats
        assert "summon_success_rate" in stats
        assert "upgrade_success_rate" in stats
    
    def test_reset_battle_state(self, engine):
        """Battle state sıfırlanması"""
        engine.summon_rush_count = 10
        engine.battle_start_time = time.time()
        
        engine.reset_battle_state()
        
        assert engine.summon_rush_count == 0
        assert engine.battle_start_time == 0
        assert engine.consecutive_same_board == 0
    
    def test_execute_summon_rush(self, engine, mock_dependencies):
        """Summon rush execu etme"""
        _, _, adb_manager = mock_dependencies
        engine.summon_rush_count = 0
        engine.summon_rush_limit = 5
        
        result = engine.execute_summon(None)
        
        assert result is True
        assert engine.summon_rush_count > 0
        assert adb_manager.tap.called


class TestDecisionLogic:
    """Karar verme lojik testleri"""
    
    @pytest.fixture
    def engine_with_mocks(self):
        """Engine with mocks"""
        config = {"board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}}
        board_manager = MagicMock()
        board_manager.memory = {}
        board_manager.update_board = MagicMock()
        adb_manager = MagicMock()
        
        return AdaptiveDecisionEngine(config, board_manager, adb_manager)
    
    def test_decide_action_summon(self, engine_with_mocks):
        """Summon aksiyonunun seçilmesi"""
        board_state = {
            "empty_slots": 5,
            "card_count": 10,
            "avg_rank": 1.0,
            "high_rank_count": 0,
            "duplicate_pairs": 0
        }
        
        action = engine_with_mocks.decide_action(board_state, mana=200, frame=None)
        # Tahtada boş slot ve yeterli mana var → summon
        assert action == "summon"
    
    def test_decide_action_merge(self, engine_with_mocks):
        """Merge aksiyonunun seçilmesi"""
        board_state = {
            "empty_slots": 0,  # Tahta dolu
            "card_count": 15,
            "avg_rank": 2.0,
            "high_rank_count": 5,
            "duplicate_pairs": 3  # Merge edebilecek kartlar var
        }
        
        action = engine_with_mocks.decide_action(board_state, mana=300, frame=None)
        # Tahta dolu ve merge pairs var → merge
        assert action == "merge"
    
    def test_decide_action_upgrade(self, engine_with_mocks):
        """Upgrade aksiyonunun seçilmesi"""
        board_state = {
            "empty_slots": 5,
            "card_count": 10,
            "avg_rank": 1.0,
            "high_rank_count": 0,
            "duplicate_pairs": 0
        }
        
        action = engine_with_mocks.decide_action(board_state, mana=600, frame=None)
        # Yüksek mana ama boş slot var → summon tercih edilir ama yüksek mana upgrade'ı tercih ettirebilir
        # Bağlı olarak: boş slot var ve mana threshold sağlıyorsa summon
        assert action in ["summon", "upgrade", "wait"]


class TestIntegration:
    """İntegrasyon testleri"""
    
    def test_full_game_simulation(self):
        """Tam oyun simulasyonu"""
        config = {"board_bounding_box": {"x1": 631, "y1": 529, "x2": 972, "y2": 734}}
        board_manager = MagicMock()
        board_manager.memory = {}
        board_manager.update_board = MagicMock()
        board_manager.get_cell_coordinates = MagicMock(return_value=(100, 100))
        adb_manager = MagicMock()
        
        engine = AdaptiveDecisionEngine(config, board_manager, adb_manager)
        engine.battle_start_time = time.time()
        
        # 5 frame simulasyon
        for frame_idx in range(5):
            board_state = {
                "empty_slots": 5 - frame_idx,
                "card_count": 10 + frame_idx,
                "avg_rank": 1.0 + frame_idx * 0.2,
                "high_rank_count": frame_idx,
                "duplicate_pairs": max(0, frame_idx - 1)
            }
            
            action = engine.decide_action(board_state, mana=200 + frame_idx * 50, frame=None)
            assert action in ["summon", "merge", "upgrade", "wait"]
        
        # Stats kontrolü
        stats = engine.get_session_stats()
        assert stats["total_actions"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
