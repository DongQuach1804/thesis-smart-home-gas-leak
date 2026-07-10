# MQTT -> Kafka -> Spark Pipeline Testcases

Nhom testcase nay dung de chung minh Kafka la thanh phan can thiet trong pipeline, khong phai thanh phan du thua. Cac testcase kiem tra duong di thuc te cua du lieu:

```text
MQTT Publisher
  -> Mosquitto MQTT Broker
  -> MQTT-Kafka Bridge
  -> Kafka topic gas.raw.sensor
  -> Spark Streaming
  -> InfluxDB measurement gas_reading
```

Script chay:

```powershell
.\scripts\test\run-kafka-pipeline-tests.ps1
```

Mac dinh script dung cau hinh demo de khong chay qua lau. Khi can chay dung quy mo bao cao, co the truyen tham so:

```powershell
.\scripts\test\run-kafka-pipeline-tests.ps1 -P1Messages 1000 -P1Rate 1
.\scripts\test\run-kafka-pipeline-tests.ps1 -P2Messages 10000 -P2Rate 50
.\scripts\test\run-kafka-pipeline-tests.ps1 -P3Messages 50000 -P3Rate 500 -SparkTimeoutSec 900
```

Luu y: trong project hien tai, Spark doc Kafka voi `SPARK_MAX_OFFSETS_PER_TRIGGER=20` va trigger moi 5 giay. Vi vay khi burst data lon, Kafka co the nhan rat nhanh, con Spark se xu ly dan. Day chinh la ly do Kafka can thiet nhu mot streaming buffer.

## Metric Duoc Ghi Nhan

| Metric | Y nghia |
|---|---|
| `sent` | So message da publish vao MQTT |
| `mqtt_rate` | Toc do publish MQTT quan sat duoc |
| `kafka_received` | So message Kafka nhan duoc, tinh bang topic offset delta |
| `kafka_success` | `kafka_received / sent` |
| `spark_processed` | So message Spark da xu ly va ghi vao InfluxDB |
| `spark_success` | `spark_processed / sent` |
| `avg_latency_ms` | Do tre trung binh tu `event_ts` den luc Spark xu ly |
| `max_latency_ms` | Do tre lon nhat tu `event_ts` den luc Spark xu ly |

Dieu kien pass mac dinh:

```text
kafka_success >= 98%
spark_success >= 20%
Bridge, Kafka, Spark khong bi crash
```

Ly do `spark_success` mac dinh khong dat 90%: muc tieu cua nhom testcase nay la kiem tra integration va chung minh Kafka lam buffer cho pipeline streaming. Kafka co the nhan nhanh hon toc do Spark xu ly. Vi vay ket qua `PASSED` mac dinh nen duoc hieu la pipeline hoat dong on dinh va Spark co xu ly du lieu, khong phai la Spark da drain toan bo backlog duoi tai cao.

Neu muon dung testcase nhu benchmark throughput nghiem ngat, nen chay:

```powershell
.\scripts\test\run-kafka-pipeline-tests.ps1 -MinSparkSuccessRate 0.9 -SparkTimeoutSec 900
```

Hoac tang cau hinh Spark:

```text
SPARK_MAX_OFFSETS_PER_TRIGGER
```

## TC-P1: Kiem Tra Truyen Du Lieu Co Ban

**Ngu canh:** Mot sensor gui du lieu o toc do thap, mo phong thiet bi IoT hoat dong binh thuong.

**Cau hinh goi y cho bao cao:**

```text
So ban tin: 1000
Toc do gui: 1 message/giay
MQTT topic: sensors/gas
Kafka topic: gas.raw.sensor
```

**Muc tieu:** Kiem tra pipeline co ban co hoat dong dung khong.

**Ket qua mong doi:**

```text
MQTT publish thanh cong
Kafka offset gas.raw.sensor tang
Spark ghi du lieu vao InfluxDB measurement gas_reading
kafka_success >= 98%
spark_success >= 20% trong thoi gian test mac dinh
```

**Y nghia:** Chung minh du lieu sensor di duoc qua toan bo luong MQTT -> Kafka -> Spark.

## TC-P2: Kiem Tra Tai Trung Binh

**Ngu canh:** Mo phong nhieu cam bien gui du lieu lien tuc trong thoi gian ngan.

**Cau hinh goi y cho bao cao:**

```text
So ban tin: 10000
Toc do gui: 10-50 message/giay
```

**Muc tieu:** Danh gia MQTT-Kafka Bridge va Kafka co xu ly on dinh khi du lieu tang khong.

**Ket qua mong doi:**

```text
Kafka nhan du message voi success rate cao
Spark van xu ly stream va ghi InfluxDB
Pipeline khong crash
```

**Chi so can ghi:**

```text
Throughput
Kafka success rate
Spark success rate
Average latency
Maximum latency
```

## TC-P3: Kiem Tra Tai Cao / Burst Data

**Ngu canh:** Mo phong nhieu du lieu do vao cung luc, vi du nhieu cam bien gui dong thoi hoac he thong sinh du lieu nhanh trong thoi gian ngan.

**Cau hinh goi y cho bao cao:**

```text
So ban tin: 50000
Toc do gui: 100-500 message/giay
Thoi gian test: 3-5 phut hoac tuy cau hinh may
```

**Muc tieu:** Kiem tra Kafka co dong vai tro buffer tot khong khi toc do du lieu tang cao.

**Ket qua mong doi:**

```text
Kafka van luu duoc message vao topic
Spark co the xu ly dan tu topic Kafka
Pipeline khong crash
```

**Giai thich quan trong:** Neu Kafka nhan du message nhung Spark chua xu ly het ngay, day khong phai loi. Day la hanh vi dung cua kien truc streaming: Kafka giu message trong topic de consumer xu ly theo toc do cua no. Khi trinh bay, nen noi ro Spark xu ly theo micro-batch/backpressure nen can them thoi gian hoac tang cau hinh de dat ti le xu ly cao hon.

## TC-P4: Kiem Tra Nhieu Topic

**Ngu canh:** He thong khong chi co du lieu raw sensor ma con co cac luong su kien sau xu ly.

**Topic trong project:**

| Topic | Vai tro |
|---|---|
| `gas.raw.sensor` | Du lieu cam bien tho tu MQTT-Kafka Bridge |
| `gas.alert.events` | Su kien canh bao do Spark/LSTM sinh ra |
| `gas.action.events` | Hanh dong dieu khien do Spark/RL sinh ra |

**Muc tieu:** Kiem tra viec tach luong du lieu bang Kafka topic.

**Ket qua mong doi:**

```text
gas.raw.sensor tang offset khi co sensor message
gas.alert.events tang offset khi co canh bao
gas.action.events tang offset khi RL chon action
```

**Y nghia:** Chung minh Kafka giup tach raw data, alert event va action event thanh cac luong rieng, de backend/dashboard/Telegram/actuator co the subscribe dung luong can thiet.

**Luu y:** Trong script hien tai, `alert_topic_delta` va `action_topic_delta` la offset delta cua toan topic, chua loc rieng theo `device_id`. Vi vay TC-P4 chung minh cac topic alert/action co hoat dong, chua dung de ket luan chinh xac 5 raw message tao ra bao nhieu alert/action.

## TC-P5: Kiem Tra Du Lieu Loi

**Ngu canh:** Publisher co tinh gui mot so ban tin sai dinh dang.

**Vi du du lieu loi:**

```text
invalid json data
{bad-json
{"gas":null,"temp":30,"humidity":60}
```

**Muc tieu:** Kiem tra Bridge/Spark co bi crash khi gap du lieu loi khong.

**Ket qua mong doi:**

```text
Message sai JSON khong duoc dua vao Kafka raw topic
Message JSON dung cu phap nhung sai schema co the vao Kafka, sau do bi Spark loc bo
MQTT-Kafka Bridge van running
Spark processing-engine van running
Sau du lieu loi, gui message hop le thi pipeline van xu ly binh thuong
```

**Chi so can ghi:**

```text
invalid_sent
invalid_kafka_delta
bridge_running
spark_running
recovery_kafka_delta
recovery_spark
```

Neu `invalid_kafka_delta = 1` van co the chap nhan duoc, vi message JSON dung cu phap nhung sai schema co the vao Kafka va bi Spark loc bo. Tieu chi quan trong cua TC-P5 la bridge/Spark khong crash va pipeline phuc hoi voi message hop le sau do.

## Bang Tong Hop Cho Slide

| Testcase | Muc tieu | Metric chinh | Tieu chi pass |
|---|---|---|---|
| TC-P1 | Truyen du lieu co ban | sent, kafka_received, spark_processed | Du lieu di qua MQTT -> Kafka -> Spark |
| TC-P2 | Tai trung binh | throughput, success rate, latency | Kafka/Spark xu ly on dinh |
| TC-P3 | Burst data | peak throughput, Kafka offset, Spark backlog | Kafka lam buffer, pipeline khong crash |
| TC-P4 | Nhieu topic | raw_delta, alert_delta, action_delta | Cac topic raw/alert/action deu hoat dong |
| TC-P5 | Du lieu loi | invalid_kafka_delta, recovery_spark | Du lieu loi khong lam sap pipeline |

## Ket Luan

Neu cac testcase TC-P1 den TC-P5 deu dat, co the ket luan Kafka duoc su dung hop ly trong he thong. Kafka giup tach roi thiet bi IoT voi Spark Streaming, nhan va luu message khi du lieu tang dot bien, phan tach nhieu luong du lieu bang topic, va tang do ben cua pipeline khi xuat hien du lieu loi.

Doan dien dat goi y cho bao cao:

```text
Ket qua kiem thu cho thay pipeline MQTT-Kafka-Spark hoat dong on dinh. Kafka tiep nhan day du du lieu trong ca ba muc tai, dat ti le 100%. Spark xu ly thanh cong du lieu va ghi ket qua vao InfluxDB, tuy nhien o tai trung binh va burst, ti le xu ly giam do co che micro-batch va gioi han maxOffsetsPerTrigger. Dieu nay cho thay he thong dam bao tinh dung cua luong du lieu, dong thoi can toi uu them cau hinh Spark de cai thien throughput trong cac kich ban tai cao.
```
