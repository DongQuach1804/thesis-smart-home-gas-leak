"""
LSTM Forecaster — Colab training script on REAL Kaggle data.

Dataset: garystafford/environmental-sensor-data-132k
URL:     https://www.kaggle.com/datasets/garystafford/environmental-sensor-data-132k
Columns: ts, device, co, humidity, light, lpg, motion, smoke, temp
         (~405k rows across 3 devices, ~7 days, ~1 sample / 1-3 s)

We treat this as a real-world "background" gas trace and reproduce the same
binary forecasting task as the simulator pipeline:

    y[i] = 1  iff  max(lpg[t+1 .. t+H]) > LPG_THRESHOLD
    X[i] = 60-step window of (lpg, temp, humidity)   ← scaled to [0, 1]

Since the dataset contains household monitoring (no labelled leak events),
LPG_THRESHOLD is chosen as the empirical 95th percentile of `lpg` so that
"high-future-lpg" episodes act as our positive class. Confirm the chosen
threshold by inspecting the printed percentile table at runtime.

HOW TO RUN ON GOOGLE COLAB
==========================
1. Upload your Kaggle API token (kaggle.json) — from kaggle.com → Account →
   "Create new API Token". The notebook will prompt you to upload it.
2. Paste this entire script into ONE Colab cell and run.
3. Run time: ~5-8 minutes on free CPU.
4. Uncomment the final block to download outputs.zip.
"""
# ============================================================================
#  CONFIGURATION
# ============================================================================
SEQ_LEN          = 60          # input window (timesteps)
HORIZON          = 300         # forecasting horizon (timesteps)
TEST_FRAC        = 0.20        # chronological tail of each device
EPOCHS           = 25
BATCH_SIZE       = 256
LPG_PCT_THRESH   = 95          # percentile used as "danger" threshold
BOOTSTRAP_ITERS  = 2000
OUT_DIR          = "outputs"

# Kaggle dataset
KAGGLE_SLUG      = "garystafford/environmental-sensor-data-132k"
CSV_FILENAME     = "iot_telemetry_data.csv"

# Kaggle credentials — fill EITHER (A) or (B) below:
# (A) Paste username + key here directly (easiest):
KAGGLE_USERNAME  = ""   # e.g. "leduong22520300"
KAGGLE_KEY       = ""   # e.g. "KGAT_4cd860405ab3b01bee9199bf3a78e71a"
# (B) ...OR leave both empty and upload kaggle.json when prompted.

# ============================================================================
#  SETUP — Kaggle credentials + download
# ============================================================================
import os, json, time, math, io
from pathlib import Path

os.makedirs(OUT_DIR, exist_ok=True)

print("=== STEP 1: Kaggle credentials ===")
if KAGGLE_USERNAME and KAGGLE_KEY:
    # Option A: use the username + key pasted above
    os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
    os.environ["KAGGLE_KEY"] = KAGGLE_KEY
    print(f"Using inline credentials for user '{KAGGLE_USERNAME}'.")
elif not (Path("/root/.kaggle/kaggle.json").exists() or Path(".kaggle/kaggle.json").exists()):
    # Option B: prompt for kaggle.json upload
    print("No inline credentials. Please upload kaggle.json (Kaggle -> Settings -> API -> Create New Token):")
    try:
        from google.colab import files  # type: ignore
        uploaded = files.upload()
        os.makedirs("/root/.kaggle", exist_ok=True)
        for fname in uploaded:
            with open(f"/root/.kaggle/{fname}", "wb") as f:
                f.write(uploaded[fname])
        os.chmod("/root/.kaggle/kaggle.json", 0o600)
        print("kaggle.json uploaded.")
    except ImportError:
        raise SystemExit("Not running in Colab — set KAGGLE_USERNAME+KAGGLE_KEY above, "
                         "or place kaggle.json at ~/.kaggle/kaggle.json")

print("\n=== STEP 2: Install + download dataset ===")
os.system("pip -q install kaggle pandas scikit-learn")
os.system(f"kaggle datasets download -d {KAGGLE_SLUG} -p data --unzip")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tensorflow as tf

print(f"\nTensorFlow {tf.__version__} | GPU: {bool(tf.config.list_physical_devices('GPU'))}")

# ============================================================================
#  LOAD + INSPECT DATA
# ============================================================================
print("\n=== STEP 3: Load CSV ===")
csv_path = Path("data") / CSV_FILENAME
if not csv_path.exists():
    # try locate any csv inside data/
    csvs = list(Path("data").glob("*.csv"))
    if not csvs:
        raise SystemExit("No CSV found under data/. Download failed?")
    csv_path = csvs[0]
print(f"Reading {csv_path}...")
df = pd.read_csv(csv_path)
print(f"Loaded {len(df):,} rows, columns = {list(df.columns)}")
print(f"Devices: {df['device'].unique() if 'device' in df.columns else 'no device col'}")
print(f"\nFirst rows:\n{df.head()}")
print(f"\nStats:\n{df[['lpg','co','smoke','temp','humidity']].describe()}")

# Sort by device + timestamp
df = df.sort_values(["device", "ts"]).reset_index(drop=True)

# ============================================================================
#  CHOOSE THRESHOLD + LABELLING
# ============================================================================
print("\n=== STEP 4: Choose LPG danger threshold ===")
pcts = [50, 75, 90, 95, 97, 99, 99.5]
for p in pcts:
    print(f"  lpg p{p:5.1f} = {np.percentile(df['lpg'], p):.6f}")
LPG_THRESHOLD = float(np.percentile(df["lpg"], LPG_PCT_THRESH))
print(f"\n→ Using percentile {LPG_PCT_THRESH} = {LPG_THRESHOLD:.6f} as 'danger' level.")

# ============================================================================
#  PER-DEVICE WINDOW BUILDER (avoids mixing devices in one window)
# ============================================================================
print("\n=== STEP 5: Build sliding windows per device ===")
FEAT_COLS = ["lpg", "temp", "humidity"]

# Scale each feature to [0, 1] using observed bounds (per dataset)
mins = df[FEAT_COLS].min().values.astype(np.float32)
maxs = df[FEAT_COLS].max().values.astype(np.float32)
print(f"feature mins = {mins}")
print(f"feature maxs = {maxs}")
spans = np.maximum(maxs - mins, 1e-6)


def make_xy_for_device(d: pd.DataFrame):
    n = len(d)
    last = n - HORIZON - 1
    if last <= SEQ_LEN:
        return None, None
    feats = (d[FEAT_COLS].values.astype(np.float32) - mins) / spans
    lpg = d["lpg"].values.astype(np.float32)
    n_s = last - SEQ_LEN
    X = np.zeros((n_s, SEQ_LEN, 3), dtype=np.float32)
    y = np.zeros((n_s,), dtype=np.float32)
    for i in range(n_s):
        end = SEQ_LEN + i
        X[i] = feats[i:end]
        y[i] = 1.0 if lpg[end + 1: end + 1 + HORIZON].max() > LPG_THRESHOLD else 0.0
    return X, y


Xtr_list, ytr_list, Xte_list, yte_list = [], [], [], []
for dev, g in df.groupby("device"):
    X, y = make_xy_for_device(g)
    if X is None:
        print(f"  device={dev}: trace too short, skipping")
        continue
    split = int(len(X) * (1 - TEST_FRAC))
    Xtr_list.append(X[:split]); ytr_list.append(y[:split])
    Xte_list.append(X[split:]); yte_list.append(y[split:])
    print(f"  device={dev}: X={X.shape}, pos={y.mean():.2%}, "
          f"train={split}, test={len(X)-split}")

Xtr = np.concatenate(Xtr_list); ytr = np.concatenate(ytr_list)
Xte = np.concatenate(Xte_list); yte = np.concatenate(yte_list)
pos_train = float(ytr.mean())
print(f"\nTRAIN: X={Xtr.shape}  pos={pos_train:.2%}")
print(f"TEST : X={Xte.shape}  pos={yte.mean():.2%}")

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


print("\n=== STEP 6: Train model ===")
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
print("\n=== STEP 7: Evaluate + bootstrap CI ===")
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

print(f"\n95% Bootstrap CI ({BOOTSTRAP_ITERS} resamples)...")
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
#  SAVE
# ============================================================================
print("\n=== STEP 8: Save artifacts ===")
model_path = Path(OUT_DIR) / "gas_forecaster_kaggle.keras"
model.save(model_path)
print(f"  model      -> {model_path}")

metrics_out = {
    "config": dict(
        dataset=KAGGLE_SLUG, csv=CSV_FILENAME,
        seq_len=SEQ_LEN, horizon=HORIZON,
        epochs=EPOCHS, batch_size=BATCH_SIZE,
        lpg_pct_thresh=LPG_PCT_THRESH,
        lpg_threshold_value=LPG_THRESHOLD,
        feature_mins=mins.tolist(), feature_maxs=maxs.tolist(),
        n_train=int(len(Xtr)), n_test=int(len(Xte)),
        pos_frac_train=pos_train, pos_frac_test=float(yte.mean()),
    ),
    **point,
    "ci_95": {k: list(v) for k, v in ci.items()},
}
metrics_path = Path(OUT_DIR) / "lstm_metrics_kaggle.json"
metrics_path.write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")
print(f"  metrics    -> {metrics_path}")

# Training curves
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
h = history.history
a1.plot(h["loss"], label="train"); a1.plot(h["val_loss"], label="val")
a1.set_title("Loss (Kaggle real data)"); a1.set_xlabel("epoch"); a1.legend(); a1.grid(alpha=.3)
a2.plot(h["accuracy"], label="train"); a2.plot(h["val_accuracy"], label="val")
a2.set_title("Accuracy"); a2.set_xlabel("epoch"); a2.legend(); a2.grid(alpha=.3)
fig.tight_layout()
fig.savefig(Path(OUT_DIR) / "lstm_training_kaggle.png", dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"  curves     -> {OUT_DIR}/lstm_training_kaggle.png")

# Confusion matrix (sklearn-style)
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
ax.set_title("Normalized confusion matrix\n(Kaggle environmental-sensor-data-132k)")
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
fig.tight_layout()
fig.savefig(Path(OUT_DIR) / "lstm_confusion_matrix_kaggle.png", dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"  confusion  -> {OUT_DIR}/lstm_confusion_matrix_kaggle.png")

print("\nDONE.")
print(f"  Trained on {len(Xtr):,} windows from real Kaggle telemetry.")
print(f"  Test set : {len(Xte):,} windows.")
print(f"  All artifacts in ./{OUT_DIR}/\n")

# ============================================================================
#  COLAB DOWNLOAD HELPER — zip outputs and trigger download
# ============================================================================
try:
    from google.colab import files  # type: ignore
    import shutil
    shutil.make_archive("outputs", "zip", OUT_DIR)
    print("Zipped outputs.zip — triggering download...")
    files.download("outputs.zip")
except ImportError:
    print("Not running in Colab — skipping download step.")
