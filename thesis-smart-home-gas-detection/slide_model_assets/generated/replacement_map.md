# Slide Replacement Map

Use these generated PNGs to replace the old model/result figures in
`BasoCaoKLTN2_6_2026 (1).pptx`.

| Old slide | Problem in old slide | Replacement asset |
|---|---|---|
| 6 | LSTM architecture has 64+32 LSTM, BatchNorm, and CO-style target | `01_lstm_forecaster_architecture.png` |
| 7 | Generic RL loop, not specific to GasLeakEnv/PPO | `02_ppo_control_loop_v3.png` |
| 8 | PPO config should stay v3/400k/VecNormalize | `03_ppo_training_config.png` |
| 9 | Input/output table should use 8-state gas controller and 4 actions | `04_ppo_input_output_table.png` |
| 10 | Reward slide should emphasize outcome-based v3 and removed +10 farming | `05_reward_v3_outcome_based.png` |
| 11-15 | Old CO/UCI regression progress and 200k PPO figures are obsolete | `06_training_metrics_summary.png`, `07_lstm_training_curve.png`, `10_ppo_reward_curve.png`, `11_controller_benchmark_chart.png` |
| Results/benchmark slides | Need final controller evidence | `11_controller_benchmark_chart.png`, `12_scenario_benchmark_chart.png` |

Key facts for narration:

- LSTM task: predict `p_critical_5min = P(max gas[t+1:t+300] > 1000 ppm)`.
- LSTM input: 60 seconds x 3 features (`gas_ppm`, `temperature_c`, `humidity_percent`).
- PPO input: 8-dimensional state including LSTM `p_critical_5min`.
- PPO output: `NO_OP`, `ALERT_USER`, `FAN_ON`, `CLOSE_VALVE`.
- PPO training: 400,000 timesteps, 4 parallel envs, `VecNormalize(norm_obs=False, norm_reward=True)`.
- Reward v3 removes the old direct `+10/action-step` incentive and rewards actual containment.
