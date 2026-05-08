"""
pack_rl_model.py — Đóng gói các file weights RL thành ppo_gas_agent.zip
mà stable-baselines3 PPO.load() có thể đọc.

Chạy từ project root:
    python scripts/dev/pack_rl_model.py
"""
import os
import zipfile
from pathlib import Path

RL_DIR  = Path(__file__).parents[2] / "processing" / "ml" / "rl"
OUT_ZIP = RL_DIR / "ppo_gas_agent.zip"

# Các file bắt buộc của SB3 PPO
REQUIRED = [
    "data",                    # JSON: hyperparams + env info
    "policy.pth",              # Actor-Critic neural network weights
    "policy.optimizer.pth",    # Adam optimizer state
    "pytorch_variables.pth",   # Misc PyTorch variables
    "_stable_baselines3_version",
    "system_info.txt",
]

missing = [f for f in REQUIRED if not (RL_DIR / f).exists()]
if missing:
    print(f"[ERROR] File thiếu: {missing}")
    raise SystemExit(1)

print(f"Đang đóng gói {len(REQUIRED)} files vào {OUT_ZIP} ...")
with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    for fname in REQUIRED:
        fpath = RL_DIR / fname
        zf.write(fpath, fname)   # arcname = chỉ tên file, không có folder prefix
        size_kb = fpath.stat().st_size / 1024
        print(f"  + {fname}  ({size_kb:.1f} KB)")

zip_size = OUT_ZIP.stat().st_size / 1024
print(f"\n✅ Tạo thành công: {OUT_ZIP}  ({zip_size:.1f} KB)")
