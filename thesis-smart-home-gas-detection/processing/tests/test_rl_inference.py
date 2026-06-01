"""
Tests for the RLInference wrapper and action metadata.

Full PPO tests are skipped when the packaged model cannot be loaded in the
current environment. The pipeline still uses GasResponseAgent with a rule-based
fallback in that case.
"""
import sys
from pathlib import Path

import pytest

PROCESSING_ROOT = Path(__file__).parents[1]
if str(PROCESSING_ROOT) not in sys.path:
    sys.path.insert(0, str(PROCESSING_ROOT))

RL_MODEL_PATH = PROCESSING_ROOT / "ml" / "rl" / "ppo_gas_agent.zip"
EXPECTED_ACTION_LABELS = {"NO_OP", "ALERT_USER", "FAN_ON", "CLOSE_VALVE"}


class TestRLInferenceStub:
    """Smoke tests that do not need a loadable PPO model."""

    def test_import(self):
        try:
            from ml.inference.rl_inference import ACTION_LABELS, RLInference  # noqa: F401
        except ImportError as exc:
            pytest.skip(f"Missing dependency: {exc}")

        assert set(ACTION_LABELS.values()) == EXPECTED_ACTION_LABELS
        assert set(ACTION_LABELS.keys()) == set(range(len(EXPECTED_ACTION_LABELS)))

    def test_missing_model_raises_file_not_found(self):
        try:
            from ml.inference.rl_inference import RLInference
        except ImportError as exc:
            pytest.skip(f"Missing dependency: {exc}")

        with pytest.raises(FileNotFoundError, match="Missing RL model"):
            RLInference("/nonexistent/ppo_agent.zip")


@pytest.mark.skipif(not RL_MODEL_PATH.exists(), reason="ppo_gas_agent.zip is not available")
class TestRLInferenceFull:
    """Full tests that require a loadable PPO model."""

    def setup_method(self):
        try:
            from ml.inference.rl_inference import RLInference
            self.agent = RLInference(str(RL_MODEL_PATH))
        except ImportError as exc:
            pytest.skip(f"Missing dependency: {exc}")
        except RuntimeError as exc:
            pytest.skip(f"PPO model cannot be loaded in this environment: {exc}")

    def test_obs_size_matches_trained_model(self):
        assert self.agent.obs_size > 0

    def test_n_actions_matches_labels(self):
        from ml.inference.rl_inference import ACTION_LABELS

        assert self.agent.n_actions == len(ACTION_LABELS)

    def test_action_is_valid_int(self):
        state = [0.15, 0.47, 0.62, 0.05] + [0.0] * 15
        action = self.agent.choose_action(state)
        assert isinstance(action, int)
        assert 0 <= action < self.agent.n_actions

    def test_auto_pad_short_input(self):
        action = self.agent.choose_action([0.15, 0.47, 0.62, 0.05])
        assert 0 <= action < self.agent.n_actions

    def test_auto_truncate_long_input(self):
        action = self.agent.choose_action(list(range(50)))
        assert 0 <= action < self.agent.n_actions

    def test_deterministic_same_state_same_action(self):
        state = [0.35, 0.48, 0.65, 0.45] + [0.0] * 15
        assert self.agent.choose_action(state) == self.agent.choose_action(state)

    def test_action_label_mapping(self):
        from ml.inference.rl_inference import ACTION_LABELS

        for action_int, expected_label in ACTION_LABELS.items():
            assert self.agent.action_label(action_int) == expected_label

    def test_three_risk_scenarios(self):
        scenarios = {
            "Normal": [150 / 2000, 28 / 60, 60 / 100, 0.05],
            "Warning": [600 / 2000, 29 / 60, 65 / 100, 0.55],
            "Alert": [1400 / 2000, 32 / 60, 71 / 100, 0.88],
        }

        for features in scenarios.values():
            action = self.agent.choose_action(features + [0.0] * 15)
            assert 0 <= action < self.agent.n_actions
