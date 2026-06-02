# Hình cho slide — phiên bản mới nhất (v3)

Sinh bằng: `python make_slide_figures.py` (đọc số liệu thật trong `thesis-latex/img/exp/`).
Chạy lại bất cứ lúc nào sau khi train lại — hình tự cập nhật theo số liệu mới.

## Ánh xạ hình → slide (thay hình cũ)

| File hình | Dùng cho slide | Thay cho hình cũ nào |
|---|---|---|
| `01_lstm_architecture.png` | LSTM Model | Slide 1 (vẽ SAI: có LSTM64+BatchNorm). Bản đúng: Input(60,3)→LSTM(32)→Dropout→Dense(16)→Dense(1) |
| `02_rl_loop.png` | Reinforcement Learning | Slide 2 (đang TRỐNG "picture can't be displayed") |
| `03_ppo_actor_critic.png` | RL — PPO | Slide 7/8 (sơ đồ actor) |
| `04_ppo_input_output.png` | RL — Input/Output PPO | Slide 9 |
| `05_reward.png` | RL — Reward | Slide 10 (cập nhật công thức v3: bỏ +10, thêm +0.3/holding cost) |
| `06_lstm_training.png` | Kết quả LSTM | Slide 12 (thay đồ thị MSE/MAE của thí nghiệm UCI cũ) |
| `07_lstm_confusion_matrix.png` | Kết quả LSTM (simulator) | (mới) |
| `08_lstm_training_kaggle.png` | Kết quả LSTM (dữ liệu thật) | (mới) |
| `09_lstm_confusion_matrix_kaggle.png` | Kết quả LSTM (Kaggle) | (mới) |
| `10_ppo_reward.png` | Kết quả PPO | Slide 16 (thay "Total Reward 33,670" CO-based cũ) |
| `11_benchmark_chart.png` | Đánh giá so sánh | (mới — RL vượt cả 4) |
| `12_scenarios_chart.png` | Đánh giá theo kịch bản | (mới) |
| `13_system_architecture.png` | Kiến trúc hệ thống | (nếu cần) |

## LƯU Ý quan trọng về slide cũ
Các slide 11–17 bạn gửi là một **thí nghiệm KHÁC** (UCI Gas Sensor, dự báo nồng độ CO bằng
hồi quy R²=0.90/MAE, action CO-based 0-Normal/1-Warning/2-Evacuate, 200k steps).
Thí nghiệm đó **không khớp** với dự án hiện tại (dự báo nhị phân P(critical 5 phút) trên
simulator + Kaggle env-sensor, action NO_OP/ALERT/FAN/VALVE, 400k steps, reward v3).
→ Nên thay toàn bộ slide kết quả bằng hình trong thư mục này để nhất quán với khóa luận.
