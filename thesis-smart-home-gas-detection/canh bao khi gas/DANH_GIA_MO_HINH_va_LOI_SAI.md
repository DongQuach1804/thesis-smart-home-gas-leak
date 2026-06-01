# Đánh giá mô hình & các lỗi sai của đề tài
**Đề tài:** Hệ thống phát hiện rò rỉ khí gas thông minh tích hợp IoT, dự báo LSTM và học tăng cường PPO
**Ngày đánh giá:** 01/06/2026

---

## 1. Kết luận nhanh (TL;DR)

| Thành phần | Dùng được? | Nhận định |
|---|---|---|
| **Kiến trúc hệ thống (IoT 4 lớp, MQTT–Kafka–Spark–DB, Telegram)** | ✅ Tốt | Thiết kế chỉn chu, đúng chuẩn, đủ sức bảo vệ. |
| **LSTM Forecaster** | ✅ Dùng được | Đúng hướng khoa học, có kiểm chứng trên **dữ liệu thực Kaggle**. Chỉ cần giữ/huấn luyện lại bình thường. |
| **PPO RL Controller** | ⚠️ **Chưa dùng được như đang trình bày** | Environment có **lỗi reward-hacking**; benchmark có **artifact** làm số liệu RL không đáng tin; **thiếu so sánh PPO vs luật tay** nên chưa chứng minh được "đóng góp khoa học". → **Cần sửa env + train lại** (đã có notebook). |

**Tổng thể:** Đề tài *không sai về hướng đi*, nhưng phần RL đang được "kể" mạnh hơn số liệu cho phép. Hội đồng nhiều khả năng sẽ "soi" đúng chỗ này. Notebook đính kèm sửa các lỗi và sinh lại số liệu phòng thủ được.

---

## 2. Về đề tài có vấn đề gì không?

Hướng đi (dự báo sớm bằng LSTM + tự động ứng phó bằng RL) là **hợp lý và được tài liệu khoa học ủng hộ**:
- LSTM/CNN-LSTM/physics-informed-LSTM cho phát hiện & dự báo rò rỉ khí là hướng phổ biến, hiệu quả.
- Tuy nhiên RL cho điều khiển van/quạt trong nhà ở **ít tiền lệ** → đây vừa là điểm mới, vừa là điểm dễ bị chất vấn. Phải chứng minh RL **hơn được luật tay đơn giản**, nếu không reviewer sẽ hỏi: "5 dòng if-else cũng làm được điều này, RL thêm giá trị gì?"

Một điểm cần làm rõ trong bảo vệ: dữ liệu RL **hoàn toàn từ simulator**. Đây là giới hạn lớn nhất (sim-to-real gap). Chương 4 đã thừa nhận — tốt — nhưng cần nhấn mạnh đây là "proof-of-concept", không tuyên bố quá mức.

---

## 3. Các lỗi sai cụ thể (đã kiểm chứng bằng code)

### Lỗi 1 — Reward hacking trong `gas_env.py` (NGHIÊM TRỌNG)
Dòng thưởng `+10` nằm **ngoài** guard `if not self.fan_on`:
```python
if action in (2, 3) and leak_state in (State.LEAK_SLOW, State.LEAK_FAST):
    reward += 10.0     # trao MỖI bước, không chỉ khi thực sự kích hoạt
```
→ Agent có thể **"farm" +10 mỗi giây** chỉ bằng cách chọn `FAN_ON` liên tục trong lúc rò rỉ.
**Kiểm chứng (đã chạy):** chính sách "spam FAN_ON mỗi bước" được env CŨ thưởng dư **+10.106** so với NO_OP; env ĐÃ SỬA chỉ còn **+4.361** (đúng phần lợi ích mitigation hợp lệ). Khoản chênh ~5.700 là phần thưởng lậu.

### Lỗi 2 — Van/quạt latch vĩnh viễn, không có chi phí giữ
`valve_closed`/`fan_on` một khi bật là **giữ nguyên cả episode**, không có penalty. Hệ quả: chính sách "đóng van/bật quạt rồi để đó" bị méo; agent không học hành vi đa cấp thực sự. → Đã thêm **holding cost** + **auto-reset khi phòng an toàn** trong env mới.

### Lỗi 3 — Benchmark đo `lead_time` và `miss` SAI cho RL (artifact, không phải kết quả thật)
Phương pháp "two-pass oracle" trong `benchmark.py` **chỉ hợp lệ cho controller không làm đổi quỹ đạo world** (threshold, forecaster chỉ cảnh báo). RL có hành động FAN/VALVE → **đổi quỹ đạo** → số leak khác hẳn (RL thấy 15 leak vs 8 của oracle) → **`leak_id` lệch giữa 2 pass** → các con số sau là **artifact**:
- `lead_time = 1.803 s` (≈ cả episode 1800 s — vô lý về vật lý, leak chậm chạm critical chỉ ~188 s).
- `miss_rate = 15%` — *cao hơn cả threshold 0%*, **mâu thuẫn trực tiếp** với khẳng định ở README/Chương 1 rằng "RL vượt threshold về miss rate".

Chương 4 đã thừa nhận miss 15% là artifact — nhưng vẫn **trình bày lead_time 1803 s và peak_gas 63 ppm như "đóng góp khoa học cốt lõi"**, trong khi:
- `peak_gas 63 ppm` đạt được **chỉ bằng việc đóng van sớm** — điều mà **luật tay cũng làm được**.
- Không có thí nghiệm nào so **PPO đã học vs luật tay** → chưa có bằng chứng PPO học được gì hơn.

### Lỗi 4 — Reward không hội tụ về dương, kẹt vùng âm `[-2000, -1800]`
Hệ số `-50`/bước-critical lấn át, đường cong khó diễn giải. Chương 4 đã nêu. → Đã sửa bằng `VecNormalize(norm_reward=True)` trong notebook.

### Lỗi 5 (nhỏ) — Docstring lệch code
Docstring đầu `gas_env.py` ghi reward `-2 / -5`, nhưng code thực và LaTeX dùng `-3 / -15 / -25`. Cần đồng bộ để tránh nhầm lẫn khi bảo vệ.

---

## 4. Việc cần làm (quy trình)

1. **Chạy notebook** `train_gas_models_colab_v2.ipynb` trên Google Colab (Run all).
2. Notebook xuất `artifacts_gas_v2.zip` gồm: `gas_forecaster.keras`, `ppo_gas_agent.zip`, các file `*_metrics.json`, `*_results.json`, biểu đồ `*.png`, và **bảng so sánh 4 controller (threshold / forecaster / rule / rl)**.
3. **Gửi lại file zip vào Cowork.**
4. Tôi sẽ: đặt model vào `processing/ml/`, **viết lại Chương 4** cho khớp số liệu mới, và **điều chỉnh câu chữ ở Chương 1/3** để các khẳng định về RL khớp với bằng chứng (đặc biệt là kết quả PPO-vs-rule).

---

## 5. Gợi ý phòng thủ trước hội đồng
- Nếu PPO **không** hơn luật tay rõ rệt: trình bày trung thực là "RL đạt ngang luật tay nhưng học tự động từ reward, không cần tinh chỉnh ngưỡng thủ công" — vẫn là đóng góp hợp lệ, và **khiêm tốn hóa** từ "đóng góp khoa học cốt lõi" xuống "proof-of-concept cho hướng tự động ứng phó".
- Luôn kèm **error bar nhiều seed** (≥5–10 seed) cho mọi số liệu RL.
- Nhấn mạnh LSTM đã kiểm chứng trên **dữ liệu thực** (đây là điểm mạnh nhất, định lượng tốt).
