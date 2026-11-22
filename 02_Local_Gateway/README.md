# BÁO CÁO KỸ THUẬT VÀ TÀI LIỆU DỰ ÁN: HỆ THỐNG BÁO CHÁY THÔNG MINH
## LOCAL IOT GATEWAY VÀ NỀN TẢNG COREIOT (TIÊU CHÍ T08, T10)

ĐẠI HỌC QUỐC GIA TP. HỒ CHÍ MINH - TRƯỜNG ĐẠI HỌC BÁCH KHOA  
KHOA KHOA HỌC VÀ KỸ THUẬT MÁY TÍNH  
MÔN HỌC: INTERNET OF THINGS (IoT) - HK261

---

## 1. TỔNG QUAN HỆ THỐNG

Dự án hiện thực trọn vẹn kiến trúc **Local IoT Edge Gateway** và hệ sinh thái cảm biến - cơ cấu chấp hành phục vụ bài toán **Hệ thống Báo cháy và Cứu hộ Khẩn cấp**. Dự án đáp ứng các tiêu chuẩn kỹ thuật trọng yếu của môn học:
- **T08 (IoT Gateway cục bộ trên PC/Raspberry Pi):** Tiếp nhận dữ liệu từ các End Node (mô phỏng hoặc mạch thật ESP32-S3 YoloUNO qua UART), đồng bộ dữ liệu Telemetry lên đám mây CoreIOT (ThingsBoard) qua giao thức MQTT QoS 1, tiếp nhận lệnh điều khiển RPC hai chiều từ Cloud và điều phối xuống mạng cục bộ.
- **T10 (Giao diện giám sát - điều khiển trên IoT Gateway local):** Xây dựng Local Monitor UI chuẩn giao diện công nghiệp Keen Dashboards (phục vụ tại cổng mạng `http://localhost:5050`), hiển thị thông số thời gian thực, cảnh báo cháy và cung cấp bảng điều khiển cưỡng bức khẩn cấp tại trạm (Local Survivability).

---

## 2. PHÂN TÍCH HỆ THỐNG (SYSTEM ANALYSIS)

Dựa trên cấu trúc chuẩn của báo cáo môn học (Chương 2), hệ thống được phân tích và bóc tách kiến trúc theo các phân lớp chức năng rõ ràng giữa **Lớp IoT Gateway cục bộ** và **Lớp Đám mây CoreIOT**.

### 2.1. Kiến trúc tổng thể hệ thống

Hệ thống được thiết kế theo mô hình lai (Hybrid Multi-Tier Architecture), kết hợp tính linh hoạt của mạng cảm biến trường và khả năng xử lý phân tán tại biên (Edge Computing):

```
+---------------------------------------------------------------------------------+
|                             LỚP THIẾT BỊ ĐẦU CUỐI (END NODES)                  |
|  - Cảm biến Khói (Smoke Sensor) & Cảm biến Lửa (Optical Flame Sensor)           |
|  - Cơ cấu chấp hành: Cửa ngăn khói (Servo), Còi báo (Buzzer), Đèn cảnh báo (LED)|
|  - Nhóm 1: Virtual Node (SimulationNode.py) qua giao tiếp UDP Socket (5000/5001)|
|  - Nhóm 2: Mạch phần cứng thật YoloUNO ESP32-S3 qua kết nối UART Serial (115200)|
+---------------------------------------------------------------------------------+
                                        |
                                        v
+---------------------------------------------------------------------------------+
|                         LỚP IOT GATEWAY CỤC BỘ (T08 & T10)                      |
|  - Nền tảng: Máy tính nhúng PC hoặc Raspberry Pi (Local Gateway Engine)         |
|  - Adapter truyền thông: HardwareSerialAdapter (UART) & UDP Inbound Listener    |
|  - Hàng đợi lệnh bất đồng bộ: Asynchronous Command Queue (queue.Queue)          |
|  - Cơ chế đệm ngoại tuyến: OfflineBufferRepository (SQLite Write-Ahead Logging) |
|  - Giao diện trạm cục bộ: Embedded Web Monitor (Keen Dashboards - Port 5050)   |
+---------------------------------------------------------------------------------+
                                        |
                         MQTTS (v1/devices/me/telemetry)
                         RPC Sub (v1/devices/me/rpc/request/+)
                                        v
+---------------------------------------------------------------------------------+
|                         LỚP ĐÁM MÂY COREIOT (CLOUD PLATFORM)                    |
|  - Máy chủ CoreIOT Cloud: app.coreiot.io:1883 (ThingsBoard Enterprise Engine)   |
|  - Quản lý phiên và xác thực: Access Token (i2tchqq1390qcxhun4zr)               |
|  - Lưu trữ dữ liệu chuỗi thời gian: Timeseries Database                         |
|  - Xử lý thông minh: RuleChain Engine (Phát hiện khói/lửa vượt ngưỡng)          |
|  - Điều khiển từ xa & Giám sát tập trung: Web Dashboard & Cloud RPC API         |
+---------------------------------------------------------------------------------+
```

### 2.2. Phân rã chức năng hệ thống

Hệ thống báo cháy được phân rã thành các luồng xử lý nghiệp vụ chính:
1. **Thu thập dữ liệu môi trường (Sensing):** Đọc định kỳ nồng độ khói (`smoke` theo ppm) và trạng thái bức xạ quang học của ngọn lửa (`flame` theo bit logic 0/1).
2. **Xử lý sơ bộ và đệm dữ liệu tại biên (Edge Ingestion & Buffering):** Đóng gói khung truyền JSON, kiểm tra tính hợp lệ của dữ liệu, ghi lập tức vào cơ sở dữ liệu đệm SQLite nội bộ để chống mất dữ liệu khi mất kết nối mạng.
3. **Đồng bộ hóa đám mây (Cloud Synchronization):** Kết nối liên tục qua MQTT Client; khi đường truyền khả dụng, luồng nền tự động đẩy dữ liệu lên CoreIOT; khi mạng phục hồi sau sự cố, dữ liệu tồn đọng trong đệm được đồng bộ theo cơ chế FIFO (First-In, First-Out).
4. **Phân phối lệnh điều khiển (Actuator Dispatching):** Tiếp nhận lệnh thay đổi trạng thái từ hai nguồn: Lệnh RPC từ đám mây (CoreIOT RuleChain/Dashboard) hoặc Lệnh cưỡng bức từ giao diện Web trạm cục bộ (Local Override), đưa vào hàng đợi không nghẽn và phát xuống vi điều khiển qua UART/UDP.

### 2.3. Phân lớp tính năng chi tiết: IoT Gateway vs Đám mây CoreIOT

Sự phân định ranh giới chức năng giữa trạm biên và đám mây được tối ưu hóa theo nguyên lý độ trễ thấp và độ sẵn sàng cao:

#### A. Phân lớp tính năng Lớp IoT Gateway Cục Bộ (T08, T10)
- **Tính độc lập sống còn (Local Survivability):** Trong các kịch bản hỏa hoạn thực tế, đường truyền cáp quang Internet hoặc sóng viễn thông thường bị gián đoạn đầu tiên do cháy nổ. Local Gateway đảm bảo khả năng giám sát và điều khiển trực tiếp các cơ cấu chấp hành tại chỗ (đóng cửa ngăn khói, kích hoạt còi hú) mà không cần chờ đợi phản hồi từ Cloud.
- **Trí tuệ nhân tạo phát hiện bất thường tại biên (Edge ML Isolation Forest):** Tích hợp thuật toán học máy không giám sát Isolation Forest (`scikit-learn`) ngay tại Gateway để liên tục phân tích vectơ 3 chiều `[smoke, temperature, flame]`. Tính toán chỉ số dị biệt chuẩn hóa `anomaly_score` (0.0 đến 1.0) và cờ `is_anomaly` theo thời gian thực, ngăn chặn ngộ độc dữ liệu nền (baseline poisoning) và cảnh báo sớm các vụ cháy tiềm ẩn hoặc lỗi hỏng cảm biến trước khi vượt ngưỡng cứng.
- **Lưu trữ đệm chống mất mát dữ liệu (Offline Store-and-Forward):** Sử dụng cơ chế SQLite ở chế độ Write-Ahead Logging (WAL) với các chỉ mục tự tăng. Mọi bản tin telemetry nhận từ End Node đều được ghi nhận trạng thái `synced = 0`. Luồng `Sync Worker` định kỳ quét và phát hành lại (publish) lên CoreIOT qua giao thức MQTT QoS 1. Sau khi nhận được mã xác nhận từ Broker, trạng thái được cập nhật thành `synced = 1`.
- **Hàng đợi điều khiển bất đồng bộ (Non-blocking Command Queue):** Tách biệt luồng nhận bản tin MQTT (`on_message` callback) ra khỏi luồng ghi Serial UART / phát UDP. Điều này triệt tiêu hoàn toàn nguy cơ đóng băng luồng mạng chính của MQTT Client, tránh tình trạng bị ngắt kết nối do quá hạn KeepAlive.
- **Trạm giám sát SCADA cục bộ (Local SCADA Web Monitor):** Cung cấp giao diện trực quan chuẩn Keen Dashboards không phụ thuộc vào Internet, cập nhật dữ liệu liên tục với độ trễ nội mạng dưới 100ms.

#### B. Phân lớp tính năng Lớp Đám Mây CoreIOT (ThingsBoard Platform)
- **Lưu trữ chuỗi thời gian tập trung (Centralized Timeseries Storage):** Ghi nhận toàn bộ diễn tiến nồng độ khói và bức xạ lửa trong suốt chu kỳ hoạt động của hệ thống, phục vụ công tác điều tra nguyên nhân cháy và phân tích độ tin cậy của cảm biến.
- **Bộ máy quy tắc thông minh (RuleChain Processing):** Cấu hình các khối xử lý logic nghiệp vụ: khi `smoke > 60.0 ppm` hoặc `flame == 1`, RuleChain tự động khởi tạo lệnh RPC `setServo(90)` để đóng cửa thoát hiểm và gửi tin nhắn cảnh báo notification (SMS, Email, Telegram) đến ban quản lý tòa nhà.
- **Bảng điều khiển quản trị trung tâm (Enterprise Dashboard):** Giám sát đồng thời nhiều trạm Gateway phân tán trên cùng một giao diện bản đồ địa lý hoặc sơ đồ mặt bằng kiến trúc.

### 2.4. Bảng ánh xạ tính năng và yếu tố công nghệ (Criteria Mapping)

| Mã tiêu chí | Tên yếu tố công nghệ | Hiện thực trong dự án | Vị trí mã nguồn |
| :--- | :--- | :--- | :--- |
| **T08** | IoT Gateway hiện thực trên PC/Raspberry Pi: tổng hợp dữ liệu, gửi lên CoreIOT, nhận lệnh RPC và phân phối thiết bị | Hoàn thành trọn vẹn cả hai nhóm: Nhóm 1 nhận UDP Socket; Nhóm 2 nhận Serial UART từ ESP32-S3 YoloUNO. Kết nối MQTT CoreIOT QoS 1, đệm SQLite WAL. | `LocalGateway_Simulation.py`<br>`LocalGateway.py` |
| **T10** | Giao diện giám sát - điều khiển trên IoT Gateway local | Xây dựng máy chủ Web nhúng (Port 5050) giao diện chuẩn Keen Dashboards, cung cấp REST API telemetry và nút điều khiển trực tiếp khẩn cấp tại trạm. | `gateway_infrastructure.py` |

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN

Dự án được phân chia thành 4 phân hệ mô-đun rõ ràng, kèm tệp điều phối hệ thống duy nhất tại thư mục gốc:

```text
c:/261/IOT/BTL_IOT/
|-- start_system.py                     # [ĐIỂM KHỞI CHẠY DUY NHẤT] Launcher điều phối toàn bộ hệ thống
|-- test_system.py                      # Bộ kiểm thử tự động toàn diện (6 bài test chuẩn công nghiệp)
|-- README.md                           # Tài liệu kỹ thuật và hướng dẫn sử dụng hệ thống
|-- gateway_simulation_buffer.db        # Cơ sở dữ liệu đệm ngoại tuyến SQLite WAL (tự động khởi tạo)
|
|-- simulation/                         # [NHÓM 1: MÔ PHỎNG ẢO]
|   |-- LocalGateway_Simulation.py      # Gateway tiếp nhận dữ liệu mô phỏng qua UDP Socket (Port 5000)
|   |-- SimulationNode.py               # Virtual End Node ESP32-S3 phát sinh nồng độ khói và ngọn lửa
|   `-- __init__.py                     # Package marker
|
|-- hardware_gateway/                   # [NHÓM 2: PHẦN CỨNG THẬT]
|   |-- LocalGateway.py                 # Gateway kết nối trực tiếp mạch ESP32-S3 YoloUNO qua UART Serial
|   `-- __init__.py                     # Package marker
|
|-- dashboard/                          # [PHÂN HỆ CLOUD / THINGSBOARD LOCAL]
|   |-- setup_thingsboard_dashboard.py  # Script tự động đăng ký thiết bị và nạp Dashboard công nghiệp
|   |-- thingsboard_dashboard.json      # Lược đồ xuất bản Dashboard ThingsBoard 3.x độc lập
|   |-- deploy_thingsboard.py           # Quản lý vòng đời Docker Stack ThingsBoard cục bộ
|   |-- docker-compose.yml              # Khai báo dịch vụ ThingsBoard tb-postgres, cổng 9090 và 1883
|   |-- verify_telemetry.py             # Kịch bản kiểm tra truyền nhận MQTT và phản hồi lệnh RPC
|   `-- __init__.py                     # Package marker
|
|-- ui/                                 # [PHÂN HỆ GIAO DIỆN CỤC BỘ & HẠ TẦNG ĐỆM]
|   |-- gateway_infrastructure.py       # Máy chủ HTTP nhúng (Port 5050), Keen Dashboards SCADA, SQLite WAL
|   |-- isolation_detector.py           # Mô-đun Edge ML Anomaly Detection (Isolation Forest)
|   `-- __init__.py                     # Package marker
|
`-- Guideline/                          # Thư mục tài liệu hướng dẫn và đề cương từ giảng viên
    |-- De.md                           # Đề bài và thang điểm môn học IoT
    |-- Suon bai.md                     # Sườn đề cương chi tiết của đề tài
    `-- Temple_report.md                # File mẫu báo cáo chính thức của môn học
```

---

## 6. HƯỚNG DẪN SỬ DỤNG MÃ NGUỒN (SOURCE CODE & GATEWAY EXECUTION SETUP)

Nội dung dưới đây cung cấp chỉ dẫn chuẩn xác để thiết lập môi trường, cấu hình thông số và khởi chạy Local IoT Gateway trên máy tính cá nhân hoặc Raspberry Pi.

### 6.1. Yêu cầu môi trường phần cứng và phần mềm

- **Hệ điều hành:** Microsoft Windows 10/11, Linux Ubuntu 20.04/22.04 LTS, hoặc Raspberry Pi OS (Debian-based).
- **Môi trường Python:** Python phiên bản 3.9 trở lên (đã được kiểm thử tương thích hoàn toàn trên Python 3.11, 3.12, 3.13, 3.14).
- **Phần cứng yêu cầu:**
  - Đối với Nhóm 1 (Mô phỏng): Chỉ cần máy tính chạy Python, không yêu cầu thiết bị ngoại vi.
  - Đối với Nhóm 2 (Phần cứng thật): Kit vi điều khiển ESP32-S3 (YoloUNO), cáp kết nối USB-C/Micro-USB, cảm biến khói MQ-2, cảm biến ngọn lửa Flame Sensor, động cơ Servo SG90, còi Buzzer và đèn LED.

### 6.2. Cài đặt các gói phụ thuộc (Dependencies)

Mở cửa sổ dòng lệnh Terminal hoặc PowerShell tại thư mục dự án và cài đặt các thư viện kết nối:

```bash
pip install paho-mqtt pyserial
```

> **Lưu ý kỹ thuật:** Giao diện Web Local Monitor (T10) được xây dựng trực tiếp trên nền tảng `http.server` và `socketserver` có sẵn của thư viện chuẩn Python (Standard Library). Do đó, Gateway không yêu cầu cài đặt thêm các framework bên thứ ba như Flask, FastAPI hay Node.js, giúp tối ưu hóa dung lượng RAM và khả năng khởi động tức thì trên các máy tính nhúng cấu hình thấp như Raspberry Pi Zero/Pi 3.

### 6.3. Cấu hình thông số Gateway

Các tham số hoạt động được cấu hình mặc định trong tệp nguồn hoặc có thể truyền qua tham số dòng lệnh:

- **Cấu hình CoreIOT Cloud:**
  - Broker Address: `app.coreiot.io` (Cổng: `1883`)
  - Device Access Token: `i2tchqq1390qcxhun4zr`
  - Telemetry Topic: `v1/devices/me/telemetry`
  - RPC Request Topic: `v1/devices/me/rpc/request/+`
- **Cấu hình Cổng Mạng Cục Bộ (Local Socket):**
  - Gateway Inbound Port (UDP): `127.0.0.1:5000`
  - Node Command Listening Port (UDP): `127.0.0.1:5001`
  - Local Web Monitor UI Port: `http://localhost:5050`
- **Cấu hình UART Serial (Mạch thật):**
  - Tốc độ truyền (Baudrate): `115200`
  - Cổng COM mặc định: Tự động quét tìm chip nạp USB (`CP210x`, `CH340`, `ESP32-S3`) hoặc cấu hình qua tham số `--port`.

---

### 6.4. Hướng dẫn khởi chạy hệ thống (Deployment & Operation)

#### Phương pháp 1: Khởi động tự động bằng trình điều phối All-in-One (Khuyến nghị)
Chỉ cần thực thi một dòng lệnh duy nhất để khởi chạy đồng thời toàn bộ hệ thống mô phỏng và tự động kích hoạt trình duyệt Web:

```bash
python start_system.py
```

Trình launcher sẽ tự động:
1. Kích hoạt tiến trình Gateway Hub ngầm (`LocalGateway_Simulation.py`).
2. Thăm dò trạng thái mở cổng mạng TCP 5050.
3. Tự động mở trình duyệt mặc định truy cập giao diện giám sát tại `http://localhost:5050`.
4. Kích hoạt tiến trình phát dữ liệu của End Node (`SimulationNode.py`).
5. Lắng nghe phím bấm `Ctrl+C` trong Terminal để dừng an toàn đồng thời tất cả các tiến trình con, đóng kết nối SQLite sạch sẽ.

Nếu muốn chạy trên môi trường máy chủ không có giao diện (Headless Raspberry Pi), thêm cờ tắt trình duyệt:
```bash
python start_system.py --no-browser
```

Khi chạy với phần cứng thật (ESP32-S3 kết nối qua cổng nối tiếp):
```bash
python start_system.py --mode hardware
# Hoặc chỉ định cổng COM cụ thể:
python start_system.py --mode hardware --port COM3
```

---

#### Phương pháp 2: Vận hành thủ công theo từng tiến trình độc lập

##### Vận hành Nhóm 1 - Mô phỏng (Simulation Mode)
Mở 2 cửa sổ Terminal độc lập tại thư mục dự án:
- **Terminal 1 - Khởi động Gateway Hub:**
  ```bash
  python simulation/LocalGateway_Simulation.py
  ```
- **Terminal 2 - Khởi động Virtual End Node:**
  ```bash
  python simulation/SimulationNode.py
  ```
- Truy cập trình duyệt tại: **`http://localhost:5050`**.

##### Vận hành Nhóm 2 - Phần cứng thực tế (Hardware Mode)
1. Cắm cáp USB nối máy tính với bo mạch YoloUNO ESP32-S3.
2. Khởi động Gateway phần cứng (tự động nhận diện cổng COM):
  ```bash
  python hardware_gateway/LocalGateway.py
  ```
   *(Trường hợp máy tính nhận cổng COM cụ thể, ví dụ COM5 hoặc `/dev/ttyUSB0`)*:
  ```bash
  python hardware_gateway/LocalGateway.py --port COM5 --baud 115200
  ```
3. Truy cập trình duyệt tại: **`http://localhost:5050`** để giám sát và điều khiển mạch thật.

---

### 6.5. Kiểm thử tự động và xác thực chất lượng (Automated Verification)

Dự án cung cấp bộ kịch bản kiểm thử toàn diện tại [`test_system.py`](test_system.py). Chạy lệnh sau để thực thi kiểm tra toàn bộ hệ thống:

```bash
python test_system.py
```

Kịch bản kiểm thử tự động thực hiện 7 bài đo chuẩn công nghiệp:
1. `test_no_emojis_or_vietnamese_in_codebase`: Kiểm tra tính chuẩn mực của mã nguồn (0 icon, 0 emoji, mã nguồn Python hoàn toàn bằng tiếng Anh chuyên ngành).
2. `test_sqlite_wal_buffer_lifecycle`: Xác thực chu trình lưu đệm ngoại tuyến SQLite, cơ chế truy vấn FIFO và cập nhật cờ đã đồng bộ (`mark_synced`).
3. `test_embedded_web_monitor_endpoints`: Xác thực tính toàn vẹn của giao diện Keen Dashboards HTML và các điểm cuối REST API (`GET /api/telemetry`, `POST /api/control`).
4. `test_hardware_serial_adapter`: Giả lập cổng Serial UART (Mock) để kiểm tra thuật toán tách dòng JSON và truyền lệnh điều khiển chấp hành xuống mạch.
5. `test_isolation_detector_inference`: Xác thực khả năng dự báo phân loại bất thường của thuật toán Isolation Forest (Edge ML Anomaly Detection) với dữ liệu thông thường và dữ liệu đột biến cháy.
6. `test_dashboard_json_structure`: Kiểm tra tính hợp lệ của lược đồ ThingsBoard Dashboard JSON (`thingsboard_dashboard.json`) và sự hiện diện đầy đủ của 8 widget đo lường/điều khiển RPC.
7. `test_udp_simulation_flow`: Kiểm tra luồng truyền nhận gói tin UDP hai chiều giữa Simulation Node và Gateway Hub.

---

## 7. ĐẶC TẢ GIAO DIỆN LẬP TRÌNH REST API CỤC BỘ

Máy chủ HTTP Gateway tại cổng `5050` cung cấp 2 điểm cuối API phục vụ giao tiếp trực tiếp với SCADA Web Dashboard hoặc các ứng dụng bên thứ ba:

### 1. `GET /api/telemetry`
Cung cấp bức ảnh chụp trạng thái tức thời của toàn trạm.

**Định dạng phản hồi mẫu:**
```json
{
  "smoke": 24.15,
  "flame": 0,
  "servo": 0,
  "buzzer": 0,
  "led": 0,
  "timestamp": 1795148184.97,
  "last_seen": 1795148184,
  "cloud_connected": true,
  "buffer_count": 0,
  "gateway_type": "Hardware (UART ESP32-S3)",
  "device_id": "YOLOUNO_FIRE_NODE_01"
}
```

### 2. `POST /api/control`
Tiếp nhận lệnh điều khiển cưỡng bức thiết bị từ giao diện trạm cục bộ.

- **Tiêu đề (Header):** `Content-Type: application/json`
- **Nội dung yêu cầu (Body):**
  ```json
  {
    "buzzer": 1,
    "led": 1,
    "servo": 90
  }
  ```
- **Phản hồi thành công:**
  ```json
  {
    "status": "success",
    "command": {
      "buzzer": 1,
      "led": 1,
      "servo": 90
    }
  }
  ```

---

## 8. TRIỂN KHAI VÀ TỰ HOST THINGSBOARD CỤC BỘ (TIÊU CHÍ N07 - 1.0 ĐIỂM CỘNG)

Dự án cung cấp bộ công cụ tự động hóa toàn diện để triển khai ThingsBoard (bản mã nguồn mở `tb-postgres`) trực tiếp trên máy tính cá nhân bằng Docker Compose:

### 8.1. Các tệp triển khai (Thư mục dashboard/)
- `dashboard/docker-compose.yml`: Khai báo dịch vụ ThingsBoard với cơ sở dữ liệu PostgreSQL tích hợp sẵn, mở cổng Web UI `9090` và cổng MQTT Broker `1883`.
- `dashboard/deploy_thingsboard.py`: Script quản lý vòng đời tự động (kiểm tra Docker daemon, nạp container, theo dõi health check và in thông tin tài khoản).

### 8.2. Hướng dẫn khởi chạy ThingsBoard cục bộ
Thực thi lệnh sau:
```bash
python dashboard/deploy_thingsboard.py
```

Script sẽ tự động khởi động stack và chờ tới khi ThingsBoard hoàn tất khởi tạo cơ sở dữ liệu (thường mất 45–60 giây):
- **Web UI:** `http://localhost:9090`
- **MQTT Broker:** `localhost:1883`
- **Tài khoản mặc định:**
  - System Administrator: `sysadmin@thingsboard.org` / mật khẩu `sysadmin`
  - Tenant Administrator: `tenant@thingsboard.org` / mật khẩu `tenant`
  - Customer User: `customer@thingsboard.org` / mật khẩu `customer`

### 8.3. Kết nối Local Gateway với ThingsBoard cục bộ
Sau khi tạo thiết bị trên ThingsBoard local và lấy Access Token, chỉ cần chạy:
```bash
# Đối với nhóm 2 (Phần cứng thật):
python hardware_gateway/LocalGateway.py --broker localhost --token <YOUR_TOKEN>

# Hoặc dùng launcher điều phối chung từ thư mục gốc:
python start_system.py --broker localhost --token <YOUR_TOKEN>
```

### 8.4. Tự động khởi tạo Dashboard và thiết bị trên ThingsBoard cục bộ

Dự án cung cấp công cụ tự động hóa khởi tạo thiết bị và Dashboard [`dashboard/setup_thingsboard_dashboard.py`](dashboard/setup_thingsboard_dashboard.py):

```bash
python dashboard/setup_thingsboard_dashboard.py
```

Công cụ sẽ thực hiện qua REST API của ThingsBoard:
- Tự động đăng nhập tài khoản Tenant (`tenant@thingsboard.org`).
- Đăng ký thiết bị `FireAlarm_Gateway` và gán Access Token cố định: `i2tchqq1390qcxhun4zr`.
- Tự động tạo Dashboard công nghiệp chuyên nghiệp: **Industrial Fire Alarm & Suppression System** với đầy đủ các thành phần:
  - Đồng hồ đo nồng độ khói khí gas (Smoke Density Radial Gauge).
  - Đèn chỉ báo cảnh báo lửa (Flame Detector Status).
  - Biểu đồ biến thiên môi trường theo thời gian thực (Environmental Telemetry History Chart: smoke, temperature, flame).
  - 3 khối điều khiển chấp hành hai chiều RPC: Cửa chống cháy/van xả Servo (`setServo`), Còi báo động (`setBuzzer`), Đèn chớp cảnh báo (`setLed`).
- Xuất toàn bộ lược đồ Dashboard ra file độc lập [`dashboard/thingsboard_dashboard.json`](dashboard/thingsboard_dashboard.json).
- **Đường dẫn truy cập trực tiếp:** `http://localhost:9090/dashboards/47c220e0-e55d-11f1-b536-af039a103c55`

### 8.5. Kiểm tra và xác nhận truyền nhận Telemetry tức thì

Chạy kịch bản [`dashboard/verify_telemetry.py`](dashboard/verify_telemetry.py) để mô phỏng truyền chuỗi dữ liệu cảm biến và kiểm tra phản hồi tức thời từ ThingsBoard MQTT Broker:

```bash
python dashboard/verify_telemetry.py 5
```

### 8.6. Dừng ThingsBoard khi kết thúc thử nghiệm
```bash
python dashboard/deploy_thingsboard.py --stop
```

