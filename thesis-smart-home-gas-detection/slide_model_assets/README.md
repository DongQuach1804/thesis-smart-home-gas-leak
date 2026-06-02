# Slide model assets for LSTM + PPO v3

This folder contains the files used to rebuild the training outputs and create
slide-ready replacement images for the old thesis deck
`BasoCaoKLTN2_6_2026 (1).pptx`.

## Quick generate from current trained artifacts

```powershell
python slide_model_assets/generate_slide_assets.py
```

Output:

```text
slide_model_assets/generated/
```

## Full retrain/rebuild workflow

```powershell
.\slide_model_assets\run_training_for_slide_results.ps1
```

This runs:

- `processing/ml/lstm/train_forecaster.py`
- `processing/ml/rl/train_rl.py`
- thesis experiment chart scripts under `thesis-latex/exp_scripts`
- `slide_model_assets/generate_slide_assets.py`

## What to replace in the old slides

See:

```text
slide_model_assets/generated/replacement_map.md
```

Main corrections:

- LSTM is now a forecaster for `p_critical_5min`, not CO regression.
- PPO uses 8 state features and 4 actions.
- PPO training uses 400,000 timesteps and `VecNormalize`.
- Reward is v3 outcome-based; the old direct `+10/action-step` reward is removed.
