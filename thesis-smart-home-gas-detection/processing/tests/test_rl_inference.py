"""
test_rl_inference.py — Tests cho RLInference wrapper (PPO agent).

Chạy:
    python -m pytest processing/tests/test_rl_inference.py -v --tb=short -s

Yêu cầu cho TestRLInferenceFull:
    - ppo_gas_agent.zip (chạy: python scripts/dev/pack_rl_model.py)
    - stable-baselines3 + torch
"""
import sys
from pathlib import Path
import pytest

# Add processing root to path
PROCESSING_ROOT = Path(__file__).parents[1]
if str(PROCESSING_ROOT) not in sys.path:
    sys.path.insert(0, str(PROCESSING_ROOT))

RL_MODEL_PATH = PROCESSING_ROOT / "ml" / "rl" / "ppo_gas_agent.zip"

# ── Stub tests (không cần model file cũng không cần torch/SB3) ───────────────

class TestRLInferenceStub:
    """Smoke tests — chỉ cần import, không load model hay torch."""

    def test_import(self):
        """Module import thành công ngay cả khi SB3 chưa cài."""
        try:
            from ml.inference.rl_inference import RLInference, ACTION_LABELS  # noqa
            assert set(ACTION_LABELS.values()) == {"NORMAL", "WARNING", "ALERT"}
        except ImportError as e:
            pytest.skip(f"Dependency thiếu: {e}")

    def test_missing_model_raises_file_not_found(self):
        """FileNotFoundError khi path không tồn tại (trước khi import SB3)."""
        try:
            from ml.inference.rl_inference import RLInference
        except ImportError as e:
            pytest.skip(f"Dependency thiếu: {e}")

        with pytest.raises(FileNotFoundError, match="Missing RL model"):
            RLInference("/nonexistent/ppo_agent.zip")


# ── Full tests (yêu cầu ppo_gas_agent.zip + stable-baselines3 + torch) ───────

@pytest.mark.skipif(not RL_MODEL_PATH.exists(), reason="ppo_gas_agent.zip chưa có — chạy: python scripts/dev/pack_rl_model.py")
class TestRLInferenceFull:
    """Full tests — load model thật, kiểm tra predict."""

    def setup_method(self):
        try:
            from ml.inference.rl_inference import RLInference
            self.agent = RLInference(str(RL_MODEL_PATH))
        except ImportError as e:
            pytest.skip(f"Thiếu dependency: {e}")

    # ── Model metadata ────────────────────────────────────────────────────────

    def test_obs_size_matches_trained_model(self):
        """Model phải có obs_size=19 (vì đã train với Box(19,))."""
        assert self.agent.obs_size == 19, (
            f"Unexpected obs_size={self.agent.obs_size}, expected 19"
        )
        print(f"\n  obs_size={self.agent.obs_size}")

    def test_n_actions_is_three(self):
        """Model phải có 3 actions: 0=NORMAL, 1=WARNING, 2=ALERT."""
        assert self.agent.n_actions == 3, (
            f"Unexpected n_actions={self.agent.n_actions}, expected 3"
        )
        print(f"  n_actions={self.agent.n_actions}")

    # ── Core predict behavior ─────────────────────────────────────────────────

    def test_action_is_valid_int(self):
        """choose_action() trả về int hợp lệ trong [0, n_actions-1]."""
        state = [0.15, 0.47, 0.62, 0.05] + [0.0] * 15   # 4 live features + 15 pad
        action = self.agent.choose_action(state)
        assert isinstance(action, int), f"Expected int, got {type(action)}"
        assert 0 <= action < self.agent.n_actions, (
            f"Action {action} out of range [0, {self.agent.n_actions-1}]"
        )
        print(f"\n  action={action}  label={self.agent.action_label(action)}")

    def test_auto_pad_short_input(self):
        """Input ngắn hơn obs_size phải được auto-pad bằng 0 (không lỗi)."""
        # Chỉ pass 4 features — phần còn lại tự pad
        action = self.agent.choose_action([0.15, 0.47, 0.62, 0.05])
        assert 0 <= action < self.agent.n_actions

    def test_auto_truncate_long_input(self):
        """Input dài hơn obs_size phải được truncate (không lỗi)."""
        long_state = list(range(50))   # 50 features >> 19
        action = self.agent.choose_action(long_state)
        assert 0 <= action < self.agent.n_actions

    def test_deterministic_same_state_same_action(self):
        """Cùng state → cùng action khi deterministic=True."""
        state = [0.35, 0.48, 0.65, 0.45] + [0.0] * 15
        a1 = self.agent.choose_action(state)
        a2 = self.agent.choose_action(state)
        assert a1 == a2, f"Non-deterministic: got {a1} then {a2}"
        print(f"\n  Deterministic action for state[:4]={state[:4]}: {a1}")

    # ── Action label helper ───────────────────────────────────────────────────

    def test_action_label_mapping(self):
        """action_label() trả về đúng string."""
        from ml.inference.rl_inference import ACTION_LABELS
        for action_int, expected_label in ACTION_LABELS.items():
            assert self.agent.action_label(action_int) == expected_label

    # ── Scenario tests ────────────────────────────────────────────────────────

    def test_three_risk_scenarios(self):
        """Chạy 3 scenarios tiêu biểu và in kết quả (không enforce action value)."""
        scenarios = {
            "Normal (gas=150ppm, risk=0.05)":   [150/2000, 28/60, 60/100, 0.05],
            "Warning (gas=600ppm, risk=0.55)":  [600/2000, 29/60, 65/100, 0.55],
            "Alert (gas=1400ppm, risk=0.88)":   [1400/2000, 32/60, 71/100, 0.88],
        }
        print()
        for label, features_4 in scenarios.items():
            state = features_4 + [0.0] * 15
            action = self.agent.choose_action(state)
            print(f"  {label}")
            print(f"    → action={action}  ({self.agent.action_label(action)})")
            assert 0 <= action < 3
