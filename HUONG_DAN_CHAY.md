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

### B. Phần mềm & Dịch vụ
* **Python 3.10+**: Đã cài các phụ thuộc:
  ```bash
  pip install pyserial paho-mqtt requests scikit-learn numpy
  ```
* **ThingsBoard Container (Khuyên dùng)**: Chạy trên Docker cổng `9090` (HTTP) và `1883` (MQTT).
  * Nếu không bật ThingsBoard Docker, hệ thống tự động fallback lên Cloud Broker `app.coreiot.io`.

---

## 2. Cách Khởi Chạy Toàn Bộ Hệ Thống (1 Lệnh Duy Nhất)

Mở Terminal tại thư mục gốc của dự án (`c:\261\IOT\CO3054-IoT-BTL-FireAlarm`), thực thi:

```bash
python run_system.py
```

Hoặc trong PowerShell:

```powershell
python run_system.py
```

### Các tham số cấu hình tùy chọn:
* `--port COM4`: Chỉ định cứng cổng Serial của ESP32-S3 (nếu cắm cổng khác).
* `--baud 115200`: Tốc độ baud UART (mặc định: 115200).
* `--broker 127.0.0.1`: Địa chỉ ThingsBoard MQTT Broker (mặc định tự động nhận diện).
* `--no-browser`: Chạy chế độ headless, không tự động bật cửa sổ trình duyệt.

---

## 3. Hoạt Động & Giao Diện Giám Sát

Khi lệnh `python run_system.py` chạy, hệ thống sẽ tự động:

1. **Nhận diện phần cứng**: Tự động quét và kết nối với bo mạch ESP32-S3 trên cổng COM.
2. **Nhận diện nền tảng ThingsBoard**: Tự động kiểm tra cổng 9090/1883, ưu tiên ThingsBoard Local.
3. **Mở đồng thời 2 Dashboard trên trình duyệt**:
   * **Dashboard 1 - Local SCADA Web Monitor** (`http://localhost:5050`):
     * Giám sát thông số cảm biến thời gian thực tại chỗ (On-station).
     * Bảng điều khiển can thiệp thủ công: Nút bấm **Kích hoạt còi**, **Bật đèn LED**, **Đóng/Mở cửa Servo 90°**, nút **Lockdown khẩn cấp**.
     * Nhật ký sự kiện FIFO kiểm toán thời gian thực.
   * **Dashboard 2 - ThingsBoard Industrial SCADA** (`http://localhost:9090`):
     * Đồng hồ kim (Gauge) nồng độ khói MQ-2 và phát hiện lửa.
     * Trạng thái AI Anomaly (Isolation Forest: 0 = Bình thường, 1 = Bất thường).
     * Đồ thị phân tích xu hướng nhiệt độ và khói theo thời gian thực.
4. **Điều khiển hai chiều (Bidirectional RPC)**:
   * Khi người dùng bấm nút trên Dashboard hoặc khi Rule Chain tự động kích hoạt, lệnh sẽ truyền từ ThingsBoard $\rightarrow$ Local Gateway $\rightarrow$ ESP32-S3 qua UART.
   * Phần cứng thực tế sẽ phản hồi lệnh: Động cơ servo xoay, còi hú và đèn sáng tức thì kèm phản hồi `[ACK]`.

---

## 4. Cấu Trúc Dự Án Thực Tế (Không còn file mô phỏng)

```text
CO3054-IoT-BTL-FireAlarm/
│
├── run_system.py                    # FILE CHÍNH KHỞI CHẠY TOÀN BỘ HỆ THỐNG
├── HUONG_DAN_CHAY.md                # Tài liệu hướng dẫn sử dụng chi tiết
├── gateway_hardware_buffer.db       # Cơ sở dữ liệu SQLite đệm (WAL Mode)
│
├── 01_Firmware_EndNode/             # Mã nguồn nhúng ESP32-S3
│   ├── platformio.ini               # Cấu hình PlatformIO & nạp flash
│   └── src/main.cpp                 # Firmware C++ đọc cảm biến & nhận lệnh RPC
│
├── 02_Local_Gateway/                # Trạm cổng trung tâm & Edge AI
│   ├── hardware_gateway/
│   │   └── LocalGateway.py          # Bộ điều phối Gateway phần cứng UART
│   ├── ui/
│   │   ├── gateway_infrastructure.py# SQLite WAL repository & Web Monitor 5050
│   │   └── isolation_detector.py    # Mô hình AI Isolation Forest phát hiện cháy
│   ├── run_hardware_gateway.py      # Runner Gateway phần cứng cục bộ
│   ├── test_system.py               # Bộ kiểm thử tự động toàn diện
│   └── dashboard/
│       ├── setup_thingsboard_dashboard.py # Tạo thiết bị & nạp Dashboard tự động
│       ├── thingsboard_dashboard.json     # File cấu hình Dashboard ThingsBoard 3.x
│       └── docker-compose.yml             # Cấu hình ThingsBoard Docker Local
│
├── 03_CoreIOT_Config/               # Quy tắc & Kịch bản kiểm thử nền tảng
│   ├── rule_chains/
│   │   └── fire_alarm_rule_chain.json     # Rule Chain 4 cấp độ cảnh báo & RPC
│   └── scripts/
│       ├── measure_latency.py       # Đo độ trễ truyền thông End-to-End
│       ├── setup_rule_chain.py      # Tải tự động Rule Chain lên ThingsBoard
│       └── test_rulechain_alert.py  # Kiểm thử tự động 4 giai đoạn báo cháy
│
└── 04_Docs_Media/                   # Báo cáo kỹ thuật, video demo & đồ thị đo
```

---

## 5. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Tình trạng | Nguyên nhân khả dĩ | Cách khắc phục |
| :--- | :--- | :--- |
| **Không tìm thấy cổng COM4** | Cáp USB tiếp xúc kém hoặc mạch vừa reset sau nạp flash | Rút cáp USB cắm lại, hoặc bấm nút **RESET (EN)** trên mạch ESP32-S3 một lần. |
| **ThingsBoard không cập nhật dữ liệu** | Docker ThingsBoard chưa bật | Mở Docker Desktop hoặc chạy `docker compose -f 02_Local_Gateway/dashboard/docker-compose.yml up -d`. |
| **Độ trễ cao khi dùng Cloud Broker** | Mạng WiFi trường học chặn cổng MQTT 1883 | Sử dụng ThingsBoard Docker Local tại `127.0.0.1:1883` để đạt độ trễ tối ưu $\approx 100\text{ ms}$. |
| **Muốn nạp lại Firmware mới** | Cần cập nhật firmware nhúng | Chạy lệnh: `cd 01_Firmware_EndNode; pio run --target upload --upload-port COM4`. |
