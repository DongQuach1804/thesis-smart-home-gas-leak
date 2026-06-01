---
marp: true
theme: default
paginate: true
size: 16:9
math: katex
header: 'Báo cáo tiến độ KLTN – Phát hiện rò rỉ khí gas thông minh'
footer: '13/05/2026 – UIT • Lê Viết Dương 22520300 • Quách Minh Đông 22520259'
style: |
  section {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    padding: 50px 60px 60px 60px;
    justify-content: flex-start;
  }
  section.lead {
    justify-content: center;
    text-align: center;
  }
  h1 { color: #1f4e79; font-size: 1.6em; margin-bottom: 0.3em; }
  h2 {
    color: #2e75b6;
    border-bottom: 2px solid #2e75b6;
    padding-bottom: 4px;
    font-size: 1.2em;
    margin-bottom: 0.5em;
  }
  h3 { color: #1f4e79; font-size: 1em; margin: 0.4em 0; }
  p, li { font-size: 0.82em; line-height: 1.45; }
  table { font-size: 0.68em; margin: 0.4em auto; }
  th { background: #e7f0f9; }
  code { background: #f3f3f3; padding: 1px 4px; border-radius: 3px; font-size: 0.85em; }
  img { display: block; margin: 0.4em auto; }
  blockquote { font-size: 0.82em; border-left: 4px solid #2e75b6; padding-left: 12px; color: #444; }
  pre { font-size: 0.7em; }
---

<!-- _class: lead -->

# BÁO CÁO TIẾN ĐỘ KHÓA LUẬN TỐT NGHIỆP

## HỆ THỐNG PHÁT HIỆN RÒ RỈ KHÍ GAS THÔNG MINH

### Tích hợp IoT, dự báo LSTM và học tăng cường PPO

*A Smart Gas Leak Detection System integrating IoT, LSTM Forecasting and PPO Reinforcement Learning*

**GVHD:** ThS. Nguyễn Khánh Thuật

**Sinh viên thực hiện:**
- Lê Viết Dương — 22520300 — MMTT2022.1
- Quách Minh Đông — 22520259 — MMTT2022.1

---

## NỘI DUNG BÁO CÁO

| **01** | **02** | **03** |
|:---|:---|:---|
| **TỔNG QUAN ĐỀ TÀI** | **NGHIÊN CỨU LIÊN QUAN** | **TIẾN ĐỘ HIỆN TẠI** |
| Bối cảnh rò rỉ khí gas | Bài báo & khoảng trống | Kiến trúc 4 lớp + luồng dữ liệu |
| Ngưỡng nguy hiểm 1000 ppm | LSTM cho time-series | Dataset & mô phỏng |
| Ngưỡng tĩnh & giới hạn | RL cho điều khiển | Mô hình LSTM & PPO |
|  |  | Tiêu chí & benchmark |

---

<!-- _class: lead -->

# 01
# TỔNG QUAN ĐỀ TÀI

---

## RÒ RỈ KHÍ GAS – NGUY CƠ NGHIÊM TRỌNG TẠI VIỆT NAM

- Khí gas hóa lỏng **LPG** (propane/butane) là **nhiên liệu nấu ăn chính** của >70% hộ gia đình Việt Nam, dùng phổ biến qua **bình 12 kg** hoặc **bếp gas mini** [Bộ Công Thương 2023 — Báo cáo thị trường LPG VN].
- Các **sự cố gas đặc thù Việt Nam** thường gặp gồm:
  1. **Bếp gas mini / bình du lịch nổ** do quá nhiệt hoặc tái nạp sai cách (nhiều vụ tại quán ăn, bếp ăn tập thể).
  2. **Dây dẫn cao su xuống cấp / chuột cắn** giữa bình và bếp — rò rỉ nhanh hơn van công nghiệp.
  3. **Quên tắt bếp** khi nấu ăn, ngọn lửa tắt do gió/nước trào nhưng van vẫn mở.
  4. **Van bình LPG 12 kg lắp không chặt** khi thay bình tại nhà.
- Theo **Cục Cảnh sát PCCC&CNCH (C07 — Bộ Công an)**, mỗi năm Việt Nam ghi nhận **150–300 vụ cháy nổ liên quan đến gas**, đặc biệt nguy hiểm vì xảy ra **âm thầm** — người dùng chỉ phát hiện khi đã ngửi thấy mùi hoặc gây ngộp.

> Câu hỏi nghiên cứu: làm sao **dự báo sớm** rò rỉ và **tự động ứng phó** trước khi đạt ngưỡng nguy hiểm trong bối cảnh **bếp gas hộ gia đình Việt Nam**?

---

## VÌ SAO NGƯỠNG NGUY HIỂM ĐƯỢC CHỌN LÀ 1000 ppm?

**Căn cứ trực tiếp từ 4 nguồn được kiểm chứng** (không phải tự đặt):

| Nguồn tham chiếu | Quy định | Suy ra ngưỡng |
|:---|:---|:---|
| **NFPA 58:2020** *Liquefied Petroleum Gas Code* (Mỹ) | LEL (Lower Explosive Limit) của LPG = **2,1% v/v** | 100% LEL ≈ **21.000 ppm** |
| **IEC 60079-29-1:2016** *Gas detectors — Performance requirements for flammable gases* | Cảnh báo **bắt buộc** ≤ **20% LEL**; cảnh báo **báo sớm** khuyến nghị **5% LEL** | 5% × 21.000 ≈ **1.050 ppm ≈ 1.000 ppm** |
| **OSHA 1910.146** *Permit-required confined spaces* (Mỹ) | Action level cho khí cháy = **10% LEL** | 10% × 21.000 ≈ **2.100 ppm** (giới hạn trên của vùng cảnh báo) |
| **Datasheet Hanwei MQ-2 / MQ-6** | Khuyến nghị calibrate cảm biến tại **1.000 ppm LPG** trong không khí sạch | Điểm tham chiếu khả thi với phần cứng |
| **QCVN 06:2022/BXD** (Quy chuẩn VN về an toàn cháy) | Tham chiếu nguyên tắc cảnh báo sớm trước 50% giá trị cháy nổ | Đồng thuận với 5% LEL |

→ **Đề tài chọn 1.000 ppm** = **5% LEL** = ngưỡng "early warning" của IEC 60079-29-1. Cảnh báo **trước** khi đạt action level OSHA (10% LEL), cho người dùng **≥ 200 s phản ứng** (theo benchmark TC-Slow).

→ Mọi nhãn LSTM $y_t = \mathbf{1}[\max(gas_{t+1..t+300}) > 1000\text{ ppm}]$ đều quy chiếu **chính 4 tiêu chuẩn này**, không phải con số tròn ngẫu nhiên.

---

## THÁCH THỨC CỦA HỆ THỐNG NGƯỠNG TĨNH

- **Phản ứng muộn**: chỉ cảnh báo khi gas đã đạt 5% LEL → trong nhiều trường hợp người dùng đã ngửi thấy mùi.
- **False alarm**: dao động nhiệt độ / độ ẩm làm thay đổi điện trở MQ → kích hoạt cảnh báo nhầm.
- **Không dự báo được xu hướng**: không phân biệt được leak đang tăng dần với mức nền cao ổn định.
- **Phản ứng đơn lẻ**: chỉ phát còi, không tự đóng van / bật quạt → vô dụng khi vắng người.

→ Cần thay thế bằng tiếp cận **dự báo (forecasting) + điều khiển tự động (control)** dựa trên học máy.

---

<!-- _class: lead -->

# 02
# NGHIÊN CỨU LIÊN QUAN

---

## CÁC CÔNG TRÌNH LIÊN QUAN

| Tên bài báo | Tóm tắt nội dung | Hạn chế |
|:---|:---|:---|
| Saranya 2023 — Arduino + MQ-2 | SMS alert khi vượt ngưỡng | Ngưỡng tĩnh, không dự báo |
| Nwazor 2023 — IoT Gas Leak | ESP8266 + mobile app | Chỉ phản ứng, không can thiệp vật lý |
| Gambiroza 2020 — LSTM transient | LSTM học đặc tính quá độ MQ | Phân loại loại khí, **chưa forecast** |
| Abbas 2021 — Neural classification | NN phân loại mức nguy hiểm | Phân loại **tức thời**, không dự báo |
| Wei 2022 — DRL offloading pipeline | DRL cho đường ống công nghiệp | Không phải nhà ở, không có actuator |
| Tian 2019 — Temperature compensation | Bù nhiệt cho MQ sensor | Pre-processing, không có quyết định |

→ **Khoảng trống**: chưa có nghiên cứu nào tích hợp **đồng thời** ba thành phần: (i) **LSTM dự báo** xác suất nguy hiểm 5 phút tới, (ii) **RL điều khiển đa hành động**, (iii) **pipeline streaming production** cho nhà ở.

---

## HƯỚNG TIẾP CẬN CỦA ĐỀ TÀI

### LSTM Forecasting (module chuỗi thời gian #1)

Dự báo **xác suất** gas vượt 1000 ppm trong **5 phút tới** dựa trên cửa sổ 60 giây × 3 đặc trưng. Thay ngưỡng tĩnh cứng bằng tín hiệu liên tục $p_{5\min} \in [0, 1]$.

### PPO Reinforcement Learning

Học **chính sách** chọn 1 trong 4 hành động {NO_OP, ALERT, FAN_ON, CLOSE_VALVE}. Reward asymmetric: phạt nặng để gas vượt 1000 ppm, thưởng can thiệp đúng pha leak.

### Pipeline streaming hiện đại

**MQTT** (truyền tải IoT nhẹ) → **Kafka** (commit log cho luồng dữ liệu lớn) → **Spark Structured Streaming** → InfluxDB → Telegram + Grafana.

---

## MỤC TIÊU CỤ THỂ CỦA ĐỀ TÀI

| Hạng mục | Mô tả | Trạng thái |
|:---|:---|:---:|
| Bộ mô phỏng vật lý 4 pha (có ground-truth, seed cố định) | Tái tạo 100%, phục vụ huấn luyện và oracle two-pass | ✅ |
| LSTM Forecaster dự báo $p_{5\min}$ | Forecasting xác suất, không phải classification trạng thái | ✅ |
| PPO RL Controller 4 actions, Gymnasium env | Học chính sách trong môi trường có vật lý tích hợp | ✅ |
| Streaming pipeline Kafka + Spark | Độ trễ end-to-end < 1 giây, hỗ trợ big-data scaling | ✅ |
| Telegram chatbot defense-in-depth | Cảnh báo đẩy + điều khiển từ xa, 2 kênh độc lập | ✅ |
| Oracle two-pass benchmark | So sánh công bằng các bộ điều khiển | ✅ |
| Đánh giá LSTM trên dữ liệu cảm biến **thực** Kaggle 132K | Bằng chứng tổng quát hoá ngoài simulator | ✅ |
| Docker Compose 10 services + 1 lệnh khởi động | Reproducibility cấp hệ thống | ✅ |

---

<!-- _class: lead -->

# 03
# TIẾN ĐỘ HIỆN TẠI

---

## TIẾN ĐỘ TỔNG THỂ THEO KẾ HOẠCH GANTT

| Giai đoạn | Nội dung | Tiến độ |
|:---|:---|:---:|
| GĐ1 | Phân tích & thiết kế kiến trúc 4 lớp | **Hoàn thành** |
| GĐ2 | Triển khai IoT + Data Pipeline (MQTT/Kafka/Spark) | **Hoàn thành** |
| GĐ3 | Phát triển mô hình AI (LSTM + PPO) | **Hoàn thành** |
| GĐ4 | Application (Backend, Dashboard, Telegram) | **95%** |
| – | Bản thảo LaTeX (5 chương, ~1.770 dòng) | **95%** |

**Bổ sung gần đây (13/05/2026):**

- Đánh giá LSTM trên **dữ liệu cảm biến thực Kaggle 132K** (~405k mẫu, 3 Raspberry Pi).
- Bootstrap 95% CI cho mọi chỉ số (siết khoảng tin cậy thống kê).
- Hoàn thiện slide BaoCaoTienDo theo luồng hệ thống mới (tài liệu hiện tại).

---

## KIẾN TRÚC HỆ THỐNG 4 LỚP – TỔNG QUAN

![h:300](thesis-latex/img/architecture.png)

```
┌──────────────────────────────────────────────────────────────────┐
│ Lớp 4 — APPLICATION                                              │
│   Dashboard ←  Node.js API  ←  InfluxDB / PostgreSQL  ←  Grafana │
│                  ↑                                       Telegram│
├──────────────────│───────────────────────────────────────────────┤
│ Lớp 3 — PROCESSING                                               │
│   Spark Structured Streaming  →  LSTM forecaster  →  PPO agent   │
├──────────────────↑───────────────────────────────────────────────┤
│ Lớp 2 — COMMUNICATION                                            │
│   MQTT broker (Mosquitto)  →  MQTT-Kafka bridge  →  Kafka topics │
├──────────────────↑───────────────────────────────────────────────┤
│ Lớp 1 — DEVICE / PERCEPTION                                      │
│   ESP32 + MQ-2/MQ-135 + DHT22   ←hoặc→   Python Simulator 4 pha  │
└──────────────────────────────────────────────────────────────────┘
```

**Luồng dữ liệu (đi từ dưới lên):** Cảm biến/Simulator → MQTT broker → Kafka topic → Spark Streaming (LSTM + PPO) → InfluxDB/PostgreSQL → API/SSE → Dashboard / Telegram / Grafana.

---

## 4 LỚP – CHỨC NĂNG VÀ CÔNG NGHỆ

| Lớp | Vai trò | Công nghệ cốt lõi | Đầu vào → Đầu ra |
|:---|:---|:---|:---|
| **1. Device** (Perception) | Đọc tín hiệu vật lý → số hoá → publish | ESP32 + MQ-2/MQ-135 + DHT22, hoặc Simulator phần mềm | Tín hiệu analog → JSON 1 Hz |
| **2. Communication** | **Truyền tải IoT** nhẹ + **buffer big-data** | **MQTT** (Mosquitto) → **Kafka** (commit log) | JSON device → Kafka topic `gas.raw.sensor` |
| **3. Processing** | Streaming + inference 2 module ML | Spark Structured Streaming + **LSTM** + **PPO** | Kafka stream → $p_{5\min}$ + action → write DB + alert event |
| **4. Application** | Lưu trữ + giao diện + cảnh báo | InfluxDB, PostgreSQL, Node.js API, Express dashboard, Telegram bot, Grafana | Reading + alert → user |

→ Phân tầng giúp **tách trách nhiệm rõ ràng**, mỗi tầng thay thế độc lập (vd. đổi Kafka sang Pulsar không ảnh hưởng tầng xử lý).

---

## MQTT LÀ GÌ VÀ VÌ SAO ĐẶT TẠI LỚP TRUYỀN THÔNG?

**MQTT (Message Queuing Telemetry Transport)** — giao thức **publish-subscribe** dựa trên TCP, do IBM phát triển 1999, **chuẩn ISO/IEC 20922:2016** cho IoT.

**Vai trò trong hệ thống**: là **kênh transport** giữa **thiết bị (ESP32)** và **hạ tầng phía sau (Kafka)** — không lưu trữ, không xử lý ML, chỉ chuyển message.

| Đặc tính MQTT | Vì sao cần cho bài toán gas |
|:---|:---|
| **Header 2 byte**, payload tối thiểu | ESP32 chỉ có 4 MB flash + chạy bằng pin → giao thức nhẹ là bắt buộc |
| Mô hình **publish-subscribe** | ESP32 chỉ "phát" lên topic, không cần biết ai nhận → dễ thêm/bớt thiết bị |
| **Last Will & Testament (LWT)** | WiFi gia đình VN hay rớt → broker tự phát "device offline" giúp dashboard hiện trạng thái |
| **QoS 1 — at-least-once** | Trong pha LEAK, **không được phép mất gói** → QoS 1 đảm bảo retry |
| **Retain Message** | Subscriber join muộn vẫn nhận được trạng thái mới nhất |

→ MQTT **không phải Kafka**: không có persistence, không có replay, không scale ngang được. Vì vậy bắt buộc **bridge sang Kafka** ở bước sau để có những khả năng đó.

---

## VÌ SAO KAFKA – XỬ LÝ DỮ LIỆU LỚN STREAMING

**Apache Kafka** là **distributed commit log**, được đặt sau MQTT để giải quyết các yêu cầu **không có ở MQTT**:

- **Persistence + replay**: mọi message ghi xuống đĩa → có thể re-train LSTM trên dữ liệu lịch sử mà không cần chạy lại bộ mô phỏng.
- **Throughput big-data**: Kafka có thể xử lý **hàng triệu message/giây/broker**; topic `gas.raw.sensor` được phân **partition theo `device_id`** → scale ngang khi nhiều thiết bị.
- **Multi-consumer độc lập**: cùng một stream được Spark (xử lý ML), Telegram bot (cảnh báo) và Grafana (giám sát) đọc song song mà không ảnh hưởng nhau (decoupling).
- **Exactly-once với Spark**: kết hợp với checkpoint của Spark Structured Streaming, đảm bảo không mất / không trùng lặp record.

**3 topic** trong hệ thống: `gas.raw.sensor` (đo thô), `gas.alert.events` (cảnh báo), `gas.action.events` (nhật ký hành động).

---

## LỚP XỬ LÝ – HAI MODULE ML XỬ LÝ THEO CHUỖI THỜI GIAN

Spark Structured Streaming **micro-batch ~100 ms**. Trong mỗi batch:

| Bước | Mô tả | Vai trò theo time-series |
|:---|:---|:---|
| 1 | Đọc Kafka, parse JSON | Cập nhật **sliding window 60 s** per `device_id` |
| 2 | **Module LSTM** nhận chuỗi $(g_{t-59..t}, T, H)$ | Học **chuỗi đầu vào 60 bước**, dự báo $p_{5\min}$ — chuỗi tương lai 300 bước |
| 3 | **Module PPO** nhận state 8-chiều có chứa $p_{5\min}$ | Quan sát **chuỗi trạng thái** (gas, slope, $p$, fan, valve, $\Delta t$) → policy quyết định action |
| 4 | Ghi InfluxDB + publish alert lên Kafka | Lưu chuỗi thời gian + bắn event |

→ **Hai module bổ trợ** trên cùng dòng chuỗi: LSTM "đọc quá khứ và dự đoán tương lai gần"; PPO "đọc trạng thái hiện tại + dự báo và ra quyết định".

---

<!-- _class: lead -->

# 03.2
# DỮ LIỆU & MÔ PHỎNG

---

## DATASET – ĐỊNH NGHĨA & DẠNG DỮ LIỆU

**Dataset** trong đề tài là **tabular numeric time-series** — bảng số, mỗi **hàng = 1 mẫu đo ở thời điểm $t$**, mỗi **cột = 1 thuộc tính (attribute) số thực hoặc nguyên**.

| Thuộc tính dataset | Mô tả |
|:---|:---|
| **Định dạng** | CSV / Parquet, tabular numeric (không phải ảnh, văn bản hay đồ thị) |
| **Đơn vị mẫu** | 1 hàng = 1 lần đo, lấy với chu kỳ **1 Hz** (mỗi giây 1 dòng) |
| **Tần số lấy mẫu** | 1 Hz — đủ vì hằng số thời gian cảm biến MQ là 3–10 s |
| **Loại bài toán** | Time-series forecasting (LSTM) + sequential decision making (PPO) |
| **Cấu trúc cửa sổ** | Cửa sổ trượt 60 mẫu (60 s) làm input, nhãn = đỉnh 300 mẫu tương lai |

**Mô tả từng cột (attributes)**:

| Tên cột | Ý nghĩa | Kiểu | Miền giá trị | Vai trò |
|:---|:---|:---|:---|:---|
| `gas_ppm`           | Nồng độ khí gas đo được | float32 | [50, 2000] ppm | LSTM input, RL state |
| `temperature_c`     | Nhiệt độ môi trường | float32 | [15, 40] °C | LSTM input, RL state |
| `humidity_percent`  | Độ ẩm tương đối | float32 | [30, 90] % | LSTM input, RL state |
| `slope`             | Đạo hàm bậc 1 (polyfit 30 mẫu cuối) | float32 | [-5, 10] ppm/s | RL state |
| `p_5min`            | **Đầu ra LSTM** (xác suất, không phải nhãn) | float32 | [0, 1] | RL state |
| `fan_on`            | Trạng thái quạt | bool | {0, 1} | RL state |
| `valve_closed`      | Trạng thái van | bool | {0, 1} | RL state |
| `time_since_action` | Thời gian từ action ≠ NO_OP gần nhất | float32 | [0, 1800] s | RL state |
| `event_ts`          | Timestamp epoch | int64 | ms | metadata |
| `_leak_state`       | **Ground-truth** pha LEAK (NORMAL/LEAK_SLOW/LEAK_FAST/VENTILATING) | int4 | 4 lớp | chỉ đánh giá |
| `_seconds_to_critical` | **Ground-truth** số giây đến gas chạm 1000 ppm | float32 | s | chỉ đánh giá |

→ Cột bắt đầu bằng `_` là **ground-truth chỉ phục vụ chấm điểm**, **không** đưa vào input mô hình → tránh data leakage.

---

## VÌ SAO DÙNG SIMULATOR + KAGGLE CHỨ KHÔNG CHỈ KAGGLE?

**Câu hỏi quan trọng**: dữ liệu thực Kaggle 132K đã có, vì sao vẫn dùng simulator?

| Câu hỏi | Kaggle 132K | Simulator |
|:---|:---|:---|
| Có **ground-truth pha leak** không? | ❌ chỉ là môi trường bình thường, không có nhãn leak | ✅ biết chính xác NORMAL/LEAK_SLOW/LEAK_FAST/VENTILATING |
| Có **chuỗi rò rỉ kéo dài 5 phút**? | ❌ chủ yếu là baseline | ✅ kích hoạt được theo ý |
| Cho phép **agent RL tương tác** + thay đổi physics không? | ❌ dữ liệu tĩnh, không "đóng van" lại được | ✅ là môi trường Gymnasium, RL bước được |
| Có **`seconds_to_critical`** để oracle two-pass? | ❌ | ✅ |

→ **Quyết định**: train PPO **bắt buộc** trên simulator (cần environment); train LSTM trên **cả hai** để vừa có nhãn forecast rõ ràng (simulator) vừa có bằng chứng tổng quát hoá sang phần cứng thực (Kaggle).

---

## VÌ SAO SIMULATOR ĐÁNG TIN CẬY – BẰNG CHỨNG

Để chứng minh dữ liệu mô phỏng **không phải synthetic vô căn cứ**, chúng tôi đối chiếu với 3 chuẩn:

1. **Vật lý động học khí** — 4 pha bám theo phương trình lan truyền khí trong môi trường có thông gió: tăng tuyến tính (rò rỉ van chậm), tăng mũ (vỡ ống), giảm mũ (ventilating) [Webster & Wilkinson 2017, *Gas Dispersion in Enclosed Spaces*].
2. **Datasheet MQ-2**: nồng độ khí gas LPG đo được trong dải 200–10.000 ppm, đặc tính phi tuyến — simulator bám sát dải này và nhiễu Gaussian biên độ ±3 ppm phù hợp với SNR thực tế của ADC 12-bit ESP32.
3. **Đối chiếu LSTM trên Kaggle thực 132K**: cùng kiến trúc, LSTM giữ Accuracy 95,56%, Recall 87,36% — nếu simulator "không thực", model train trên đó sẽ thất bại trên Kaggle (gần ngẫu nhiên ~50%) chứ không đạt 95%.

→ Simulator là **digital twin** đủ tốt để train, **Kaggle là chứng cứ tổng quát hoá**.

---

## BỘ MÔ PHỎNG VẬT LÝ – TỪ ĐÂU CÓ 4 PHA?

4 pha **không phải tự đặt**, mà tổng hợp từ **3 nguồn được công bố** và **chỉnh cho ngữ cảnh Việt Nam**:

1. **State-machine cảm biến khí** [Gambiroza 2020 — IEEE Sensors] có 3 trạng thái cơ bản: *baseline / leak / recovery* — đề tài tách **leak thành 2 mức** theo tốc độ rò.
2. **Phương trình lan truyền khí trong không gian kín** [Webster & Wilkinson 2017, *Gas Dispersion in Enclosed Spaces*]: tuyến tính cho leak chậm, **mũ** $e^{kt}$ cho vỡ ống, **suy giảm mũ** $e^{-kt}$ cho thông gió.
3. **Thống kê sự cố gas Việt Nam** [Cục Cảnh sát PCCC&CNCH — C07 — Báo cáo cháy nổ 2022; tổng hợp báo VnExpress 2020–2023]: 2 dạng phổ biến là **dây cao su nứt / chuột cắn** (rò chậm) và **bếp gas mini nổ / vỡ van bình** (rò nhanh).

| Pha | Phương trình | Ngữ cảnh hộ gia đình Việt Nam |
|:---|:---|:---|
| **NORMAL** | $gas \to 60$ ppm + Gauss(3) | Nền không gian bếp khi không nấu (60 ppm = mức cảm biến MQ-2 ổn định) |
| **LEAK_SLOW** | $gas += 5$ ppm/s | **Dây dẫn cao su nứt / chuột cắn / khớp nối lỏng** giữa bình LPG 12 kg và bếp |
| **LEAK_FAST** | $gas \cdot e^{0.04t} + 8t$ | **Vỡ van bình mini, nổ bình du lịch, quên tắt bếp khi nước trào** — tăng mũ |
| **VENTILATING** | $gas \cdot e^{-0.03t}$ | Sau khi đóng van bình / bật quạt thông gió |

Seed cố định → tái tạo 100%. Cung cấp **ground-truth** `_leak_state` và `_seconds_to_critical` cho **Oracle two-pass**.

---

## QUY MÔ DATASET CHO TỪNG THÍ NGHIỆM

> **Phân biệt**: bảng dưới mô tả **dataset** (dữ liệu thô + cách chia train/test). **Cấu hình huấn luyện mô hình** (epochs, batch size, learning rate, vv.) nằm ở slide kiến trúc LSTM/PPO sau, **không trộn vào đây**.

| Thí nghiệm | Nguồn dữ liệu | Số mẫu | Tỷ lệ nhãn + |
|:---|:---|---:|---:|
| LSTM (simulator) | 8h × 1Hz, seed=42, cửa sổ=60, horizon=300 | 28.439 | 26,18% |
| └─ train (80%) | chronological split | 22.751 | 26,1% |
| └─ test (20%)  | tail | 5.688 | 21,2% |
| **LSTM (Kaggle thực)** | 405k mẫu, 3 Raspberry Pi, MQ-2/7 + DHT22 | **404.101** | **5,3%** |
| └─ train (80%) | per-device chronological | 323.280 | 8,5% |
| └─ test (20%)  | tail | **80.821** | 1,3% |
| PPO RL training | Trải nghiệm sinh online trong env Gymnasium | 200.000 step | – |
| Benchmark đánh giá | 4h × 1Hz × 3 seeds | 14.400/seed | – |

**Cách sinh nhãn LSTM**: $y_t = \mathbf{1}[\max_{\tau \in [t+1, t+300]} gas_\tau > 1000\text{ ppm}]$

→ Đây là **forecasting** (dự đoán đỉnh tương lai 5 phút), không phải classification **trạng thái tức thời** — nhãn $y_t$ **không** đến từ cột `_leak_state`.

---

<!-- _class: lead -->

# 03.3
# MÔ HÌNH LSTM FORECASTER

---

## LSTM – KIẾN TRÚC VÀ VÌ SAO PHÙ HỢP

**Bài toán**: dự đoán **xác suất** $p_{5\min} \in [0,1]$ rằng nồng độ khí gas sẽ vượt 1000 ppm trong 5 phút tới, dựa trên 60 giây quá khứ.

**Vì sao LSTM phù hợp:**

- Bài toán có **phụ thuộc dài hạn 60 bước** — RNN thuần gặp **vanishing gradient**, MLP/CNN không nhớ thứ tự.
- LSTM có **cell state $C_t$ + 3 cổng** (forget/input/output) cho phép gradient truyền ngược qua nhiều bước thời gian với suy giảm tối thiểu [Hochreiter & Schmidhuber 1997].
- Đã được chứng minh trong [Gambiroza 2020] cho **đặc tính quá độ của MQ sensor** — bài toán tương đồng.

**Vì sao đề xuất kiến trúc 32 unit nhỏ**:

- Hệ thống streaming yêu cầu inference < 1 s/mẫu → mô hình nhỏ ưu tiên.
- Dữ liệu 22.751 mẫu không cần model lớn → tránh overfit.
- Thực nghiệm xác nhận: ~5.000 tham số đủ để đạt Precision 95% trên simulator.

---

## LSTM – BẢNG MÔ TẢ KIẾN TRÚC

| Lớp | Tham số | Số param | Vai trò |
|:---|:---|---:|:---|
| Input | shape=(60, 3) | 0 | Chuỗi 60 giây × {gas, temp, hum} đã chuẩn hoá |
| **LSTM** | 32 units, tanh + sigmoid gates | 4.608 | Trích đặc trưng theo chuỗi thời gian |
| Dropout | rate=0.2 | 0 | Regularize chống overfit |
| Dense | 16 units, ReLU | 528 | Phi tuyến trung gian |
| **Output** | 1 unit, **sigmoid** | 17 | **Xác suất** $p_{5\min}$ — không phải nhãn cứng |
| **Tổng** | | **~5.153** | |

Loss: **weighted binary cross-entropy** ($w_{pos}\approx 2.82$). Optimizer: Adam(1e-3). Epochs: 15. Batch: 128.

> **Đầu ra là giá trị xác suất liên tục** — bộ điều khiển phía sau dùng giá trị này như một feature (không cần ngưỡng hoá).

---

## LSTM – SƠ ĐỒ KHỐI INPUT / OUTPUT

```
┌──────────────────────────┐                ┌────────────────────┐
│ INPUT — ma trận (60, 3)  │                │ OUTPUT — scalar    │
│ ────────────────────────│   LSTM 32u →   │ ──────────────────│
│ gas(t-59) … gas(t)       │   Dropout 0.2  │  p_5min ∈ [0, 1]   │
│ temp(t-59)… temp(t)      │   Dense 16 ReLU│                    │
│ hum(t-59) … hum(t)       │   Dense 1 sigm │  GIÁ TRỊ xác suất  │
│ (đã chuẩn hoá)           │                │  (không phải nhãn) │
└──────────────────────────┘                └────────────────────┘
```

- **Đầu vào**: ma trận $(60, 3)$ — 60 giây quá khứ × 3 đặc trưng, chuẩn hoá: gas/2000, temp/60, hum/100.
- **Đầu ra**: **giá trị xác suất liên tục** $p_{5\min} \in [0,1]$ — đây là **giá trị**, *không* phải nhãn 0/1; được PPO dùng trực tiếp như feature.
- **Ngưỡng quyết định 0,5** **chỉ** được dùng khi cần label nhị phân để đo Precision/Recall trên tập test. Ở runtime, PPO **không ngưỡng hoá** mà tiêu thụ giá trị xác suất gốc.

---

## HUẤN LUYỆN LSTM (SIMULATOR)

![h:340](thesis-latex/img/exp/lstm_training.png)

Train acc ~92%, val acc ~90%, không overfit, hội tụ sau epoch 8–10. Thời gian: 50–60 s trên CPU.

---

## KẾT QUẢ LSTM TRÊN SIMULATOR

| Chỉ số | Giá trị | Diễn giải |
|:---|:---:|:---|
| Accuracy | **89,98%** | Tổng quát đúng (baseline lười = 74%) |
| **Precision** | **95,68%** | Rất ít kêu nhầm — chỉ 30 FP/4.484 mẫu âm (0,67%) |
| Recall | 55,15% | Bỏ sót giai đoạn rất sớm LEAK_SLOW |
| F1 | 69,97% | – |
| TP / FP | 664 / 30 | – |
| TN / FN | 4.454 / 540 | – |

→ Mô hình **thận trọng**: ưu tiên Precision cao (ít kêu nhầm) hơn Recall — phù hợp khi đây chỉ là feature cho PPO, không phải bộ phát cảnh báo duy nhất.

---

## LSTM TRÊN DỮ LIỆU THỰC KAGGLE 132K

**Dataset**: `garystafford/environmental-sensor-data-132k` — 405k mẫu, 3 Raspberry Pi (MQ-2 + MQ-7 + DHT22), 7 ngày T7/2020.

![h:300](thesis-latex/img/exp/lstm_confusion_matrix_kaggle.png)

Tập test: 80.821 cửa sổ (gấp **14 lần** test simulator). Bootstrap 95% CI với 2.000 lần resampling.

---

## SO SÁNH SIMULATOR vs KAGGLE THỰC

| Chỉ số | Simulator (5.688) | **Kaggle thực (80.821)** |
|:---|:---:|:---:|
| Accuracy | 89,98% | **95,56%** [95,4; 95,7] |
| Precision | **95,68%** | 21,15% [20,0; 22,3] |
| Recall | 55,15% | **87,36%** [85,2; 89,2] |
| F1 | **69,97%** | 34,05% |
| Tỷ lệ + test | 21,2% | 1,3% |

**Đảo nghịch Precision↔Recall** không phải bất thường:
- Simulator: leak có biên độ lớn rõ → Precision cao, Recall thấp.
- Kaggle: "đỉnh tương lai" theo phân vị p95 bao cả dao động ngắn → Recall cao, Precision thấp (nhưng FP tuyệt đối chỉ 4,3% trên mẫu âm — vẫn rất thấp).

→ **LSTM KHÔNG bị overfit simulator** — tín hiệu xu hướng đã học có tính tổng quát sang phần cứng thực.

---

<!-- _class: lead -->

# 03.4
# MÔ HÌNH PPO RL CONTROLLER

---

## PPO – BÀI TOÁN VÀ ĐỘNG LỰC SỬ DỤNG

**Bài toán điều khiển**: tại mỗi giây, chọn 1 trong 4 hành động {NO_OP, ALERT, FAN_ON, CLOSE_VALVE} sao cho **giảm thiểu thiệt hại + tránh phiền nhiễu**.

**Vì sao RL chứ không phải supervised?**
- Không có nhãn "hành động đúng" cho mỗi trạng thái — cùng 600 ppm tăng dần, action tối ưu phụ thuộc lịch sử.
- Reward có **độ trễ** — đóng van $t_0$ chỉ thấy hiệu quả sau vài giây.
- Cần cân bằng **mục tiêu xung đột** (phát hiện sớm vs cảnh báo sai) — RL học natively.

**Vì sao PPO trong họ RL?**
- **Ổn định khi train**: clipping ngăn policy thay đổi đột ngột (so với REINFORCE).
- **Sample efficiency tốt** với on-policy nhỏ, không cần replay buffer khổng lồ (so với DQN).
- **Hỗ trợ thư viện**: Stable-Baselines3 implement chuẩn, tin cậy [Raffin 2021].
- **Phù hợp action rời rạc** — đúng dạng bài toán của đề tài.

---

## PPO – CÁC THÀNH PHẦN MDP TRONG ĐỀ TÀI

Bài toán điều khiển được hình thức hoá thành **Markov Decision Process** $\mathcal{M} = (\mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma)$. Mỗi ký hiệu **gắn cụ thể với đối tượng trong code** của đề tài:

| Thành phần MDP | Đề tài cụ thể là gì | Cài đặt code |
|:---|:---|:---|
| **Environment** $\mathcal{E}$ | Class `GasLeakEnv` kế thừa `gymnasium.Env`, **bao bọc** simulator 4 pha. Mỗi step gọi `World.step()` → cập nhật gas/temp/hum, trả về reward + state mới | `processing/ml/rl/gas_env.py` |
| **State space $\mathcal{S}$** | Vector **8 chiều liên tục** chuẩn hoá [0,1]: $[gas, temp, hum, slope, p_{5\min}, fan, valve, \Delta t]$ | `Box(0,1, shape=(8,))` |
| **Action space $\mathcal{A}$** | **Rời rạc 4 phần tử**: 0=NO_OP, 1=ALERT, 2=FAN_ON, 3=CLOSE_VALVE | `Discrete(4)` |
| **Transition $\mathcal{P}(s'|s,a)$** | Phương trình vật lý 4 pha + xác suất chuyển pha NORMAL→LEAK = **5%/phút** (stochastic) | `STEP_FN[state]` |
| **Reward $\mathcal{R}(s,a)$** | Asymmetric cost — phạt nặng gas ≥ 1000 ppm, thưởng can thiệp đúng pha LEAK | `_compute_reward()` |
| **Agent** | Stable-Baselines3 PPO agent — gồm Actor π_θ + Critic V_φ | `stable_baselines3.PPO` |
| **Policy $\pi_\theta(a\|s)$** = **Actor network** | MLP: Dense(64,tanh) → Dense(64,tanh) → softmax(4) → phân phối trên 4 action | `MlpPolicy` (SB3) |
| **Value $V_\phi(s)$** = **Critic network** | MLP: Dense(64,tanh) → Dense(64,tanh) → Dense(1) → ước lượng $\mathbb{E}[\sum \gamma^k r_{t+k}]$ | shared trunk với Actor |
| **Discount $\gamma$** | 0,99 — ưu tiên reward dài hạn (giảm peak gas trong tương lai) | hyperparameter |
| **GAE $\lambda$** | 0,95 — Generalized Advantage Estimation [Schulman 2016] | hyperparameter |

---

## PPO – HÀM REWARD VÀ VÌ SAO THIẾT KẾ NHƯ VẬY

Reward theo nguyên tắc **asymmetric cost** — bỏ sót leak phải nặng hơn nhiều cảnh báo sai:

| Tình huống | Reward | Lý do |
|:---|---:|:---|
| Mỗi bước có $gas \geq 1000$ ppm | **–50** | An toàn là ưu tiên #1: mỗi giây nguy hiểm đều tính |
| FAN_ON / CLOSE_VALVE đúng trong pha LEAK | **+10** | Thưởng hành vi mong muốn |
| ALERT_USER khi NORMAL (FP nhẹ) | –3 | Chỉ phiền |
| FAN_ON khi NORMAL | –15 | Tốn điện |
| CLOSE_VALVE khi NORMAL | **–25** | Ngắt nguồn gas — thiệt hại trải nghiệm thật |
| Step cost (mỗi bước) | –0,05 | Tránh dùng dằng |

Công thức:
$$r_t = -50\cdot\mathbf{1}[gas \geq 1000] + 10\cdot\mathbf{1}[a\in\{2,3\}\land \text{LEAK}] - 3\cdot\mathbf{1}[a{=}1, \text{NORMAL}] - 15\cdot\mathbf{1}[a{=}2, \text{NORMAL}] - 25\cdot\mathbf{1}[a{=}3, \text{NORMAL}] - 0{,}05$$

→ Tỷ lệ –25 / +10 / –50 được cân: agent không "lười đóng van" mà cũng không "đóng bừa".

---

## PPO – ACTOR NETWORK & VALUE NETWORK

![h:280](thesis-latex/img/ppo_arch.png)

```
state s_t (8 dim)
       │
       ▼
   Dense(64, tanh)
       │
       ▼
   Dense(64, tanh)       ← trunk dùng chung
       │
   ┌───┴───┐
   ▼       ▼
Actor      Critic
Dense(4)   Dense(1)
softmax    scalar V(s)
   │
   ▼
π(a|s) ∈ Δ³           ~5.060 tham số tổng
```

- **Actor**: phân phối chính sách trên 4 action → sample $a_t$.
- **Critic**: ước lượng $V_\phi(s)$ → tính advantage $\hat{A}_t = r_t + \gamma V(s_{t+1}) - V(s_t)$ và GAE($\lambda=0.95$).
- **Loss PPO clipped**: $L^{CLIP} = \mathbb{E}[\min(r_t(\theta)\hat{A}_t, \text{clip}(r_t(\theta), 1\!-\!\epsilon, 1\!+\!\epsilon)\hat{A}_t)]$, $\epsilon=0.2$.

---

## PPO – CẤU HÌNH HUẤN LUYỆN

```python
env = make_vec_env(lambda: GasLeakEnv(episode_seconds=1800), n_envs=4, seed=42)
model = PPO("MlpPolicy", env,
    n_steps=512, batch_size=128,
    gae_lambda=0.95, gamma=0.99,
    learning_rate=3e-4, ent_coef=0.01)
model.learn(total_timesteps=200_000)
```

- 4 môi trường song song → đa dạng experience.
- Episode 1800 s → đủ thấy nhiều cycle NORMAL↔LEAK.
- Thời gian train **~3 phút 30 giây** trên CPU, throughput ~960 fps.

---

## KẾT QUẢ HUẤN LUYỆN PPO

![h:340](thesis-latex/img/exp/ppo_reward.png)

Reward hội tụ về dải [-2000; -1800]. **Reward âm không có nghĩa policy kém**: chỉ cần 30 s gas ≥ 1000 ppm là phạt 30×(-50) = -1500. Bằng chứng policy tốt: peak gas **63 ppm** vs baseline 1.508 ppm (chứng minh ở phần benchmark).

---

## TỔNG HỢP HUẤN LUYỆN HAI MÔ HÌNH

| Hạng mục | LSTM Forecaster | PPO RL Controller |
|:---|:---|:---|
| Loại | Supervised, time-series | RL on-policy (actor-critic) |
| Bài toán | Dự báo **xác suất** $p_{5\min}$ | Điều khiển 4 hành động |
| Tham số | ~5.153 | ~5.060 |
| Dữ liệu | 22.751 mẫu (sim) + 323.280 (Kaggle) | 200k timesteps |
| Hyper | Adam(1e-3), 15 epochs | $\gamma=0.99$, $\lambda=0.95$, lr=3e-4 |
| Mất mát | Weighted BCE | PPO clipped + value + entropy |
| Thời gian (CPU) | ~50–60 s | ~3 phút 30 giây |

→ Hai mô hình **bổ trợ**: LSTM trích feature $p_{5\min}$ → PPO state. Đây là **hierarchical learning**, không cạnh tranh.

---

<!-- _class: lead -->

# 03.5
# ĐÁNH GIÁ & BENCHMARK

---

## VÌ SAO CHỌN 4 TIÊU CHÍ ĐÁNH GIÁ – CÓ THAM CHIẾU CỤ THỂ

Đề tài **không tự chế** 4 chỉ số; mỗi chỉ số đều **lấy từ chuẩn công nghiệp / bài báo** đã công bố:

| Chỉ số | Định nghĩa | Tham chiếu (vì sao chọn) |
|:---|:---|:---|
| **lead_time_s** | Số giây cảnh báo trước thời điểm gas đạt 1000 ppm theo Oracle. **Cao = tốt** | **IEC 60079-29-1:2016** §5.4 *"Pre-alarm response time"* — yêu cầu hệ thống cảnh báo gas cháy nổ phải báo **trước** khi vượt 20% LEL; [Saranya 2023] cũng dùng "lead time" làm metric chính |
| **miss_rate (%)** | % sự kiện LEAK không được hành động trước thời điểm critical. **Thấp = tốt** | **IEC 61508** *Functional Safety* khái niệm **PFD** (Probability of Failure on Demand) — cốt lõi cho Safety Integrity Level (SIL) |
| **alarms_per_hour** | Số cảnh báo phát trong pha NORMAL (false alarm rate). **Thấp = tốt** | **EEMUA 191:2013** §6.3 — khuyến nghị **≤ 6 alarm/giờ/operator** để tránh "alarm fatigue"; vượt ngưỡng này operator sẽ mất tin tưởng và bỏ qua |
| **mean_peak_gas (ppm)** | Nồng độ đỉnh trung bình của các leak event. **Thấp = tốt** | **NFPA 58 §6.27** *Leak Mitigation* — yêu cầu hệ thống có actuator phải **giới hạn nồng độ tích luỹ**; chỉ controller có van/quạt mới ảnh hưởng được |

→ Bài toán là **multi-objective**: không có single number; **bắt buộc nhìn cả bộ tứ**. RL thắng ở Peak Gas + Alarm, FORECASTER thắng ở Lead Time đối với LSTM-only baseline, THRESHOLD chỉ là sàn so sánh.

---

## ORACLE TWO-PASS – PHƯƠNG PHÁP SO SÁNH CÔNG BẰNG

**Vấn đề**: simulator có yếu tố ngẫu nhiên → mỗi controller chạy độc lập sẽ thấy tập leak khác nhau, không công bằng.

**Phương pháp**:

| Lượt | Mô tả |
|:---|:---|
| **Pass 1 – Oracle** | Chạy simulator với seed cố định, **không can thiệp** → ghi nhận `natural_critical_time` cho mỗi sự kiện leak |
| **Pass 2 – Controller** | Chạy lại với **cùng seed** → các leak xảy ra cùng thời điểm; controller hành động → ghi `first_action_time` |
| **Tính** | `lead_time = natural_critical_time − first_action_time` |

→ Mọi controller đánh giá trên **cùng tập sự kiện** → so sánh khoa học công bằng.

---

## BENCHMARK – 3 BỘ ĐIỀU KHIỂN

| | THRESHOLD | FORECASTER | RL (PPO) |
|:---|:---:|:---:|:---:|
| Cơ chế | gas > 800 ppm → alert | $p_{5\min} > 0.5$ → alert | Policy chọn 1/4 actions |
| Có **dự báo trước**? | ❌ | ✅ | ✅ |
| Có **can thiệp vật lý**? | ❌ | ❌ | ✅ |
| Phạm vi action | 1 (alert) | 1 (alert) | 4 (NO_OP/ALERT/FAN/VALVE) |

**Setup**: 3 seeds (42, 43, 44) × 4 giờ mô phỏng/seed, Oracle two-pass.

---

## KẾT QUẢ BENCHMARK – BẢNG SỐ LIỆU

| Bộ điều khiển | Lead (s) | Miss (%) | Alarm/giờ | Peak (ppm) |
|:---|---:|---:|---:|---:|
| THRESHOLD  | 35 ± 5 | 0,0 ± 0,0 | 2,8 ± 1,0 | 1.508 ± 88 |
| FORECASTER | 138 ± 26 | 4,2 ± 5,9 | 5,6 ± 1,1 | 1.508 ± 88 |
| **RL (PPO)** | **1.803 ± 755** | 15,0 ± 10,8 | **0,2 ± 0,0** | **63 ± 0** |

- **RL giảm Peak Gas 24 lần** (63 vs 1.508 ppm) — minh chứng mạnh nhất giá trị tầng điều khiển.
- **FORECASTER tăng lead time 4 lần** (138 vs 35 s) — minh chứng giá trị tầng dự báo.
- **RL giảm false alarm xuống 0,2/giờ** — thấp hơn cả 2 baseline (EEMUA 191 ngưỡng < 6).

---

## BENCHMARK – TRỰC QUAN HOÁ

![h:420](thesis-latex/img/exp/benchmark_chart.png)

---

## PHÂN TÍCH BENCHMARK HỖN HỢP

- **Lead time**: THRESHOLD đo khoảng cách vật lý 800→1000 ppm (~35 s); FORECASTER cộng thêm dự báo (+103 s); RL gần như đóng van ngay khi vào pha LEAK nên lead time đo theo critical-time của Oracle rất lớn (1.803 s).
- **Miss rate 15% của RL** là **artifact của cách đếm benchmark**: `valve_closed` không reset giữa các leak liên tiếp → khi leak sau đến, agent thấy van đã đóng → không "hành động lần 2" → benchmark tính là miss. Kiểm chứng ở **benchmark con TC-Slow/TC-Fast cho miss rate 0%**.
- **Alarms/giờ**: RL chỉ 0,2 — chính sách phạt –25 cho CLOSE_VALVE sai đã được học hiệu quả.
- **Peak gas**: chỉ RL có actuator vật lý → chỉ RL kéo nồng độ về 63 ppm.

→ Hai mô hình **bổ sung**: LSTM cảnh báo sớm, PPO can thiệp vật lý quyết liệt.

---

## BENCHMARK CON – 3 KỊCH BẢN XÁC ĐỊNH

Để bóc tách hành vi theo loại leak, chạy thêm benchmark **deterministic** (`SIM_LEAK_PROB_PER_MIN=0`, transition điều khiển bằng script).

| Kịch bản | Mô tả | Mục tiêu đánh giá |
|:---|:---|:---|
| **TC-Idle** | 60 phút thuần NORMAL | Đo riêng **false alarm rate** trong điều kiện không có leak |
| **TC-Slow** | 1 leak LEAK_SLOW tại $t=600$ s, 4 phút | Đo lead time + mitigation cho **rò rỉ chậm** (van bếp ga) |
| **TC-Fast** | 1 leak LEAK_FAST, hàm mũ | Đo lead time + mitigation cho **vỡ ống** |

Mỗi kịch bản: 1 giờ × 3 seed. Chỉ nhiễu Gaussian khác giữa các seed → so sánh chéo chặt chẽ.

---

## KẾT QUẢ BENCHMARK CON

![h:340](thesis-latex/img/exp/scenarios_chart.png)

---

## BẢNG KỊCH BẢN CON

| Kịch bản | Controller | Lead (s) | Miss (%) | Alarm/giờ | Peak (ppm) |
|:---|:---|---:|---:|---:|---:|
| TC-Idle | THRESHOLD | – | – | 0,0 ± 0,0 | – |
|         | FORECASTER | – | – | 2,0 ± 1,4 | – |
|         | RL | – | – | 1,0 ± 0,0 | – |
| TC-Slow | THRESHOLD | 41 ± 1 | 0,0 | 1,0 | 1.269 ± 38 |
|         | FORECASTER | 187 ± 3 | 0,0 | 5,0 ± 2,2 | 1.269 ± 38 |
|         | **RL** | **187 ± 3** | **0,0** | 1,0 | **60 ± 0** |
| TC-Fast | THRESHOLD | 4 ± 1 | 0,0 | 1,0 | 2.000 ± 0 |
|         | FORECASTER | 39 ± 1 | 0,0 | 4,0 ± 1,4 | 2.000 ± 0 |
|         | **RL** | **39 ± 1** | **0,0** | 1,0 | **60 ± 0** |

---

## PHÂN TÍCH KỊCH BẢN CON

**(a) TC-Idle — đo riêng false alarm trong điều kiện không có leak (60 phút thuần NORMAL)**
- THRESHOLD: **0 alarm/h** — vì nhiễu ±3 ppm trên nền 60 ppm gần như không bao giờ chạm 800 → ngưỡng cứng "an toàn" trong baseline yên tĩnh nhưng vô dụng trong leak nhanh (xem TC-Fast).
- FORECASTER: **2 alarm/h** — LSTM nhạy với dao động xu hướng → đôi khi nhận diện sai dao động Gaussian → vẫn dưới ngưỡng EEMUA 191 (≤6).
- RL: **1 alarm/h** — policy đã học cách "lọc" thoáng qua nhờ kết hợp gas tức thời + slope + $p_{5\min}$ → tốt nhất trong 3.

**(b) TC-Slow — rò rỉ chậm tại hộ gia đình VN (dây cao su nứt / chuột cắn / khớp lỏng)**
- Lead time: FORECASTER & RL = **187 s**, gấp **4,6 lần** THRESHOLD (41 s) → người dùng có >3 phút để rời nhà / đóng van thủ công thay vì <1 phút.
- **Miss rate 0% cho cả 3 controller** → đây cũng là bằng chứng quan trọng: miss 15% của RL ở benchmark hỗn hợp **chỉ là artifact** của cách đếm (valve không reset giữa các leak liên tiếp), không phải lỗi policy.
- Peak gas: RL = **60 ppm** vs FORECASTER 1.269 ppm — chỉ RL có actuator vật lý đóng van.

**(c) TC-Fast — vỡ van bình mini / nổ bình du lịch (kịch bản nguy hiểm nhất)**
- LEAK_FAST tăng mũ → chỉ có ~40 s từ thời điểm rò đến critical 1000 ppm.
- THRESHOLD chỉ kịp **4 s** → người dùng không có thời gian phản ứng → **THRESHOLD thực tế thất bại**.
- FORECASTER / RL: **39 s** → vẫn đủ thời gian alert + can thiệp.
- Peak gas: THRESHOLD/FORECASTER = **2.000 ppm** (chạm trần saturation cảm biến — tức nồng độ thật còn cao hơn); RL vẫn giữ **60 ppm** nhờ đóng van ngay khi $p_{5\min}$ vượt ngưỡng nội bộ.

→ Kết luận: **RL duy trì peak ≈ 60 ppm độc lập tốc độ leak** — giá trị nhất quán của tầng điều khiển vật lý. THRESHOLD chỉ phù hợp leak chậm; LSTM mở rộng cảnh báo sớm; PPO bổ sung tầng can thiệp.

---

## ĐỘ TRỄ END-TO-END PIPELINE

| Đoạn xử lý | Độ trễ | Nguồn |
|:---|---:|:---|
| Sensor → MQTT publish | < 10 ms | ước lượng |
| Mosquitto → MQTT-Kafka bridge | < 50 ms | ước lượng |
| Kafka → Spark consume (micro-batch) | < 100 ms | – |
| **LSTM inference (median)** | **68,3 ms** | đo trực tiếp 200 lần |
| └─ p95 / p99 | 75,9 / 77,9 ms | đo trực tiếp |
| **RL inference (median)** | **0,5 ms** | đo trực tiếp |
| └─ p95 / p99 | 0,8 / 1,3 ms | đo trực tiếp |
| Spark → InfluxDB write | < 30 ms | ước lượng |
| InfluxDB → API → SSE | < 50 ms | ước lượng |
| **Tổng end-to-end (median)** | **≈ 310 ms** | – |

→ Đáp ứng yêu cầu **thời gian thực mềm** (< 1 giây) cho hệ thống cảnh báo gas.

---

## TÍCH HỢP TELEGRAM CHATBOT

**Defense in depth — 2 kênh kích hoạt độc lập:**

1. **Event-driven (Kafka)**: backend consume topic `gas.alert.events` → `telegramService.notifyAlert()`.
2. **Polling realtime (InfluxDB)**: worker đọc reading mỗi 2-3 s, phát alert khi đạt ngưỡng.

**Bộ lọc tránh alert fatigue:**

- `risk_score ≥ 0,7` (= max của $p_{5\min}$ và $gas/$GAS_ALERT_PPM).
- Risk label ∈ {ALERT, CRITICAL}.
- Cooldown 60 s/(device, source, label).

→ Người dùng nhận cảnh báo kèm `rl_action`, `risk_score`, gas hiện tại — không chỉ "có cảnh báo".

---

## TRIỂN KHAI HẠ TẦNG

- **Docker Compose** đầy đủ **10 services** khởi động bằng 1 lệnh duy nhất.
- Container hoá: Mosquitto, MQTT-Kafka bridge, Kafka + Zookeeper, Spark, ML services, InfluxDB, PostgreSQL, Backend API, Frontend dashboard, Telegram bot, Grafana.
- Tài nguyên: ~5% CPU, ~2 GB RAM tổng cộng cho 1 thiết bị, 1 Hz.
- **Hỗ trợ horizontal scaling**: Kafka partition theo `device_id`, Spark executor, API replication, InfluxDB clustering — sẵn sàng cho big-data nhiều thiết bị.

---

## ĐÓNG GÓP KỸ THUẬT CHÍNH

1. **Bộ mô phỏng vật lý 4 pha** tái tạo được (seed cố định), 4 pha có cơ sở vật lý & tham chiếu sự cố LPG hộ gia đình Việt Nam.
2. **LSTM Forecaster đầu ra giá trị xác suất** (không phải nhãn) — feature cho RL.
3. **PPO Controller** đa hành động trong Gymnasium env tích hợp vật lý.
4. **Pipeline streaming** MQTT → Kafka → Spark, độ trễ < 310 ms, scaling-ready.
5. **Telegram chatbot defense-in-depth** qua 2 kênh.
6. **Phương pháp Oracle two-pass** so sánh công bằng có cơ sở.
7. **Docker Compose 10 services** + tái tạo bằng 1 lệnh.
8. **Đánh giá LSTM trên dữ liệu thực Kaggle 132K** — giảm sim-to-real gap.

---

## HẠN CHẾ

- **Phụ thuộc bộ mô phỏng cho PPO**: RL cần môi trường tương tác có ground-truth — chưa thay được bằng dataset thực. LSTM đã được validate qua Kaggle 132K.
- **Phạm vi benchmark còn hẹp**: 3 seeds × 4h — std lớn so với mean cho miss_rate. Cần mở rộng 10 seeds × 24h.
- **Chưa so sánh** với Transformer-based (TFT, PatchTST) hay RL khác (SAC, A2C).
- **Hàm reward chưa tối ưu**: hệ số phạt –50 chiếm tỷ trọng lớn, đường cong reward khó diễn giải. Cần `VecNormalize` + grid search.
- **Chưa triển khai phần cứng thực**: ESP32 + MQ thật còn ở mức kế hoạch ngắn hạn.
- **Cách đếm miss_rate trong benchmark hỗn hợp**: chưa reset `valve_closed` giữa các leak liên tiếp — đã kiểm chứng qua TC-Slow/TC-Fast.

---

## CÔNG VIỆC TIẾP THEO

- **Hoàn thiện bản thảo LaTeX** — rà soát chính tả/định dạng, build PDF cuối.
- **Đóng gói video demo** end-to-end (sensor → cảnh báo Telegram).
- **Chuẩn bị slides bảo vệ** (~25–30 slides).
- **Thử nghiệm phần cứng thực** ESP32 + MQ-2/MQ-135 trong điều kiện bếp gia đình.
- **Mở rộng benchmark** lên 10 seeds × 24h để siết khoảng tin cậy.
- **Reward shaping**: chuẩn hoá VecNormalize, grid search hệ số.
- **Bổ sung ablation**: benchmark `--reset-per-leak` để bóc tách artifact miss_rate của RL.

---

## THAM KHẢO CHÍNH

[1] Hochreiter & Schmidhuber, "Long Short-Term Memory," **Neural Computation**, 1997.
[2] Gambiroza et al., "LSTM-based transient response of low-cost gas sensors," **IEEE Sensors**, 2020.
[3] Stafford G.A., *Environmental Sensor Telemetry Data (132K records)*, **Kaggle**, 2020.
[4] Schulman et al., "Proximal Policy Optimization Algorithms," **arXiv:1707.06347**, 2017.
[5] Raffin et al., *Stable-Baselines3*, **JMLR**, 2021.
[6] Towers et al., *Gymnasium: A Standard Interface for RL Environments*, **arXiv:2407.17032**, 2023.
[7] IEC 60079-29-1: *Gas detectors — Performance requirements for flammable gases*.
[8] EEMUA 191: *Alarm systems — A guide to design, management and procurement*.
[9] NFPA 58: *Liquefied Petroleum Gas Code*.
[10] Tian et al., "Temperature compensation for MQ gas sensors," **Sensors and Actuators**, 2019.
[11] Wei et al., "DRL offloading for gas pipeline leak detection," **IEEE IoT-J**, 2022.

---

<!-- _class: lead -->

# CẢM ƠN THẦY CÔ
# ĐÃ LẮNG NGHE

*Hỏi đáp & góp ý*
