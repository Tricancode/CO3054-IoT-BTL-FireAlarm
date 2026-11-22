# HƯỚNG DẪN VẬN HÀNH HỆ THỐNG IOT BÁO CHÁY THÔNG MINH
**Đề tài lớn môn Internet of Things (CO3054) - Trường ĐH Bách Khoa ĐHQG-HCM**
**Đáp ứng đầy đủ tiêu chí T08, T10, T12, T13**

---

## 1. Yêu Cầu Chuẩn Bị & Môi Trường

### A. Phần cứng
* **Mạch điều khiển trung tâm**: ESP32-S3 YoloUNO cắm qua cổng USB Type-C (cổng COM mặc định: `COM4`).
* **Cảm biến đầu vào**:
  * Cảm biến khói/khí gas: **MQ-2** (Chân Analog A0 - GPIO 1).
  * Cảm biến lửa: **Flame Sensor** (Chân Digital D6 - GPIO 9).
  * Cảm biến môi trường: **DHT11 / DHT20** (Chân D7 - GPIO 10).
* **Cơ cấu chấp hành (Actuators)**:
  * Động cơ đóng/mở cửa thoát hiểm: **Servo Motor** (Chân D2 - GPIO 5).
  * Còi báo động: **Buzzer** (Chân D3 - GPIO 6).
  * Đèn LED cảnh báo: **Warning LED** (Chân D8 - GPIO 17).
  * Màn hình hiển thị: **TFT SPI ILI9341 320x240**.

### B. Cài đặt thư viện Python (Chạy 1 lần trên máy mới)
Mở Terminal tại thư mục dự án và cài các thư viện phụ thuộc:
```powershell
pip install pyserial paho-mqtt requests scikit-learn numpy
```

---

## 2. KỊCH BẢN A: TRIỂN KHAI TRÊN MÁY MỚI (DÙNG DOCKER LOCALHOST)

Khi clone hoặc copy toàn bộ project sang máy tính mới có cài **Docker Desktop**, thực hiện lần lượt các bước sau:

### Bước 2.1: Bật Docker Container ThingsBoard
Mở ứng dụng Docker Desktop trên máy tính, sau đó mở Terminal tại thư mục gốc và chạy:

```powershell
python 02_Local_Gateway/dashboard/deploy_thingsboard.py
```
> **Lưu ý quan trọng**: Khi container `thingsboard-local` vừa được bật lên, dịch vụ Spring Boot và cơ sở dữ liệu PostgreSQL của ThingsBoard sẽ mất khoảng **45 - 60 giây** để khởi tạo hoàn toàn. Hãy đợi khoảng 1 phút trước khi sang Bước 2.2.

---

### Bước 2.2: Tự Động Nạp Dashboard & Thiết Bị (Provisioning)
Chạy script tự động tạo thiết bị `FireAlarm_Gateway` (Token: `i2tchqq1390qcxhun4zr`) và dựng toàn bộ Industrial Dashboard:

```powershell
python 02_Local_Gateway/dashboard/setup_thingsboard_dashboard.py
```
*(Script có cơ chế tự động chờ ThingsBoard sẵn sàng tối đa 180 giây, không bao giờ lo bị lỗi 404).*

---

### Bước 2.3: Tự Động Nạp Rule Chain Báo Cháy
Chạy script tải Rule Chain xử lý báo động 4 cấp độ và liên kết với Root Rule Chain:

```powershell
python 03_CoreIOT_Config/scripts/setup_rule_chain.py
```

---

### Bước 2.4: Khởi Chạy Toàn Bộ Hệ Thống
Cắm mạch ESP32-S3 vào cổng USB và chạy đúng 1 lệnh duy nhất:

```powershell
python run_system.py
```

Hệ thống sẽ tự động:
1. Kết nối mạch ESP32-S3 qua cổng COM (baudrate 115200).
2. Kết nối tới ThingsBoard Local (`127.0.0.1:1883`).
3. Tự động mở đồng thời cả 2 Dashboard trên trình duyệt:
   * **Local SCADA Web Monitor**: `http://localhost:5050` (Điều khiển còi, đèn, servo thủ công tại chỗ).
   * **ThingsBoard Industrial Dashboard**: `http://localhost:9090/dashboards/47c220e0-e55d-11f1-b536-af039a103c55` (Đồng hồ gas MQ-2, lửa, biểu đồ AI Anomaly).

---

## 3. KỊCH BẢN B: CHẠY TRÊN MÁY KHÔNG CÓ DOCKER (DÙNG CLOUD BROKER)

Nếu máy tính không cài Docker Desktop hoặc không muốn chạy local:

```powershell
python run_system.py --broker app.coreiot.io
```
* Dữ liệu telemetry sẽ được đẩy thẳng lên nền tảng đám mây `app.coreiot.io`.
* Màn hình Local SCADA Web Monitor vẫn hoạt động độc lập tại `http://localhost:5050`.

---

## 4. Cấu Trúc Dự Án Thực Tế (Production Clean)

```text
c:\261\IOT\CO3054-IoT-BTL-FireAlarm\
├── run_system.py               # FILE CHÍNH KHỞI CHẠY TOÀN BỘ HỆ THỐNG
├── HUONG_DAN_CHAY.md           # Hướng dẫn chi tiết kịch bản A & B
├── gateway_hardware_buffer.db  # CSDL SQLite lưu đệm phần cứng (WAL mode)
│
├── 01_Firmware_EndNode/        # Firmware ESP32-S3 YoloUNO (C++/Arduino)
│   ├── platformio.ini          # Cấu hình nạp firmware qua PlatformIO
│   └── src/main.cpp            # Đọc cảm biến MQ-2, Lửa, DHT & xử lý lệnh RPC
│
├── 02_Local_Gateway/           # Gateway phần cứng UART & Edge AI
│   ├── hardware_gateway/
│   │   └── LocalGateway.py     # Cổng giao tiếp UART & ThingsBoard MQTT
│   ├── ui/
│   │   ├── gateway_infrastructure.py # Web Monitor 5050 & SQLite WAL
│   │   └── isolation_detector.py     # Mô hình AI Isolation Forest
│   ├── run_hardware_gateway.py # Runner phần cứng cục bộ
│   ├── test_system.py          # Bộ kiểm thử tự động
│   └── dashboard/
│       ├── deploy_thingsboard.py          # Script bật/tắt Docker ThingsBoard
│       ├── setup_thingsboard_dashboard.py # Nạp tự động thiết bị & Dashboard
│       ├── thingsboard_dashboard.json     # File cấu hình Dashboard ThingsBoard 3.x
│       └── docker-compose.yml             # File compose cấu hình container
│
├── 03_CoreIOT_Config/          # ThingsBoard Rule Chains & Scripts
│   ├── rule_chains/
│   │   └── fire_alarm_rule_chain.json     # Rule Chain 4 cấp độ cảnh báo & RPC
│   └── scripts/
│       ├── measure_latency.py       # Đo độ trễ truyền thông End-to-End
│       ├── setup_rule_chain.py      # Tải tự động Rule Chain lên ThingsBoard
│       └── test_rulechain_alert.py  # Kiểm thử tự động 4 giai đoạn báo cháy
│
└── 04_Docs_Media/              # Tài liệu báo cáo & số liệu thực nghiệm
```

---

## 5. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Tình trạng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Lỗi `404 Not Found: /api/auth/login` khi chạy setup** | Container ThingsBoard vừa bật, Spring Boot chưa khởi tạo xong | Đợi thêm 30–45 giây để container nạp xong rồi chạy lại lệnh setup. Tui đã nâng timeout lên 180s để tự động chờ. |
| **Không tìm thấy cổng COM** | Cáp USB tiếp xúc kém hoặc mạch vừa reset sau flash | Rút cáp USB cắm lại, hoặc bấm nút **RESET (EN)** trên mạch ESP32-S3 một lần. |
| **Muốn nạp lại Firmware mới cho ESP32-S3** | Cần cập nhật firmware nhúng | Chạy lệnh: `cd 01_Firmware_EndNode; pio run --target upload --upload-port COM4`. |
