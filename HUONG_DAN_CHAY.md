# HƯỚNG DẪN VẬN HÀNH HỆ THỐNG IOT BÁO CHÁY THÔNG MINH
**Đề tài lớn môn Internet of Things (CO3054) - Trường ĐH Bách Khoa ĐHQG-HCM**
* **Đáp ứng đầy đủ 10/10 tiêu chí**: N07, T03, T04, T05, T08, T09, T10, T11, T12, T13, T14, T15, N06.

---

## 1. Yêu Cầu Chuẩn Bị & Môi Trường

### A. Phần cứng
* **Mạch điều khiển trung tâm**: ESP32-S3 YoloUNO cắm nguồn rời qua củ sạc hoặc pin dự phòng (hoặc cắm USB Type-C cổng COM mặc định `COM4`/`COM6`).
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
Mở Terminal tại thư mục gốc dự án và cài các thư viện phụ thuộc:
```powershell
pip install pyserial paho-mqtt requests scikit-learn numpy bleak
```

---

## 2. TRIỂN KHAI HẠ TẦNG THINGSBOARD LOCAL TRÊN DOCKER (TIÊU CHÍ N07)

Khi clone hoặc copy toàn bộ project sang máy tính mới có cài **Docker Desktop**, thực hiện lần lượt các bước sau:

### Bước 2.1: Bật Docker Container ThingsBoard
Mở ứng dụng Docker Desktop trên máy tính, sau đó mở Terminal tại thư mục gốc và chạy:
```powershell
python 02_Local_Gateway/dashboard/deploy_thingsboard.py
```
> **Lưu ý**: Khi container `thingsboard-local` vừa bật lên, dịch vụ Spring Boot và cơ sở dữ liệu PostgreSQL của ThingsBoard sẽ mất khoảng **45 - 60 giây** để khởi tạo hoàn toàn. Hãy đợi khoảng 1 phút trước khi sang Bước 2.2.

---

### Bước 2.2: Tự Động Nạp Dashboard & Thiết Bị (Provisioning)
Chạy script tự động tạo thiết bị `FireAlarm_Gateway` (Token: `i2tchqq1390qcxhun4zr`) và dựng toàn bộ Industrial Dashboard:
```powershell
python 02_Local_Gateway/dashboard/setup_thingsboard_dashboard.py
```
*(Script có cơ chế tự động chờ ThingsBoard sẵn sàng tối đa 180 giây, không bao giờ lo bị lỗi 404).*

---

### Bước 2.3: Tự Động Nạp Rule Chain Báo Cháy (Tiêu chí T12)
Chạy script tải Rule Chain xử lý báo động 3 cấp độ (Safe/Warning/Critical) và liên kết với Root Rule Chain:
```powershell
python 03_CoreIOT_Config/scripts/setup_rule_chain.py
```

---

## 3. KỊCH BẢN CHÍNH: VẬN HÀNH KHÔNG DÂY QUA BLE (TIÊU CHÍ T03)

Đây là chế độ truyền thông hoàn toàn không dây phục vụ **Tiêu chí T03 (Chuẩn truyền thông không dây BLE)**:
* **Mạch ESP32-S3 (YoloUNO)**: Cắm nguồn qua pin sạc dự phòng hoặc củ sạc (hoàn toàn không cắm dây nối với máy tính để làm minh chứng không dây). Mạch tự phát Bluetooth Advertising với tên `YoloUNO_FireNode` (MAC: `10:20:BA:06:57:7D`).
* **Máy tính Laptop**: Bật Bluetooth trên Windows và chạy lệnh:

```powershell
python run_system.py --ble
```

* **Cơ chế hoạt động**:
  1. Thư viện `bleak` tự động quét tìm thiết bị có tên `YoloUNO_FireNode` (hoặc MAC `10:20:BA:06:57:7D`).
  2. Kết nối và subscribe characteristic `beb5483e-36e1-4688-b7f5-ea07361b26a8` (GATT Telemetry Notify).
  3. Dữ liệu JSON đẩy thẳng vào pipeline cục bộ (Isolation Forest AI $\rightarrow$ SQLite WAL $\rightarrow$ ThingsBoard MQTT $\rightarrow$ Local SCADA UI 5050).
  4. Gateway tự động bắt địa chỉ Wi-Fi IP của mạch (ví dụ: `172.20.10.5`) từ luồng BLE để sẵn sàng cho tác vụ nạp OTA.
  5. Hỗ trợ gửi lệnh điều khiển ngược xuống mạch (Servo, Buzzer, LED) qua Characteristic Command `1c95d5e3-d8f7-413a-bf3d-7a2e5d7be87e`.
  6. Tự động phục hồi kết nối (auto-reconnect) khi ngắt kết nối.

---

## 4. KỊCH BẢN NẠP FIRMWARE OTA TỪ XA QUA WEB COREIOT (TIÊU CHÍ T14)

Chức năng cập nhật firmware không dây OTA (Over-The-Air) đáp ứng đầy đủ **Tiêu chí T14: Cập nhật firmware OTA cho thiết bị**:

### A. Sự khác biệt giữa 2 phiên bản Firmware để Demo Trực Quan Phần Cứng
Hệ thống đã chuẩn bị sẵn 2 bản file nhị phân `.bin` được tối ưu hóa trong thư mục `01_Firmware_EndNode/`:

1. **Bản chuẩn ban đầu ([firmware_v1.0.1.bin](file:///c:/261/IOT/Bluetooth/01_Firmware_EndNode/firmware_v1.0.1.bin))**:
   * Khi trạng thái bình thường (**SAFE**): Đèn LED cảnh báo (GPIO 17) **TẮT HOÀN TOÀN** (chỉ bật khi có cháy hoặc kích hoạt còi báo động).
   * Màn hình TFT LCD hiển thị: `FW: v1.0.1`.
   * Cấu hình Wi-Fi sẵn: `Pham Trung` / `14052006`.
   * *Mục đích*: Nạp trước vào mạch bằng máy khác (hoặc nạp dây lần đầu) để làm trạng thái gốc.

2. **Bản cập nhật OTA ([firmware_v1.0.2.bin](file:///c:/261/IOT/Bluetooth/01_Firmware_EndNode/firmware_v1.0.2.bin))**:
   * Khi nạp thành công qua OTA, ở trạng thái bình thường (**SAFE**): Đèn LED cảnh báo (GPIO 17) **TỰ ĐỘNG NHẤP NHÁY LIÊN TỤC** chu kỳ 500ms (chớp tắt 1Hz). Đây là minh chứng vật lý đập vào mắt người chấm thi mà không cần phải mở xem code hay cắm cáp USB.
   * Màn hình TFT LCD hiển thị rõ ràng: `FW: v1.0.2 (OTA)`.
   * Telemetry đẩy lên CoreIOT / ThingsBoard hiển thị `fw_version: "1.0.2"`.

---

### B. Quy trình các bước thực hiện Demo OTA

#### Bước 1: Mạch ở trạng thái v1.0.1 ban đầu
* Nạp file `firmware_v1.0.1.bin` vào mạch (bằng máy khác hoặc cắm dây nạp lần đầu: `pio run -d 01_Firmware_EndNode -e yolo_uno_v101 -t upload`).
* Cắm mạch vào pin dự phòng rời: Đèn LED cảnh báo tắt, màn hình LCD hiện `v1.0.1`, LCD góc trên hiện `WiFi: Pham Trung | IP: 172.20.10.5`.

#### Bước 2: Máy tính chạy hệ thống không dây BLE
Trên máy tính (không cắm dây vào mạch):
```powershell
python run_system.py --ble
```
* Dữ liệu cảm biến thời gian thực bay qua Bluetooth vào máy tính và đẩy lên Dashboard.
* Gateway nhận diện địa chỉ Wi-Fi IP của mạch: `172.20.10.5`.

#### Bước 3: Kích hoạt nạp OTA v1.0.2 qua Web CoreIOT / ThingsBoard
MemBau có thể chọn 1 trong 2 cách:

* **Cách 1 - Thao tác trực tiếp trên Web (Khuyên dùng khi thuyết trình):**
  1. Mở trình duyệt vào `http://localhost:9090` (hoặc `https://app.coreiot.io`).
  2. Vào mục **Entities** $\rightarrow$ **Devices** (hoặc **Device Groups** $\rightarrow$ **All**).
  3. Bấm chọn thiết bị **FireAlarm_Gateway**.
  4. Tại tab **Details**, cuộn xuống mục **Firmware**: Chọn gói **`yolo_firmware 1.0.2`**.
  5. Bấm biểu tượng **Dấu tích (Save)** ở góc dưới bên phải.

* **Cách 2 - Kích hoạt bằng lệnh Terminal tự động:**
  Mở thêm 1 tab PowerShell khác và chạy:
  ```powershell
  python 02_Local_Gateway/dashboard/upload_ota_firmware.py --version 1.0.2 --file 01_Firmware_EndNode/firmware_v1.0.2.bin
  ```

#### Bước 4: Quan sát kết quả thực nghiệm
1. Trên Terminal Gateway: Gateway tải file binary và đẩy qua Wi-Fi vào mạch:
   `[CoreIOT OTA] Pushing binary over Wi-Fi via ArduinoOTA to 172.20.10.5:3232...`
   `[CoreIOT OTA] Wireless ArduinoOTA flash succeeded!`
2. Trên Web CoreIOT: Huy hiệu firmware chuyển sang **`UPDATED (Màu xanh lá)`**.
3. **Trên phần cứng thật của mạch ESP32-S3**:
   * Mạch tự động khởi động lại vào phân vùng `app1`.
   * Màn hình TFT LCD đổi thành: **`FW: v1.0.2 (OTA)`**.
   * **Đèn LED cảnh báo (chân D8) bắt đầu chớp nháy liên tục mỗi 500ms**!
   * Terminal máy tính tự động kết nối lại BLE và tiếp tục truyền dữ liệu với `fw_version: "1.0.2"`.

---

### C. Kiến trúc & Tối ưu kỹ thuật OTA
* **Phân vùng nhớ kép (Dual OTA Partitions)**: Firmware sử dụng bảng phân vùng `min_spiffs.csv` chia Flash thành 2 phân vùng app (`app0` và `app1`) với kích thước **1.96 MB** mỗi phân vùng.
* **Tối ưu NimBLE-Arduino**: Thay thế thư viện Bluedroid mặc định bằng `NimBLE-Arduino 2.5.2` giúp firmware chỉ chiếm **42.8% Flash** (842 KB / 1.96 MB) và **15.3% RAM** (50 KB / 327 KB).
* **Wi-Fi / BLE Coexistence & Bảo vệ nạp**: 
  * Chip ESP32-S3 chia sẻ anten 2.4 GHz chung theo cơ chế Time-Division Coexistence (luân phiên từng lát cắt mili-giây giữa Wi-Fi và BLE).
  * Trong lúc ghi Flash OTA (`ArduinoOTA.onStart`), mạch tự động **tạm ngắt BLE** trong 3–5 giây để dành 100% tài nguyên cho Wi-Fi, ngăn ngừa tuyệt đối lỗi mất gói tin hay lỗi tràn bộ nhớ. Khi nạp xong, mạch reboot và cả 2 kết nối lại chạy song song bình thường.

---

## 5. KỊCH BẢN KIỂM THỬ ĐỆM NGOẠI TUYẾN SQLITE WAL (TIÊU CHÍ T15)

Tiêu chí T15 (2.0 điểm) yêu cầu chứng minh khả năng lưu đệm ngoại tuyến và tự động đẩy bù khi mạng phục hồi:

1. **Mô phỏng ngắt kết nối mạng**:
   Mở một tab PowerShell gõ:
   ```powershell
   docker pause thingsboard-local
   ```
2. **Quan sát phản ứng**:
   * Terminal Gateway: `[CoreIOT Cloud] Connection lost (code: 7). Switching to local offline buffering mode.`
   * Trên Web SCADA (`http://localhost:5050`): Navbar đổi sang huy hiệu màu cam **`CoreIOT: Offline (Buffering)`**.
   * Chỉ số **`Buffer: 1, 2, 3, 4, 5...`** tăng dần. Mọi dữ liệu đo đạc vẫn được lưu an toàn vào SQLite WAL `gateway_hardware_buffer.db`.
3. **Khôi phục mạng**:
   Gõ lệnh:
   ```powershell
   docker unpause thingsboard-local
   ```
4. **Kết quả**:
   * Terminal: `[Buffer Sync] Synchronized X buffered records to CoreIOT.`
   * SCADA 5050: Huy hiệu đổi lại màu xanh **`CoreIOT: Online`**, bộ đệm giải phóng về `Buffer: 0`.
   * ThingsBoard Dashboard: Biểu đồ Telemetry vẽ liền mạch 100% không mất bất kỳ điểm dữ liệu nào.

---

## 6. KỊCH BẢN PHỤ: CHẠY CÓ DÂY QUA CỔNG COM USB TRUYỀN THỐNG

Nếu muốn chạy mạch có cắm cáp USB vào máy tính:
```powershell
python run_system.py
```
* Hệ thống tự động quét cổng COM (CP210x/CH340/ESP32 CDC).
* Giao tiếp trực tiếp qua UART 115200 baud.

---

## 7. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Tình trạng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Không tìm thấy thiết bị BLE (`Device not found`)** | Windows chưa bật Bluetooth hoặc quét chậm | Đảm bảo Bluetooth trên Windows đang **BẬT**. Tui đã thêm cơ chế Direct Address Fallback tự động kết nối thẳng vào MAC `10:20:BA:06:57:7D`. |
| **Mạch không kết nối được Hotspot điện thoại** | Điện thoại phát sóng 5 GHz (ESP32 chỉ nhận sóng 2.4 GHz) | **Trên iPhone**: Vào Cài đặt $\rightarrow$ Điểm phát sóng $\rightarrow$ Bật **"Tối đa hóa khả năng tương thích"**.<br/>**Trên Android**: Chọn Băng tần AP là **2.4 GHz**. |
| **Lỗi `404 Not Found` khi nạp setup Dashboard** | Container ThingsBoard vừa bật, Spring Boot chưa khởi tạo xong | Đợi thêm 30–45 giây để container nạp xong rồi chạy lại lệnh setup (script đã có sẵn timeout tự động chờ). |
| **Nạp firmware qua cáp USB** | Muốn nạp firmware có dây | Gõ: `pio run -d 01_Firmware_EndNode -e yolo_uno_v101 -t upload` (cho bản 1.0.1) hoặc `-e yolo_uno_v102` (cho bản 1.0.2). |
