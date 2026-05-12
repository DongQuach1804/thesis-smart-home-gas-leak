"""
LSTM Forecaster — Colab training script (statistically robust evaluation).

Self-contained: just paste this into ONE Colab cell and run. No repo clone
needed. Output: gas_forecaster.keras + lstm_metrics.json + figures, all
downloadable at the end.

What this script does differently from the original:
1. Generates MULTIPLE INDEPENDENT TRACES (different seeds) instead of one.
2. Splits per-seed (chronological) so positive samples are well represented
   in both train and test.
3. Reports bootstrap 95% CI for Accuracy / Precision / Recall / F1.
4. Saves a clean sklearn-style normalized confusion matrix.

Recommended Colab config (free tier is enough):
    NUM_SEEDS = 5,  HOURS_PER_SEED = 24      # ~120 h total simulated data
                                             # ~150-200 independent leak events

Run time on Colab CPU: ~6-10 minutes total.
GPU not required (LSTM is tiny).
"""
# ============================================================================
#  CONFIGURATION  --  edit these
# ============================================================================
NUM_SEEDS       = 5          # number of independent simulation runs
HOURS_PER_SEED  = 24         # simulated hours per seed
EPOCHS          = 20
BATCH_SIZE      = 256
TEST_FRAC       = 0.20       # chronological tail of each seed -> test set
SEQ_LEN         = 60         # input window (seconds)
HORIZON         = 300        # forecasting horizon (seconds = 5 min)
CRITICAL_PPM    = 1000.0
LEAK_PROB_PER_MIN = 0.05     # simulator leak probability
BOOTSTRAP_ITERS = 2000       # for CI estimation
OUT_DIR         = "outputs"  # where to save artifacts

# ============================================================================
#  IMPORTS
# ============================================================================
import os, json, math, random, time
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import tensorflow as tf
print(f"TensorFlow {tf.__version__}  |  GPU: {bool(tf.config.list_physical_devices('GPU'))}")

os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================================
#  INLINED SIMULATOR  (matches device/simulator/sensor_simulator.py)
# ============================================================================
class State(str, Enum):
    NORMAL = "NORMAL"
    LEAK_SLOW = "LEAK_SLOW"
    LEAK_FAST = "LEAK_FAST"
    VENTILATING = "VENTILATING"


@dataclass
class World:
    gas: float = 60.0
    temp: float = 28.0
    hum: float = 60.0
    state: State = State.NORMAL
    state_age_s: float = 0.0


def _step_normal(w, dt):
    target = 60.0
    w.gas += (target - w.gas) * 0.1 * dt + random.gauss(0, 3) * dt
    w.gas = max(20.0, min(w.gas, 200.0))
    w.temp += random.gauss(0, 0.05)
    w.hum  += random.gauss(0, 0.1)


def _step_leak_slow(w, dt):
    w.gas += 5.0 * dt + random.gauss(0, 2) * dt
    w.gas = min(w.gas, 1500.0)
    w.hum += 0.02 * dt


def _step_leak_fast(w, dt):
    k = 0.04
    w.gas = w.gas * math.exp(k * dt) + 8.0 * dt + random.gauss(0, 3) * dt
    w.gas = min(w.gas, 2000.0)
    w.hum += 0.05 * dt


def _step_vent(w, dt):
    w.gas = max(60.0, w.gas * math.exp(-0.03 * dt) - 0.5 * dt)
    w.temp += random.gauss(0, 0.05)
    w.hum  -= 0.05 * dt


STEP_FN = {
    State.NORMAL: _step_normal,
    State.LEAK_SLOW: _step_leak_slow,
    State.LEAK_FAST: _step_leak_fast,
    State.VENTILATING: _step_vent,
}


def _maybe_transition(w, dt):
    p = LEAK_PROB_PER_MIN / 60.0 * dt
    if w.state == State.NORMAL:
        if random.random() < p:
            w.state = State.LEAK_SLOW if random.random() < 0.7 else State.LEAK_FAST
            w.state_age_s = 0.0
            return
    if w.state in (State.LEAK_SLOW, State.LEAK_FAST):
        if w.state_age_s > 180 and random.random() < 0.005:
            w.state = State.VENTILATING
            w.state_age_s = 0.0
            return
    if w.state == State.VENTILATING:
        if w.gas < 100 and w.state_age_s > 30:
            w.state = State.NORMAL
            w.state_age_s = 0.0


def simulate(hours: float, seed: int) -> np.ndarray:
    random.seed(seed)
    np.random.seed(seed)
    n = int(hours * 3600)
    out = np.zeros((n, 3), dtype=np.float32)  # gas, temp, hum
    w = World()
    for t in range(n):
        STEP_FN[w.state](w, 1.0)
        _maybe_transition(w, 1.0)
        w.state_age_s += 1.0
        out[t] = (w.gas, w.temp, w.hum)
    return out


# ============================================================================
#  DATASET BUILDER (per-trace, chronological split)
# ============================================================================
BOUNDS = np.array([2000.0, 60.0, 100.0], dtype=np.float32)


def make_xy(trace: np.ndarray):
    n = len(trace)
    last = n - HORIZON - 1
    if last <= SEQ_LEN:
        raise ValueError("Trace too short.")
    n_s = last - SEQ_LEN
    X = np.zeros((n_s, SEQ_LEN, 3), dtype=np.float32)
    y = np.zeros((n_s,), dtype=np.float32)
    feats = trace / BOUNDS
    gas = trace[:, 0]
    for i in range(n_s):
        end = SEQ_LEN + i
        X[i] = feats[i:end]
        y[i] = 1.0 if gas[end + 1: end + 1 + HORIZON].max() > CRITICAL_PPM else 0.0
    return X, y


def count_leak_events(trace: np.ndarray) -> int:
    """Count independent leak events (gas crossing CRITICAL from below)."""
    gas = trace[:, 0]
    above = gas > CRITICAL_PPM
    # transitions False -> True
    return int(np.sum((~above[:-1]) & above[1:]))


print(f"\n[1/4] Generating {NUM_SEEDS} seeds x {HOURS_PER_SEED} h "
      f"= {NUM_SEEDS * HOURS_PER_SEED} h total...")
seeds = [42 + i for i in range(NUM_SEEDS)]
Xtr_list, ytr_list, Xte_list, yte_list = [], [], [], []
total_events = 0
for s in seeds:
    t0 = time.time()
    trace = simulate(HOURS_PER_SEED, seed=s)
    X, y = make_xy(trace)
    split = int(len(X) * (1 - TEST_FRAC))
    Xtr_list.append(X[:split]);  ytr_list.append(y[:split])
    Xte_list.append(X[split:]);  yte_list.append(y[split:])
    events = count_leak_events(trace)
    total_events += events
    print(f"  seed={s}: trace={trace.shape}, X={X.shape}, "
          f"pos={y.mean():.2%}, leak_events={events}, "
          f"sim_time={time.time()-t0:.1f}s")

Xtr = np.concatenate(Xtr_list); ytr = np.concatenate(ytr_list)
Xte = np.concatenate(Xte_list); yte = np.concatenate(yte_list)
pos_train = float(ytr.mean())
print(f"\nTRAIN: X={Xtr.shape}  pos={pos_train:.2%}")
print(f"TEST : X={Xte.shape}  pos={yte.mean():.2%}")
print(f"Total independent leak events across all seeds: {total_events}")

# ============================================================================
#  MODEL
# ============================================================================
def build_model():
    inp = tf.keras.layers.Input(shape=(SEQ_LEN, 3))
    x = tf.keras.layers.LSTM(32)(inp)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    m = tf.keras.Model(inp, out)
    m.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy",
                 tf.keras.metrics.Precision(name="precision"),
                 tf.keras.metrics.Recall(name="recall")],
    )
    return m


print("\n[2/4] Training model...")
tf.random.set_seed(42)
model = build_model()
model.summary()

class_w = {0: 1.0, 1: max(1.0, (1 - pos_train) / max(pos_train, 1e-3))}
print(f"class_weight = {class_w}")

history = model.fit(
    Xtr, ytr,
    validation_data=(Xte, yte),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    class_weight=class_w,
    verbose=2,
)

# ============================================================================
#  EVALUATION + BOOTSTRAP CI
# ============================================================================
print("\n[3/4] Evaluating on test set with bootstrap CI...")
y_prob = model.predict(Xte, batch_size=BATCH_SIZE, verbose=0).ravel()
y_pred = (y_prob >= 0.5).astype(np.int32)
y_true = yte.astype(np.int32)

def metrics_from_arrays(yt, yp):
    tp = int(((yt == 1) & (yp == 1)).sum())
    fp = int(((yt == 0) & (yp == 1)).sum())
    tn = int(((yt == 0) & (yp == 0)).sum())
    fn = int(((yt == 1) & (yp == 0)).sum())
    acc = (tp + tn) / max(1, tp + fp + tn + fn)
    prec = tp / max(1, tp + fp)
    rec  = tp / max(1, tp + fn)
    f1   = 2 * prec * rec / max(1e-9, prec + rec)
    return dict(tp=tp, fp=fp, tn=tn, fn=fn,
                accuracy=acc, precision=prec, recall=rec, f1=f1)


point = metrics_from_arrays(y_true, y_pred)
print("\nPoint estimates:")
for k in ("accuracy", "precision", "recall", "f1"):
    print(f"  {k:10s} = {point[k]*100:.2f}%")
print(f"  TP={point['tp']}  FP={point['fp']}  "
      f"TN={point['tn']}  FN={point['fn']}")

print(f"\nBootstrap CI (95%) over {BOOTSTRAP_ITERS} resamples...")
rng = np.random.default_rng(0)
n_te = len(y_true)
boot = {k: [] for k in ("accuracy", "precision", "recall", "f1")}
for _ in range(BOOTSTRAP_ITERS):
    idx = rng.integers(0, n_te, size=n_te)
    bm = metrics_from_arrays(y_true[idx], y_pred[idx])
    for k in boot:
        boot[k].append(bm[k])

ci = {}
for k, arr in boot.items():
    arr = np.array(arr)
    lo, hi = np.percentile(arr, [2.5, 97.5])
    ci[k] = (float(lo), float(hi))
    print(f"  {k:10s}: {point[k]*100:.2f}%   95% CI = "
          f"[{lo*100:.2f}%, {hi*100:.2f}%]")

# ============================================================================
#  SAVE ARTIFACTS
# ============================================================================
print("\n[4/4] Saving artifacts...")

# Model
model_path = Path(OUT_DIR) / "gas_forecaster.keras"
model.save(model_path)
print(f"  model       -> {model_path}")

# Metrics JSON
metrics_out = {
    "config": dict(num_seeds=NUM_SEEDS, hours_per_seed=HOURS_PER_SEED,
                   epochs=EPOCHS, batch_size=BATCH_SIZE,
                   seq_len=SEQ_LEN, horizon=HORIZON,
                   leak_prob_per_min=LEAK_PROB_PER_MIN,
                   total_leak_events=total_events,
                   n_train=int(len(Xtr)), n_test=int(len(Xte))),
    **point,
    "ci_95": {k: list(v) for k, v in ci.items()},
}
metrics_path = Path(OUT_DIR) / "lstm_metrics.json"
metrics_path.write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")
print(f"  metrics     -> {metrics_path}")

# Training curves
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
h = history.history
ax1.plot(h["loss"], label="train"); ax1.plot(h["val_loss"], label="val")
ax1.set_title("Loss"); ax1.set_xlabel("epoch"); ax1.legend(); ax1.grid(alpha=.3)
ax2.plot(h["accuracy"], label="train"); ax2.plot(h["val_accuracy"], label="val")
ax2.set_title("Accuracy"); ax2.set_xlabel("epoch"); ax2.legend(); ax2.grid(alpha=.3)
fig.tight_layout()
fig.savefig(Path(OUT_DIR) / "lstm_training.png", dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"  training    -> {OUT_DIR}/lstm_training.png")

# Confusion matrix (sklearn-style, normalized)
cm = np.array([[point["tn"], point["fp"]],
               [point["fn"], point["tp"]]], dtype=float)
cm_norm = cm / cm.sum(axis=1, keepdims=True)

fig, ax = plt.subplots(figsize=(6.2, 5.2))
im = ax.imshow(cm_norm, cmap="Blues", vmin=0.0, vmax=1.0, aspect="equal")
for i in range(2):
    for j in range(2):
        v = cm_norm[i, j]
        c = "white" if v > 0.55 else "#1f2d3d"
        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                fontsize=20, weight="bold", color=c)
ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
ax.set_xticklabels(["0", "1"]); ax.set_yticklabels(["0", "1"])
ax.set_xlabel("Predicted label"); ax.set_ylabel("True label")
ax.set_title("Normalized confusion matrix")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
fig.tight_layout()
fig.savefig(Path(OUT_DIR) / "lstm_confusion_matrix.png", dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"  confusion   -> {OUT_DIR}/lstm_confusion_matrix.png")

# ============================================================================
#  COLAB DOWNLOAD HELPER  (uncomment in Colab)
# ============================================================================
# from google.colab import files
# import shutil
# shutil.make_archive("outputs", "zip", OUT_DIR)
# files.download("outputs.zip")

print("\nDONE.\n"
      f"  - Trained on {len(Xtr):,} samples ({total_events} independent leak events).\n"
      f"  - Test set: {len(Xte):,} samples.\n"
      f"  - Model + metrics + figures saved to ./{OUT_DIR}/\n"
      f"  - Uncomment the last 4 lines to download as zip from Colab.")
