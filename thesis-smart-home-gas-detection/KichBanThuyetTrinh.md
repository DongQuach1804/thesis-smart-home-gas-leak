# Kịch bản thuyết trình — Báo cáo tiến độ khóa luận

**Đề tài:** Hệ thống phát hiện rò rỉ khí gas thông minh — tích hợp IoT, LSTM và PPO
**Sinh viên:** Lê Viết Dương (22520300) — Quách Minh Đông (22520259)
**GVHD:** ThS. Nguyễn Khánh Thuật — ThS. Văn Thiên Luân
**Ngày báo cáo:** 12/05/2026
**Thời lượng dự kiến:** 12–15 phút trình bày + 5–10 phút Q&A

---

## Slide 1 — Bìa

> "Kính thưa thầy, hôm nay em xin báo cáo tiến độ khóa luận tốt nghiệp với đề tài *Hệ thống phát hiện rò rỉ khí gas thông minh, tích hợp IoT, dự báo LSTM và học tăng cường PPO*. Nhóm gồm em Lê Viết Dương MSSV 22520300 và Quách Minh Đông 22520259, dưới sự hướng dẫn của thầy Nguyễn Khánh Thuật và thầy Văn Thiên Luân."

**Mục tiêu slide:** giới thiệu ngắn gọn, chuyển sang outline trong vòng 30 giây.

---

## Slide 2 — Nội dung báo cáo

> "Báo cáo của em gồm ba phần chính: phần một là tổng quan đề tài, nói về bối cảnh và vấn đề; phần hai là các nghiên cứu liên quan và hướng tiếp cận của nhóm; phần ba là tiến độ hiện tại — đây là phần dài nhất, bao gồm kiến trúc hệ thống, kết quả huấn luyện hai mô hình AI, kết quả benchmark, và đánh giá hệ thống vận hành."

---

# PHẦN 1 — TỔNG QUAN ĐỀ TÀI

---

## Slide 3 — Section divider "01 — Tổng quan đề tài"

> "Em xin bắt đầu phần một."

(Lướt nhanh, không dừng quá 5 giây.)

---

## Slide 4 — Rò rỉ khí gas: nguy cơ nghiêm trọng

> "Tại Việt Nam, khí gas hóa lỏng — gọi tắt là LPG — và khí tự nhiên được sử dụng rộng rãi trong hộ gia đình cũng như cơ sở sản xuất. Tuy nhiên đây cũng là nguồn nguy cơ rất lớn. Theo Cục Phòng cháy chữa cháy, mỗi năm xảy ra hàng trăm vụ cháy nổ liên quan đến rò rỉ khí gas, gây thiệt hại lớn về người và tài sản. Đặc điểm nguy hiểm là phần lớn các vụ rò rỉ này diễn ra âm thầm — người dùng chỉ phát hiện khi nồng độ đã đạt ngưỡng nguy hiểm hoặc khi ngửi thấy mùi. Câu hỏi đặt ra cho đề tài là: làm sao dự báo sớm rò rỉ và tự động ứng phó trước khi gas đạt ngưỡng nguy hiểm?"

**Điểm nhấn khi nói:** "âm thầm", "dự báo sớm", "tự động ứng phó".

---

## Slide 5 — Vai trò của IoT + AI

> "Có ba vai trò chính của IoT và AI trong an toàn nhà ở. Thứ nhất là cảnh báo sớm — dự báo trước 5 phút bằng LSTM trên chuỗi cảm biến để người dùng có thời gian sơ tán. Thứ hai là phản ứng tự động — RL agent tự bật quạt, đóng van mà không cần người dùng can thiệp. Thứ ba là giám sát từ xa — qua Telegram bot và dashboard, đảm bảo tiếp cận mọi lúc."

---

## Slide 6 — Thách thức của hệ thống ngưỡng tĩnh

> "Các hệ thống thương mại hiện nay chủ yếu hoạt động theo nguyên tắc ngưỡng tĩnh — báo động khi gas đạt khoảng 10% Lower Explosive Limit. Cách này có bốn hạn chế: thứ nhất là phản ứng muộn, đôi khi người dùng đã ngửi thấy mùi trước khi còi kêu; thứ hai là tỷ lệ false alarm cao do dao động độ ẩm, nhiệt độ; thứ ba là không có khả năng dự báo, không phân biệt được leak đang tăng dần với nồng độ nền cao ổn định; và thứ tư là phản ứng đơn lẻ — chỉ phát còi, không tự đóng van hay bật quạt. Do đó, cần một tiếp cận khác dựa trên học máy."

---

# PHẦN 2 — NGHIÊN CỨU LIÊN QUAN

---

## Slide 7 — Section divider "02"

> "Tiếp theo là phần hai về các nghiên cứu liên quan."

---

## Slide 8 — Bảng các công trình liên quan

> "Em đã khảo sát các nghiên cứu theo bốn hướng. Hướng IoT thuần như Saranya 2023 với Arduino và MQ-2 — phương pháp này cải thiện kết nối nhưng vẫn dùng ngưỡng tĩnh. Hướng học máy như Abbas 2021 dùng neural network phân loại mức nguy hiểm — nhưng chỉ phân loại trạng thái hiện tại, không dự báo. Hướng LSTM của Gambiroza 2020 chứng minh LSTM có thể học đặc tính quá độ của cảm biến MQ — đây là nền tảng lý thuyết của nhóm em. Cuối cùng là hướng Reinforcement Learning của Wei 2022 — nhưng dành cho pipeline công nghiệp, không phải nhà ở. Khoảng trống lớn nhất là: chưa có nghiên cứu nào kết hợp đồng thời cả ba yếu tố — dự báo LSTM, điều khiển RL, và pipeline streaming hoàn chỉnh cho nhà ở. Đây chính là chỗ đề tài của em đặt mình vào."

**Lưu ý:** không cần đọc từng bài báo. Nói khoảng 3 bài đại diện, rồi nhấn vào "khoảng trống".

---

## Slide 9 — Hướng tiếp cận của đề tài

> "Nhóm tiếp cận bài toán theo ba mũi tên. Mũi thứ nhất là LSTM Forecasting — thay vì phân loại trạng thái hiện tại, mô hình của em dự báo xác suất gas vượt 1000 ppm trong 5 phút tới, dựa trên cửa sổ 60 giây. Kết quả là một tín hiệu liên tục $p_{5\min}$ trong khoảng 0 đến 1, thay thế ngưỡng tĩnh nhị phân. Mũi thứ hai là PPO Reinforcement Learning — học chính sách chọn hành động tối ưu trong 4 hành động: không làm gì, cảnh báo, bật quạt, hoặc đóng van. Hàm reward cân bằng giữa hiệu quả can thiệp và chi phí false alarm. Mũi thứ ba là pipeline streaming hiện đại MQTT, Kafka, Spark — đảm bảo độ trễ end-to-end thực tế."

---

## Slide 10 — Mục tiêu đề tài (bảng 7 dòng)

> "Cụ thể, đề tài đặt ra 7 mục tiêu kỹ thuật. Em xin liệt kê nhanh: bộ mô phỏng vật lý có ground-truth tái tạo được; mô hình LSTM dự báo nhị phân; bộ điều khiển PPO 4 hành động; pipeline streaming độ trễ dưới 1 giây; tích hợp Telegram chatbot; phương pháp Oracle two-pass để đánh giá công bằng các bộ điều khiển; và toàn bộ hệ thống đóng gói trong Docker Compose 10 services."

---

# PHẦN 3 — TIẾN ĐỘ HIỆN TẠI

---

## Slide 11 — Section divider "03"

> "Bây giờ em xin trình bày phần ba — phần quan trọng nhất — về tiến độ hiện tại của đề tài."

---

## Slide 12 — Tiến độ tổng thể theo Gantt

> "Theo kế hoạch Gantt 15 tuần ban đầu, nhóm em đã hoàn thành toàn bộ 4 giai đoạn chính. Giai đoạn 1 phân tích và thiết kế kiến trúc 4-layer — hoàn thành 100%. Giai đoạn 2 triển khai IoT và Data Pipeline MQTT-Kafka-Spark — hoàn thành 100%. Giai đoạn 3 phát triển mô hình AI gồm LSTM và PPO — hoàn thành 100%. Giai đoạn 4 phát triển Application bao gồm Backend API, Dashboard Grafana, Telegram Bot — đạt 95%, còn tinh chỉnh demo cuối. Bản thảo LaTeX 5 chương, khoảng 1.770 dòng nội dung, cũng đạt 95%. Đặc biệt, trong đợt báo cáo này nhóm em đã bổ sung được hai phần quan trọng: đánh giá LSTM trên dữ liệu cảm biến thực Kaggle 132K — em sẽ trình bày kỹ ở phần sau; và bootstrap 95% CI cho tất cả chỉ số."

---

## Slide 13 — Kiến trúc hệ thống 4 lớp (HÌNH `architecture.png`)

**Cách giải thích hình:**

> "Đây là kiến trúc tổng thể của hệ thống, tổ chức theo mô hình IoT 4 lớp kinh điển. Em xin giải thích từ trái sang phải, hoặc từ dưới lên trên. Lớp dưới cùng là **Device Layer** — ESP32 gắn cảm biến MQ-135 đo gas và DHT22 đo nhiệt độ, độ ẩm. Lớp thứ hai là **Communication Layer** gồm Mosquitto MQTT Broker và MQTT-Kafka Bridge. Lớp thứ ba là **Processing Layer** — quan trọng nhất — bao gồm Apache Kafka cho streaming, Apache Spark Structured Streaming để xử lý micro-batch, mô hình LSTM Forecaster, mô hình PPO RL Controller, và InfluxDB để lưu chuỗi thời gian. Lớp trên cùng là **Application Layer** gồm Backend Node.js, Dashboard Grafana, và Telegram Bot. Toàn bộ luồng dữ liệu đi từ ESP32 qua MQTT, vào Kafka, được Spark đọc và đẩy qua LSTM/PPO, kết quả ghi vào InfluxDB và hiển thị trên Dashboard hoặc gửi cảnh báo qua Telegram. Độ trễ end-to-end median đo được khoảng 310 ms."

**Khi chỉ vào hình:** dùng laser pointer hoặc chuột — chỉ tuần tự ESP32 → MQTT → Kafka → Spark → ML → InfluxDB → Telegram.

---

## Slide 14 — Bộ mô phỏng vật lý trạng thái

> "Vì điều kiện phòng lab, nhóm em sử dụng bộ mô phỏng phần mềm thay cho phần cứng ESP32 thực tế trong quá trình huấn luyện. Bộ mô phỏng được xây dựng dựa trên một máy trạng thái 4 pha tham khảo từ tài liệu chuyên ngành. NORMAL — trạng thái nền với nồng độ kéo về 60 ppm cộng nhiễu Gauss. LEAK_SLOW — rò rỉ van chậm, gas tăng 5 ppm mỗi giây cộng nhiễu. LEAK_FAST — vỡ ống, gas tăng theo hàm mũ e mũ 0,04 nhân t. VENTILATING — sau khi đóng van hoặc bật quạt, gas giảm theo hàm e mũ trừ 0,03 nhân t. Toàn bộ chạy với seed cố định nên tái tạo 100%. Quan trọng nhất là bộ mô phỏng cung cấp ground-truth — gồm trường `_leak_state` và `_seconds_to_critical` — cho phép em thực hiện phương pháp đánh giá Oracle two-pass mà em sẽ giải thích sau."

---

## Slide 15 — Dữ liệu huấn luyện

> "Đây là bảng tổng kết các tập dữ liệu sử dụng. Với LSTM trên simulator: nhóm sinh 8 giờ dữ liệu tần số 1 Hz với seed 42, được 28.439 cửa sổ huấn luyện, tỷ lệ mẫu dương 26%. Chia chronological 80/20 — không xáo trộn — ra 22.751 mẫu train và 5.688 mẫu test. **Phần mới** mà em vừa bổ sung là đánh giá LSTM trên dataset thực **Kaggle Environmental Sensor Telemetry 132K**, gồm khoảng 405 nghìn mẫu từ 3 thiết bị Raspberry Pi gắn cảm biến MQ-2 và MQ-7, thu thập trong 7 ngày tháng 7 năm 2020. Sau khi build sliding window, em có 323.280 mẫu train và 80.821 mẫu test — gấp 14 lần kích thước test set simulator. Với PPO RL: 200.000 timesteps trên 4 môi trường song song. Với benchmark: 4 giờ × 3 seeds (42, 43, 44)."

---

## Slide 16 — Kiến trúc LSTM (HÌNH `lstm_arch.png`)

**Cách giải thích hình:**

> "Đây là sơ đồ khối của mô hình LSTM Forecaster. Đầu vào là một tensor 60 bước thời gian × 3 đặc trưng — gồm gas_ppm, nhiệt độ, và độ ẩm — đã chuẩn hoá về khoảng 0 đến 1. Tensor này đi qua một lớp LSTM với 32 đơn vị ẩn — đây là lớp cốt lõi học các phụ thuộc thời gian trong cửa sổ 60 giây. Sau LSTM là Dropout 0,2 để chống overfitting. Tiếp theo là một lớp Dense 16 đơn vị với activation ReLU. Cuối cùng là một lớp Dense 1 đơn vị với sigmoid để cho ra $p_{5\min}$ — xác suất gas vượt 1000 ppm trong 5 phút tới. Tổng số tham số khoảng 5.153 — rất nhỏ so với các mô hình deep learning thông thường, giúp huấn luyện nhanh trên CPU. Nhãn được sinh từ gas tương lai, không phải từ trạng thái hiện tại — đây là điểm quan trọng đảm bảo mô hình thực sự học dự báo chứ không phải phân loại tức thời."

---

## Slide 17 — Đường cong huấn luyện LSTM (HÌNH `lstm_training.png`)

**Cách giải thích hình:**

> "Hình này có hai biểu đồ. Bên trái là **loss** theo epoch — đường xanh là training loss, đường cam là validation loss. Cả hai cùng giảm từ khoảng 0,76 xuống 0,40 sau 15 epoch. Đường validation không vọt lên xa hơn training, nghĩa là **mô hình không bị overfit**. Bên phải là **accuracy** — training acc hội tụ về khoảng 92%, validation acc ổn định quanh 90%. Khoảng cách hẹp giữa train và val xác nhận một lần nữa là không overfit. Mô hình hội tụ tốt sau epoch 8 đến 10; các epoch sau cải thiện không đáng kể."

---

## Slide 18 — Ma trận nhầm lẫn LSTM Simulator (HÌNH `lstm_confusion_matrix.png`)

**Cách giải thích hình:**

> "Đây là ma trận nhầm lẫn (confusion matrix) của LSTM trên tập kiểm thử simulator. Trục dọc là nhãn thực — hàng trên là 'an toàn' (gas sẽ không vượt ngưỡng), hàng dưới là 'rò rỉ trong 5 phút'. Trục ngang là nhãn dự đoán của mô hình. Số trong mỗi ô là tỷ lệ chuẩn hóa theo hàng. Đọc hình: ô trên trái 0,99 nghĩa là 99% các mẫu thực-an-toàn được dự đoán đúng là an-toàn — đây là **specificity** rất cao. Ô trên phải 0,01 là tỷ lệ báo nhầm — chỉ 1%. Ô dưới trái 0,45 — đây là tỷ lệ bỏ sót, nghĩa là 45% các trường hợp thực sự sẽ nguy hiểm bị mô hình đánh dấu là an toàn. Ô dưới phải 0,55 là **recall** — tỷ lệ phát hiện đúng các trường hợp nguy hiểm."

---

## Slide 19 — Bảng kết quả LSTM Simulator

> "Quy ra số cụ thể: trên 5.688 mẫu kiểm thử, mô hình đạt Accuracy 89,98%, Precision rất cao 95,68%, Recall 55,15%, F1 69,97%. Có 664 True Positive, chỉ 30 False Positive, 4.454 True Negative, và 540 False Negative. Em xin nhấn mạnh: **Precision 95,68% là rất cao** — nghĩa là khi mô hình kêu, hơn 95% là kêu đúng, false alarm cực ít. Tuy nhiên Recall chỉ 55% — đây là điểm yếu. Lý do là phần lớn các False Negative tập trung ở giai đoạn đầu LEAK_SLOW khi xu hướng tăng chưa đủ rõ trong cửa sổ 60 giây. Đây là **giới hạn cố hữu** — không có chuyên gia nào dự đoán được leak khi nó còn chưa rõ ràng. Hướng cải thiện là hạ ngưỡng quyết định từ 0,5 xuống khoảng 0,35 — sẽ tăng Recall mạnh với chi phí Precision giảm không đáng kể."

---

## Slide 20 — Ma trận nhầm lẫn LSTM Kaggle (HÌNH `lstm_confusion_matrix_kaggle.png`) — PHẦN MỚI

**Cách giải thích hình:**

> "Đây là kết quả mới mà em vừa bổ sung trong đợt báo cáo này. Để giải quyết một phần hạn chế 'phụ thuộc vào simulator', nhóm em đã huấn luyện và đánh giá lại mô hình LSTM trên một tập dữ liệu **cảm biến IoT thực** — dataset Environmental Sensor Telemetry 132K trên Kaggle, gồm khoảng 405 nghìn mẫu từ 3 thiết bị Raspberry Pi gắn cảm biến MQ thực trong 7 ngày. Em dùng cùng kiến trúc LSTM, cùng quy tắc gán nhãn — nhưng ngưỡng 'danger' giờ là phân vị 95 của cột LPG vì đơn vị dataset khác. Tập kiểm thử có 80.821 cửa sổ — gấp 14 lần test set simulator. Ma trận nhầm lẫn trong hình: ô (0, 0) bằng 0,96 — gần như tất cả mẫu an toàn được dự đoán đúng. Ô (1, 1) bằng 0,87 — Recall đạt 87%, tức mô hình bắt được hầu hết các đỉnh nồng độ LPG cao trong tương lai."

---

## Slide 21 — So sánh Simulator vs Kaggle

> "Đây là bảng đối chiếu rất có ý nghĩa. So với simulator: Accuracy tăng từ 89,98 lên **95,56%**. Recall tăng vọt từ 55 lên **87,36%**. Tuy nhiên Precision **giảm** từ 95,68 xuống 21,15%. Vì sao? Trên simulator, các sự kiện rò rỉ có biên độ lớn và xu hướng rõ ràng — mô hình chỉ kêu khi rất chắc nên Precision cực cao. Trên Kaggle thực, 'đỉnh tương lai' định nghĩa bằng phân vị p95 nên bao gồm cả các dao động ngắn, dẫn đến nhiều dao động nhỏ bị xếp vào lớp dương — mô hình kêu nhiều hơn nhưng cũng kêu nhầm hơn. Quan trọng là tỷ lệ false alarm tuyệt đối vẫn rất thấp — chỉ khoảng 4% trên các mẫu âm. Khoảng tin cậy bootstrap 95%: Accuracy [95,4; 95,7] và Recall [85,2; 89,2] — rất hẹp do test set lớn. **Kết luận quan trọng nhất**: mô hình KHÔNG bị overfit vào simulator. Nếu nó overfit, áp lên dữ liệu Kaggle thực sẽ cho kết quả gần ngẫu nhiên — accuracy khoảng 50%. Thực tế Accuracy 95% và Recall 87% chứng tỏ tín hiệu xu hướng tăng nồng độ LPG mà LSTM đã học có tính tổng quát sang dữ liệu vật lý thực."

**Câu chốt quan trọng:** "Mô hình không bị overfit simulator — đây là điểm em muốn nhấn mạnh."

---

## Slide 22 — Kiến trúc PPO RL Controller (HÌNH `ppo_arch.png`)

**Cách giải thích hình:**

> "Đây là sơ đồ PPO RL Controller. Đầu vào là vector quan sát $s_t$ 8 chiều — bao gồm gas chuẩn hoá, nhiệt độ, độ ẩm, slope (đạo hàm bậc 1 của gas), $p_{5\min}$ từ LSTM, hai cờ trạng thái fan_on và valve_closed, và time_since_action. Vector này đi qua MLP có 2 lớp ẩn — mỗi lớp 64 đơn vị. Sau đó tách thành hai head: **policy head** cho ra phân phối xác suất trên 4 hành động — NO_OP, ALERT_USER, FAN_ON, CLOSE_VALVE; và **value head** ước lượng V(s) cho phép thuật toán PPO tính advantage. Tổng tham số khoảng 5.060 — tương đương kích thước LSTM. Hyper-parameter của PPO em dùng theo mặc định Stable-Baselines3: gamma 0,99, lambda GAE 0,95, clip epsilon 0,2, learning rate 3e-4, entropy coefficient 0,01."

**Điểm cần nói rõ:** "$p_{5\min}$ từ LSTM được đưa vào làm một feature của PPO — đây là **kiến trúc ghép tầng** mà em đã thiết kế."

---

## Slide 23 — Vòng tương tác RL (HÌNH `rl_loop.png`)

**Cách giải thích hình:**

> "Hình này minh hoạ vòng tương tác Reinforcement Learning. Agent quan sát trạng thái $s_t$ từ môi trường — bộ mô phỏng — và chọn hành động $a_t$. Môi trường thực thi hành động (vd. nếu đóng van thì simulator chuyển trạng thái sang VENTILATING) và trả về trạng thái mới $s_{t+1}$ cùng reward $r_t$. Reward được thiết kế theo logic: phạt nặng (-50) khi gas vượt ngưỡng nguy hiểm 1000 ppm, phạt nhẹ khi cảnh báo nhầm hoặc bật quạt sai, thưởng nhỏ khi hành động đúng. Agent dùng kinh nghiệm thu thập được để cập nhật policy theo thuật toán PPO clipped objective. Quá trình lặp lại 200.000 timesteps trên 4 môi trường song song — tức là 4 simulator chạy đồng thời, mỗi cái có thể đang ở pha khác nhau, giúp agent thấy đa dạng tình huống. Thời gian huấn luyện trên CPU khoảng 3 phút 30 giây, throughput 960 fps."

---

## Slide 24 — Reward curve PPO (HÌNH `ppo_reward.png`)

**Cách giải thích hình:**

> "Đây là đường cong reward trung bình của PPO qua 200 nghìn timesteps. Đường nhạt là reward thô từng episode, đường đậm là moving average. Reward dao động trong khoảng -3500 đến -1500 và **luôn âm** — chứ không vào vùng dương như kỳ vọng ban đầu. Em xin giải thích trung thực điểm này. Mỗi episode dài 1800 bước. Chỉ cần một sự kiện rò rỉ vượt 1000 ppm trong khoảng 30 giây mà agent chưa kịp đóng van là đã phạt -50 nhân 30 bằng -1500 điểm. Một episode 30 phút trung bình có 1 đến 2 sự kiện rò rỉ, mỗi sự kiện có pha 'ngộ độc' ngắn trước khi van đóng. Do đó reward âm **không** đồng nghĩa với chính sách kém — nó phản ánh đặc tính khắc nghiệt của hệ số phạt -50. Bằng chứng trực tiếp về chất lượng chính sách thực sự xuất hiện ở phần benchmark — peak gas trung bình của RL controller chỉ 63 ppm so với 1.508 ppm của baseline, chứng tỏ agent đã học được phản xạ đóng van rất sớm. Đường cong cho thấy reward ổn định dần — pha đầu dao động mạnh -3500 đến -2500, pha sau hội tụ về dải -2000 đến -1800."

---

## Slide 25 — Tổng hợp huấn luyện hai mô hình

> "Bảng này tổng hợp cả hai mô hình ở cùng một chỗ. Quan sát quan trọng: hai mô hình có kích thước **gần tương đương** (khoảng 5.000 tham số mỗi mô hình) — đây là minh chứng cho tính khả thi triển khai trên phần cứng phổ thông. Tổng thời gian huấn luyện chỉ vài phút trên CPU. Quan trọng hơn, hai mô hình đóng vai trò **bổ trợ chứ không cạnh tranh**: LSTM cung cấp một feature cao cấp ($p_{5\min}$) cho không gian trạng thái của PPO, trong khi PPO ra quyết định cuối cùng. Đây là kiến trúc ghép tầng — hierarchical."

---

## Slide 26 — Tiêu chí đánh giá

> "Trước khi vào benchmark, em xin giới thiệu 4 chỉ số đánh giá. Lead time — số giây cảnh báo trước thời điểm gas đạt ngưỡng — càng cao càng tốt. Miss rate — tỷ lệ sự kiện nguy hiểm bị bỏ sót — càng thấp càng tốt. Alarms per hour — số cảnh báo trong trạng thái bình thường, phản ánh phiền nhiễu — càng thấp càng tốt. Mean peak gas — nồng độ đỉnh trung bình — càng thấp càng tốt, nhưng chỉ những controller có hành động vật lý mới có thể giảm được. Bốn chỉ số này có **trade-off lẫn nhau** — không có một con số duy nhất nào đủ để đánh giá."

---

## Slide 27 — Benchmark 3 bộ điều khiển (giải thích Oracle two-pass)

> "Để so sánh công bằng giữa các bộ điều khiển, em áp dụng phương pháp **Oracle two-pass**. Lượt một: chạy bộ mô phỏng với seed cố định, không có controller can thiệp, ghi nhận thời điểm tự nhiên mà mỗi sự kiện rò rỉ sẽ đạt 1000 ppm — gọi là natural critical time. Lượt hai: chạy lại với CÙNG seed, lần này có controller hoạt động — vì cùng seed nên các sự kiện rò rỉ xảy ra tại đúng thời điểm như lượt một, và ghi nhận thời điểm controller hành động đầu tiên. Lead time bằng natural critical time trừ first action time. Phương pháp này đảm bảo cả ba controller được test trên cùng tập sự kiện. Em so sánh 3 bộ điều khiển: THRESHOLD — gas > 800 ppm; FORECASTER — $p_{5\min}$ > 0,5; và RL PPO. Chạy 3 seeds (42, 43, 44), mỗi seed 4 giờ mô phỏng."

---

## Slide 28 — Bảng kết quả benchmark

> "Đây là bảng kết quả chính của đề tài. THRESHOLD cho lead time 35 giây — đây là khoảng cách thuần vật lý giữa 800 và 1000 ppm; ngưỡng tĩnh không nhìn về tương lai. FORECASTER đạt 138 giây — **gấp 4 lần THRESHOLD** — đây là phần thưởng trực tiếp của tầng dự báo LSTM. RL đạt 1.803 giây — con số lớn vì agent học được phản xạ đóng van ngay khi vừa vào pha LEAK. Về peak gas: THRESHOLD và FORECASTER cùng cho 1.508 ppm — vì cả hai chỉ cảnh báo, không can thiệp vật lý. RL chỉ **63 ppm** — giảm **24 lần** so với hai baseline. Đây là **bằng chứng định lượng mạnh nhất** về giá trị của tầng RL. Về false alarm: RL chỉ 0,2/giờ — thấp hơn THRESHOLD (2,8) một bậc."

---

## Slide 29 — Trực quan hoá benchmark (HÌNH `benchmark_chart.png`)

**Cách giải thích hình:**

> "Hình này trực quan hoá bảng vừa nói. Bốn panel cho bốn chỉ số. Panel lead time dùng thang log để thể hiện được khoảng cách giữa các bậc — vì RL cao gấp 50 lần THRESHOLD. Panel miss rate cho thấy RL có miss rate cao nhất nhưng em sẽ giải thích lý do ở slide kế tiếp. Panel alarm/giờ cho thấy RL áp đảo — chỉ 0,2. Panel peak gas — đây là chỗ RL nhả ra sức mạnh thực sự — cột RL gần như chạm sàn so với hai cột 1.508 ppm của các baseline. Error bar là độ lệch chuẩn qua 3 seed."

---

## Slide 30 — Phân tích benchmark

> "Tóm lại, có ba điểm nổi bật. Thứ nhất, RL áp đảo về peak gas — giảm 24 lần — nhờ chủ động đóng van sớm. Thứ hai, FORECASTER tăng lead time gấp 4 lần so với THRESHOLD — đây là phần thưởng của tầng dự báo. Thứ ba, RL giảm false alarm xuống mức thấp nhất 0,2/giờ. Một điểm cần thừa nhận trung thực: **miss rate 15% của RL** là artifact của benchmark — state `valve_closed` không reset giữa các leak liên tiếp. Em đã kiểm chứng bằng benchmark con đơn-leak — TC-Slow và TC-Fast — cho miss rate 0%. Kết luận: hai mô hình bổ sung lẫn nhau — LSTM cảnh báo sớm, PPO can thiệp vật lý quyết liệt."

---

## Slide 31 — Benchmark theo kịch bản con (HÌNH `scenarios_chart.png`)

**Cách giải thích hình:**

> "Để bóc tách hành vi của 3 controllers theo từng loại rò rỉ, em làm thêm một bộ benchmark theo 3 kịch bản con — TC-Idle là 1 giờ thuần NORMAL, TC-Slow là LEAK_SLOW deterministic, TC-Fast là LEAK_FAST. Hình này có 4 panel — 4 chỉ số — mỗi panel có 3 cụm cột — 3 kịch bản — mỗi cụm 3 cột — 3 controllers. Quan sát rõ nhất ở panel peak gas (cuối): RL duy trì peak gas khoảng 60 ppm bất kể loại leak, trong khi 2 baseline còn lại để gas leo đến đỉnh tự nhiên 1.269 ppm với LEAK_SLOW hoặc tới sát trần saturation 2.000 ppm với LEAK_FAST. Lead time của FORECASTER và RL trong TC-Slow gấp 4,6 lần THRESHOLD."

---

## Slide 32 — Bảng kịch bản con

> "Bảng tóm tắt. Trong TC-Slow, peak gas của RL là 60 ppm trong khi 2 baseline là 1.269. Trong TC-Fast, RL vẫn 60 ppm trong khi 2 baseline tới 2.000. Trong TC-Idle, false alarm của RL ở mức 1/giờ — giữa THRESHOLD (0) và FORECASTER (2). Kết luận quan trọng: RL duy trì peak gas độc lập tốc độ leak — đây là **minh chứng giá trị nhất quán** của tầng điều khiển vật lý."

---

## Slide 33 — Độ trễ end-to-end

> "Bảng này phân tích độ trễ từng đoạn xử lý. Hai thành phần em đo trực tiếp bằng `time.perf_counter` là LSTM và RL inference. Các thành phần truyền thông em ước lượng từ tài liệu broker. Điểm phát hiện đáng chú ý: **LSTM inference chiếm 68 ms** — thành phần tốn thời gian nhất trong toàn pipeline. Đây là chi phí của TensorFlow trên CPU khi gọi `model.predict()` cho từng mẫu — phần lớn dùng cho dispatch graph chứ không phải compute thuần. RL inference chỉ 0,5 ms — không phải nút thắt. Tổng end-to-end median khoảng 310 ms — đáp ứng yêu cầu thời gian thực mềm dưới 1 giây."

---

## Slide 34 — Tích hợp Telegram chatbot

> "Để cảnh báo người dùng, em tích hợp Telegram bot với hai kênh kích hoạt độc lập theo nguyên tắc defense in depth. Kênh thứ nhất là event-driven — backend consume topic Kafka `gas.alert.events` và gọi telegramService.notifyAlert(). Kênh thứ hai là polling realtime — một worker chạy mỗi 2-3 giây đọc reading mới nhất từ InfluxDB và gửi alert nếu đạt ngưỡng. Hai kênh độc lập nên dù Kafka tạm gián đoạn, kênh polling vẫn cảnh báo được. Để tránh alert fatigue, em áp dụng 3 bộ lọc: risk_score phải ≥ 0,7; risk_label phải thuộc ALERT hoặc CRITICAL; và cooldown 60 giây mỗi khoá. Tin Telegram gồm cả risk_score, gas hiện tại, và rl_action — nên người dùng biết hệ thống đã làm gì."

---

## Slide 35 — Triển khai hạ tầng

> "Toàn bộ hệ thống đóng gói trong Docker Compose với 10 services — Mosquitto, MQTT-Kafka bridge, Kafka, Spark, ML services, InfluxDB, Backend API, Frontend dashboard, Telegram bot — khởi động bằng một lệnh duy nhất `docker compose up`. Tài nguyên: 5% CPU và 2 GB RAM tổng cộng cho 1 thiết bị, 1 Hz. Hệ thống hỗ trợ horizontal scaling qua Kafka partition và Spark executor."

---

## Slide 36 — Đóng góp kỹ thuật

> "Tóm tắt 8 đóng góp chính: bộ mô phỏng vật lý trạng thái tái tạo được; LSTM Forecasting thay thế classification trạng thái; PPO Controller đa hành động; pipeline streaming độ trễ dưới 310 ms; Telegram chatbot defense-in-depth; phương pháp Oracle two-pass đánh giá công bằng; Docker Compose 10 services tái tạo bằng 1 lệnh; và đặc biệt — đánh giá trên dữ liệu thực Kaggle 132K để giảm sim-to-real gap."

---

## Slide 37 — Hạn chế

> "Em xin trình bày các hạn chế trung thực. Thứ nhất, PPO vẫn phụ thuộc vào bộ mô phỏng — vì RL cần môi trường tương tác có ground-truth — chưa thay được bằng dataset thực. Tuy nhiên LSTM đã được giảm thiểu bằng đánh giá Kaggle 132K. Thứ hai, phạm vi benchmark còn hẹp — chỉ 3 seeds × 4 giờ — std lớn so với mean cho miss_rate. Thứ ba, chưa so sánh với Transformer-based time series như TFT hay PatchTST. Thứ tư, hàm reward chưa tối ưu — hệ số phạt -50 chiếm tỷ trọng quá lớn. Thứ năm, chưa triển khai trên phần cứng thực ESP32."

---

## Slide 38 — Công việc tiếp theo

> "Trong thời gian tới, nhóm em sẽ: hoàn thiện bản thảo LaTeX, đóng gói video demo end-to-end, chuẩn bị slides bảo vệ; thử nghiệm phần cứng thực ESP32 + cảm biến MQ-2/MQ-135; mở rộng benchmark lên 10 seeds × 24 giờ để siết khoảng tin cậy; và thực hiện reward shaping — chuẩn hoá VecNormalize, grid search hệ số reward."

---

## Slide 39 — Tham khảo

> "Đây là một số tài liệu tham khảo chính: Gambiroza 2020 về LSTM transient của cảm biến MQ; Stafford 2020 về dataset Kaggle Environmental Sensor 132K; Schulman 2017 về thuật toán PPO; Gymnasium 2023; Wei 2022; và Saranya 2023."

---

## Slide 40 — Cảm ơn

> "Em xin chân thành cảm ơn các thầy đã lắng nghe. Em xin được tiếp nhận câu hỏi và góp ý từ thầy."

---

# DỰ KIẾN CÂU HỎI VÀ CÁCH TRẢ LỜI

### Q1: "Tại sao chọn LSTM mà không chọn Transformer/GRU?"
> "LSTM phù hợp với chuỗi thời gian ngắn (60 bước) và đặc biệt nhỏ gọn (~5.000 tham số) — đáp ứng yêu cầu inference dưới 100 ms trên CPU phổ thông. Transformer-based model như TFT hay PatchTST có thể cho kết quả tốt hơn, em đã đề cập trong phần hướng phát triển ngắn hạn. GRU là một lựa chọn thay thế tương đương nhưng không có lợi thế rõ ràng cho window 60s."

### Q2: "Tại sao không dùng phần cứng ESP32 thực?"
> "Trong giai đoạn huấn luyện, em cần ground-truth chính xác để đánh giá Oracle two-pass — bộ mô phỏng cho phép điều này còn cảm biến thực thì không. Tuy nhiên em đã giảm thiểu sim-to-real gap bằng đánh giá LSTM trên dataset cảm biến thực Kaggle. Triển khai trên ESP32 là hướng phát triển ngắn hạn ưu tiên số một."

### Q3: "Recall LSTM chỉ 55% trên simulator — có phải mô hình kém?"
> "Recall 55% là giới hạn cố hữu của bài toán — không có cách nào dự đoán được leak khi nó còn chưa rõ xu hướng trong 60 giây. Đây là điểm em đã giải thích chi tiết trong báo cáo. Hơn nữa, trên dữ liệu Kaggle thực Recall đạt 87% — chứng tỏ tín hiệu mô hình đã học có tính tổng quát."

### Q4: "Reward âm — vậy huấn luyện RL có thành công không?"
> "Reward âm phản ánh đặc tính khắc nghiệt của hệ số phạt -50, không phản ánh chất lượng policy. Bằng chứng policy tốt là peak gas chỉ 63 ppm so với baseline 1.508 ppm — giảm 24 lần. Hướng cải tiến đã đề xuất là chuẩn hoá reward về [-1, 0] hoặc dùng VecNormalize."

### Q5: "Miss rate 15% của RL có phải là vấn đề an toàn?"
> "Đây là artifact của benchmark — state `valve_closed` không reset giữa các leak liên tiếp. Em đã kiểm chứng bằng benchmark đơn-leak (TC-Slow, TC-Fast) cho miss rate 0%. Trong sản phẩm thực sẽ thêm option `--reset-per-leak` để fix triệt để."

### Q6: "Test set 5.688 mẫu có quá nhỏ?"
> "Trên simulator thì có một phần đúng — về mặt thống kê CI hẹp nhưng số sự kiện rò rỉ độc lập chỉ khoảng 5. Em đã bổ sung đánh giá trên Kaggle 80.821 mẫu — gấp 14 lần — với bootstrap 95% CI, cho khoảng tin cậy rất hẹp (Recall [85,2; 89,2])."

### Q7: "Phân biệt forecasting vs classification — sao quan trọng?"
> "Classification trạng thái hiện tại chỉ trả lời 'gas đang cao hay thấp' — tương đương ngưỡng tĩnh. Forecasting trả lời 'gas SẼ cao trong 5 phút tới' — cho người dùng thời gian phản ứng. Đây là điểm khác biệt cốt lõi với các nghiên cứu trước như Abbas 2021."

---

# CHECKLIST TRƯỚC KHI BÁO CÁO

- [ ] Mở sẵn file PDF slides + file LaTeX bản nháp (phòng khi thầy yêu cầu xem chương cụ thể).
- [ ] Có sẵn laptop, sạc, adapter HDMI.
- [ ] Test laser pointer / chuột với máy chiếu trước 5 phút.
- [ ] Có sẵn demo video (sensor → cảnh báo Telegram) — backup nếu thầy muốn xem.
- [ ] In bản tóm tắt 1 trang để thầy đối chiếu.
- [ ] Đến sớm 10 phút, set up máy chiếu, mở slide 1 sẵn.

---

# LƯU Ý KHI TRÌNH BÀY

1. **Tốc độ**: Không quá 60 giây/slide trừ các slide có hình quan trọng (kiến trúc, confusion matrix Kaggle).
2. **Giao tiếp mắt**: Nhìn thầy chứ không nhìn slide.
3. **Tone**: Tự tin nhưng khiêm tốn — nói "em đã làm được X, còn Y là hạn chế em nhận thấy" thay vì "X tuyệt vời, Y không quan trọng".
4. **Khi gặp câu hỏi khó**: Đừng cố trả lời nếu không chắc — nói "Em chưa khảo sát kỹ điểm này, em sẽ nghiên cứu thêm và báo cáo lại thầy ở buổi sau" — thầy sẽ đánh giá cao sự trung thực hơn là câu trả lời mơ hồ.
5. **Câu chốt cần nhớ**: Mỗi phần kết bằng 1 câu chốt mạnh — vd. cuối phần LSTM: "Mô hình không bị overfit simulator"; cuối phần benchmark: "RL giảm peak gas 24 lần"; cuối phần Telegram: "Defense in depth qua 2 kênh".
