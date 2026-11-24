# KỊCH BẢN QUAY VIDEO DEMO BÀI TẬP LỚN IOT (CO3054)

**Đề tài:** Hệ thống Báo cháy & Điều khiển Cửa Ngăn Cháy Thông minh (YoloUNO ESP32-S3 + Dual-AI TinyML/Isolation Forest + Local IoT Gateway UART/BLE + ThingsBoard/CoreIOT)  
**Giảng viên hướng dẫn:** TS. Lê Trọng Nhân (`02_Local_Gateway/Guideline/Đề.md`)  
**Thời lượng video khuyến nghị:** 6 – 8 phút *(đáp ứng quy định 5 – 10 phút trong đề bài)*  
**Mục tiêu điểm số:** **8.0/8.0 Công nghệ** *(tích lũy 13.0 điểm, dư 5.0 điểm dự phòng)* + **1.0/1.0 Nâng cao** *(tích lũy 2.0 điểm)* + **2.0/2.0 Báo cáo** = **10.0/10.0 điểm tối đa**.

> **Lưu ý kiểm toán mã nguồn (Codebase Audit):** Tài liệu này đã được đối chiếu 100% với mã nguồn thực tế trong workspace. Hệ thống sử dụng **mô hình kết nối qua IoT Gateway** (ESP32-S3 giao tiếp **UART Serial** hoặc **BLE không dây** với PC Gateway, sau đó PC Gateway kết nối MQTT tới ThingsBoard Local / CoreIOT), **không** dùng Wi-Fi/WebServer trực tiếp trên ESP32 (`T07`) và màn hình TFT hiện vẽ bằng **`Adafruit_ILI9341` + `Adafruit_GFX`** (chưa chuyển sang LVGL `N03` dù có sẵn file `include/lv_conf.h`). Xem chi tiết các điểm cần lưu ý ở **Phần 3**.

---

## Phần 1: Bảng tổng hợp tiêu chí & Minh chứng

### 1.1. Bảng ánh xạ các tiêu chí ĐÃ HIỆN THỰC trong mã nguồn

| Mã tiêu chí | Tên tiêu chí trong đề bài | Điểm | File code/Module tương ứng | Phân cảnh demo |
| :---: | :--- | :---: | :--- | :---: |
| **T03** | Cảm biến sử dụng kết nối BLE với thiết bị khác | 1.5 | `01_Firmware_EndNode/src/main.cpp` (`initBle`, `YoloUNO_FireNode`, GATT Telemetry Notify & Command Write)<br>`02_Local_Gateway/hardware_gateway/LocalGateway.py` (`BLEGatewayAdapter`, `bleak`)<br>`run_system.py` (`--ble`) | Phân cảnh 1, Phân cảnh 4 |
| **T04** | Thông tin được nội suy từ AI (TinyML chạy trên thiết bị) | 1.0 | `01_Firmware_EndNode/include/tinyml_fire_model.h` (`tinyml_predict_fire_risk`, `tinyml_get_risk_label`)<br>`01_Firmware_EndNode/src/main.cpp` (dòng 95, 358, 379, 390) | Phân cảnh 1, Phân cảnh 2, Phân cảnh 3 |
| **T05** | Công cụ thu thập dữ liệu, huấn luyện và export ra model TinyML | 1.0 | `01_Firmware_EndNode/tinyml/train_tinyml.py` (tổng hợp 2,500 mẫu, train Logistic Regression + Z-score, export `tinyml_fire_model.h`) | Phân cảnh 1 |
| **T08** | IoT Gateway hiện thực trên PC (hoặc Raspberry Pi): tổng hợp dữ liệu, gửi lên CoreIOT, nhận lệnh điều khiển từ CoreIOT và phân phối cho các thiết bị trong mạng local – mạch ESP giao tiếp UART với PC | 1.0 | `02_Local_Gateway/hardware_gateway/LocalGateway.py` (`LocalHardwareGateway`, `HardwareSerialAdapter`, `on_mqtt_message`, `command_worker`)<br>`run_system.py` | Phân cảnh 1, Phân cảnh 2, Phân cảnh 4 |
| **T09** | Chức năng AI chạy trên IoT Gateway local để phân tích dữ liệu, phát hiện (detect) và gửi kết quả lên server | 1.0 | `02_Local_Gateway/ui/isolation_detector.py` (`IsolationDetector` – Scikit-Learn `IsolationForest`)<br>`02_Local_Gateway/hardware_gateway/LocalGateway.py` (dòng 725–727) | Phân cảnh 2, Phân cảnh 3 |
| **T10** | Giao diện giám sát – điều khiển trên IoT Gateway local | 1.0 | `02_Local_Gateway/ui/gateway_infrastructure.py` (`EmbeddedWebMonitor`, `HTML_DASHBOARD`, cổng `5050`, `/api/telemetry`, `/api/control`) | Phân cảnh 2, Phân cảnh 4 |
| **T11** | Sử dụng template để phát triển ứng dụng, thiết kế dashboard, giám sát và điều khiển từ xa | 1.0 | `02_Local_Gateway/dashboard/setup_thingsboard_dashboard.py`<br>`02_Local_Gateway/dashboard/thingsboard_dashboard.json` (10 widget trên lưới 24 cột) | Phân cảnh 2, Phân cảnh 3, Phân cảnh 4 |
| **T12** | Sử dụng RuleChain để phát triển tính năng thông minh | 1.0 | `03_CoreIOT_Config/rule_chains/fire_alarm_rule_chain.json`<br>`03_CoreIOT_Config/scripts/setup_rule_chain.py`<br>`03_CoreIOT_Config/scripts/test_rulechain_alert.py`<br>`03_CoreIOT_Config/scripts/measure_latency.py` | Phân cảnh 3 |
| **T13** *(Bổ sung)* | Gửi cảnh báo bằng notification khi dữ liệu vượt ngưỡng (Notification Center & Email Dispatch) | 0.5 | `03_CoreIOT_Config/scripts/setup_customer_notifications.py`<br>`02_Local_Gateway/hardware_gateway/LocalGateway.py` (`dispatch_customer_notifications`)<br>`03_CoreIOT_Config/email_dispatch_log.txt` (gửi email tới Customer A, B, C) | Phân cảnh 3 (Bước 3.4) |
| **T14** *(Bổ sung)* | Cập nhật firmware qua OTA (Over-The-Air) không dây qua Wi-Fi / ThingsBoard | 2.0 | `01_Firmware_EndNode/firmware_v1.0.1.bin` & `firmware_v1.0.2.bin`<br>`02_Local_Gateway/dashboard/upload_ota_firmware.py`<br>`02_Local_Gateway/hardware_gateway/LocalGateway.py` (`_perform_ota_update`, ArduinoOTA qua Wi-Fi) | Phân cảnh 5 (Mới) |
| **T15** | IoT Gateway trên CoreIOT đồng bộ với IoT Gateway local | 2.0 | `02_Local_Gateway/dashboard/setup_thingsboard_dashboard.py` (`additionalInfo.gateway = True`)<br>`02_Local_Gateway/hardware_gateway/LocalGateway.py` (`--gateway-api`, `v1/gateway/telemetry`, `v1/gateway/rpc`, `sync_worker`)<br>`02_Local_Gateway/ui/gateway_infrastructure.py` (`OfflineBufferRepository` – SQLite WAL `gateway_hardware_buffer.db`) | Phân cảnh 4 |
| **N06** | Giao diện dashboard thiết kế riêng, có khả năng phát hiện (detect) và ghi nhận (record) các sự kiện | 1.0 *(Cộng)* | `02_Local_Gateway/ui/gateway_infrastructure.py` (`HTML_DASHBOARD`, `#alert-banner`, `Real-Time Station Event Log`, SQLite WAL audit) | Phân cảnh 2, Phân cảnh 3, Phân cảnh 4 |
| **N07** | Tự triển khai (deploy) ThingsBoard trên máy local | 1.0 *(Cộng)* | `02_Local_Gateway/dashboard/docker-compose.yml` (`thingsboard-local`, cổng `9090`/`1883`)<br>`02_Local_Gateway/dashboard/deploy_thingsboard.py` | Phân cảnh 1, Phân cảnh 4 |

### 1.2. Công thức tính tổng điểm BTL (theo Mục 3.4 trong `Đề.md`)

$$\text{Điểm BTL} = \min\!\left(8.0;\ \sum \text{Công nghệ}\right) + \text{Báo cáo } (\le 2.0) + \min\!\left(1.0;\ \sum \text{Nâng cao}\right)$$

* **Tổng điểm Công nghệ tích lũy:**
  $$\begin{aligned}
  \sum \text{Công nghệ} &= T03(1.5) + T04(1.0) + T05(1.0) + T08(1.0) + T09(1.0) + T10(1.0) \\
  &\quad + T11(1.0) + T12(1.0) + T13(0.5) + T14(2.0) + T15(2.0) = \mathbf{13.0\text{ điểm}}
  \end{aligned}$$
  $\rightarrow$ Điểm Công nghệ tính theo trần quy chế: $\min(8.0;\ 13.0) = \mathbf{8.0 / 8.0\text{ điểm}}$ *(dư 5.0 điểm an toàn dự phòng tuyệt đối)*.
* **Tổng điểm Nâng cao tích lũy:**
  $$\sum \text{Nâng cao} = N06(1.0) + N07(1.0) = \mathbf{2.0\text{ điểm}} \rightarrow \min(1.0;\ 2.0) = \mathbf{1.0 / 1.0\text{ điểm}}$$
* **Điểm Báo cáo kỹ thuật:** $\mathbf{2.0 / 2.0\text{ điểm}}$ *(trình bày đầy đủ 6 chương theo `02_Local_Gateway/Guideline/Temple_report.md` kèm ảnh minh chứng và bảng tự đánh giá)*.
* **Tổng điểm dự kiến:** $\mathbf{8.0 + 1.0 + 2.0 = 10.0 / 10.0\text{ điểm tối đa}}$.

### 1.3. Tổng hợp các tiêu chí KHÔNG đăng ký / chưa hiện thực trong mã nguồn

| Mã | Tên tiêu chí trong đề bài | Trạng thái kiểm tra mã nguồn |
| :---: | :--- | :--- |
| **T01, T02** | Cảm biến I2C trên Tasmota (0.5) / Modbus RS485 (1.0) | Không dùng (cảm biến hiện tại: MQ-2 Analog GPIO1, Flame Digital GPIO9, DHT11 GPIO10). |
| **T06, T07** | ESP-NOW (1.5) / Webserver trên ESP32 (1.0) | Không dùng (ESP32-S3 chạy qua Gateway UART/BLE; Web Monitor cổng 5050 chạy trên PC là **T10**, không phải T07). |
| **N01, N02, N04, N05** | LLM / Giọng nói / GPU AI / Mobile App riêng | Không triển khai. |
| **N03** | Màn hình hiển thị dựa trên LVGL (1.0) | **Chưa đạt trong code hiện tại:** có file `01_Firmware_EndNode/include/lv_conf.h`, nhưng `platformio.ini` chưa cài thư viện `lvgl` và `main.cpp` đang vẽ bằng `Adafruit_GFX` + `Adafruit_ILI9341`. Không nên đánh dấu "Có" cho N03 nếu chưa port sang LVGL (nhóm đã đạt tối đa 1.0/1.0 điểm Nâng cao nhờ **N06 + N07**). |

### 1.4. Mô hình Cảnh báo Khẩn cấp 4 Cấp độ Đã Bổ Sung (4-Tier Notification Architecture)

1. **Cấp độ 1 (Hardware End-Node ESP32-S3):** Còi Buzzer (GPIO 6) hú tần số cao, Đèn Warning LED (GPIO 17) chớp đỏ, Servo (GPIO 5) xoay 180° đóng cửa ngăn cháy, Màn hình TFT 320x240 chuyển toàn bộ nền đỏ rực `CANH BAO CHAY!` hiển thị chỉ số rủi ro TinyML Edge AI (%).
2. **Cấp độ 2 (Local Gateway SCADA Port 5050 & SQLite WAL):** Nhấp nháy Banner đỏ khẩn cấp `ALARM WARNING: HIGH SMOKE CONCENTRATION DETECTED!`, Bảng `Real-Time Station Event Log` tự động ghi nhận sự kiện `[TIER 1-4 EMERGENCY]`, lưu trữ ngoại tuyến tức thì vào SQLite WAL `gateway_hardware_buffer.db`.
3. **Cấp độ 3 (ThingsBoard Cloud Rule Chain):** Node `Evaluate Fire Risk` lọc đa biến, kích hoạt Alarm `FIRE_ALARM` mức độ `CRITICAL` và tự động kích hoạt `Clear Fire Alarm` khi môi trường trở về an toàn.
4. **Cấp độ 4 (Notification Center & Email Broadcast - Tiêu chí T13):** ThingsBoard Notification Target / Template gửi Web In-App Notification; Local Gateway Dispatcher tự động phát email cảnh báo tới Customer A, B, C (`customera@gmail.com`, `customerb@gmail.com`, `customerc@gmail.com`) và ghi log kiểm toán vào `03_CoreIOT_Config/email_dispatch_log.txt`.

---

## Phần 2: Kịch bản chi tiết từng Phân cảnh

### Bố cục khung hình khuyến nghị khi quay

* **Màn hình máy tính (Screen Capture):**
  * **Nửa trái:** Cửa sổ Terminal / PowerShell hiển thị log khởi động, dữ liệu UART/BLE, lệnh MQTT/RPC, bảng dispatch email và quá trình đồng bộ SQLite.
  * **Nửa phải:** Hai đến ba tab trình duyệt đặt sẵn để chuyển qua lại nhanh:
    * Tab 1: **Local SCADA Web Monitor** (`http://localhost:5050`).
    * Tab 2: **ThingsBoard Industrial Dashboard** (`http://localhost:9090/dashboards/47c220e0-e55d-11f1-b536-af039a103c55`).
    * Tab 3: **ThingsBoard Alarms / Notification Center / OTA Updates**.
* **Camera góc nhỏ (Webcam / Điện thoại):** Đặt cố định quay rõ mạch **ESP32-S3 YoloUNO**, màn hình **TFT ILI9341 320x240**, cụm cảm biến **MQ-2 / Flame / DHT11**, và **Servo cửa ngăn cháy, còi Buzzer, đèn LED đỏ**.

---

### Phân cảnh 1: Khởi động hệ thống, Kết nối mạng & Màn hình giao diện thiết bị *(0:00 – 1:45)*

* **Tiêu chí demo:** **N07**, **T05**, **T08**, **T04**, **T03** *(Lưu ý: màn hình TFT đang dùng `Adafruit_ILI9341`, không đọc là LVGL `N03`)*.

#### Bước 1.1: Chào mở đầu & Hạ tầng ThingsBoard chạy local (`N07`)

* **Thao tác & Góc quay:**
  * Mở **Docker Desktop** (hoặc gõ `docker ps` trong PowerShell).
  * Đưa chuột chỉ vào container `thingsboard-local` đang `Up / Running` với cổng `9090` (Web) và `1883` (MQTT).
  * *(Tùy chọn)* Lướt nhanh thư mục chứa `02_Local_Gateway/dashboard/deploy_thingsboard.py` và `setup_thingsboard_dashboard.py`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Em chào thầy ạ. Hôm nay nhóm em xin quay video demo đồ án môn IoT: Hệ thống báo cháy và điều khiển cửa ngăn cháy thông minh, chạy trên mạch ESP32-S3 YoloUNO kết hợp Local IoT Gateway và nền tảng ThingsBoard.*
  > *Đầu tiên, về phần hạ tầng server, thay vì phụ thuộc hoàn toàn vào cloud ngoài, nhóm em đã tự triển khai hẳn một máy chủ ThingsBoard chạy ngay trên máy tính cá nhân bằng Docker — đây là phần đáp ứng tiêu chí nâng cao **N07**. Như thầy thấy trên Docker Desktop, container `thingsboard-local` đang chạy ổn định ở cổng `9090` cho giao diện web và cổng `1883` cho MQTT Broker, kèm theo script `deploy_thingsboard.py` và `setup_thingsboard_dashboard.py` để tự động dựng lại toàn bộ thiết bị và Dashboard khi cần."*

#### Bước 1.2: Huấn luyện & xuất model TinyML sang mã C (`T05`)

* **Thao tác & Góc quay:**
  * Chuyển sang cửa sổ PowerShell ở thư mục gốc, chạy lệnh:
    ```powershell
    python 01_Firmware_EndNode/tinyml/train_tinyml.py
    ```
  * Chờ terminal in xong, lia chuột vào các dòng: `Dataset Size : 2500 samples (Train: 2000, Test: 500)`, `Overall Accuracy : 100.00%`, bảng `Confusion Matrix`, và dòng `[OK] Successfully exported TinyML C header to: .../01_Firmware_EndNode/include/tinyml_fire_model.h`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Tiếp theo, để đáp ứng tiêu chí **T05** về quy trình chuẩn bị dữ liệu, huấn luyện và xuất model TinyML, nhóm em có viết sẵn script `train_tinyml.py`. Khi chạy lệnh này, chương trình sẽ tổng hợp 2.500 mẫu dữ liệu cảm biến gồm khói MQ-2, nhiệt độ, độ ẩm và tín hiệu lửa, chia theo tỉ lệ 2.000 mẫu huấn luyện và 500 mẫu kiểm thử, sau đó huấn luyện mô hình phân loại có chuẩn hóa Z-score.*
  > *Kết quả in ra đạt độ chính xác 100% trên tập kiểm thử, và quan trọng nhất là script tự động xuất trọng số ra file C header `tinyml_fire_model.h` để nhúng thẳng vào firmware của ESP32-S3 mà không tốn bộ nhớ heap."*

#### Bước 1.3: Cấp nguồn YoloUNO & Khởi chạy toàn bộ hệ thống (`T08`, `T04`, `T03`)

* **Thao tác & Góc quay:**
  * Cắm cáp USB Type-C nối mạch ESP32-S3 YoloUNO vào máy tính (hoặc bấm nút RESET trên mạch).
  * **Quay camera phần cứng:** Màn hình TFT ILI9341 hiện nền xanh lá đậm (`ILI9341_DARKGREEN`), dòng chữ **`HE THONG AN TOAN`**, 4 dòng thông số (`MQ-2: <val>/4095`, `LUA: KHONG`, `T:28.xC RH:6x%`, **`TinyML: 0.x% (SAFE)`**); Servo ở góc **`0°`** (đang mở), còi im, LED tắt.
  * Trên PowerShell chạy lệnh khởi động tổng:
    ```powershell
    python run_system.py
    ```
  * Chờ terminal hiện các dòng: `[UART Serial] Opened port COMx at 115200 baud`, `[BLE] Server initialized and advertising as: YoloUNO_FireNode` *(nếu vừa reset)*, `[AN TOAN] Servo mo cua`, `[CoreIOT Cloud] Connected successfully to 127.0.0.1`, subscribe `v1/devices/me/rpc/request/+` (và `v1/gateway/rpc` nếu có `--gateway-api`).
  * Trình duyệt tự mở 2 tab `http://localhost:5050` và `http://localhost:9090`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Bây giờ em cấp nguồn cho mạch YoloUNO và khởi động toàn bộ hệ thống chỉ bằng một lệnh `python run_system.py`.*
  > *Ở góc camera phần cứng, thầy có thể thấy màn hình TFT 320x240 trên mạch đã sáng nền xanh lá với dòng chữ `HE THONG AN TOAN`. Ngay bên dưới là các thông số đo thực tế từ cảm biến MQ-2, cảm biến lửa, DHT11 và đặc biệt là kết quả suy luận trực tiếp trên chip **`TinyML: 0.x% (SAFE)`** — đáp ứng tiêu chí **T04**. Lúc này cửa ngăn cháy Servo đang mở ở góc `0 độ`, còi và đèn LED đều tắt. Đồng thời, firmware trên mạch cũng đã tự kích hoạt BLE Server tên `YoloUNO_FireNode` sẵn sàng cho chế độ kết nối không dây **T03** mà lát nữa em sẽ test riêng.*
  > *Còn ở cửa sổ Terminal bên trái, Local Gateway trên PC — tức tiêu chí **T08** — đã tự dò đúng cổng COM ở tốc độ `115200 baud`, kết nối thành công tới MQTT Broker `127.0.0.1`, đăng ký lắng nghe các lệnh điều khiển RPC, và tự mở sẵn cả hai trang giám sát trên trình duyệt. Sau đây em xin đi vào chi tiết màn hình giám sát ở trạng thái bình thường."*

* **Ảnh minh chứng cần chụp (`captured_picture/`):**
  * `captured_picture/N07.png`: Docker Desktop / `docker ps` hiển thị container `thingsboard-local` đang chạy cổng `9090` & `1883`.
  * `captured_picture/T05.png`: Terminal chạy `train_tinyml.py` hiển thị 2,500 mẫu, Accuracy 100%, Confusion Matrix và xuất thành công `tinyml_fire_model.h`.
  * `captured_picture/T04_1.jpg`: Ảnh chụp cận cảnh màn hình TFT nền xanh `"HE THONG AN TOAN"` kèm dòng `TinyML: X.X% (SAFE)`.
  * `captured_picture/T08.png`: Terminal hiển thị mở cổng COM, kết nối MQTT Broker và nhận dòng telemetry từ ESP32-S3.

---

### Phân cảnh 2: Giám sát trạng thái bình thường & Dashboard công nghiệp *(1:45 – 3:00)*

* **Tiêu chí demo:** **T04**, **T08**, **T09**, **T10**, **T11**, **N06**.

#### Bước 2.1: Xem luồng dữ liệu thời gian thực & Kiến trúc Dual-AI (`T04`, `T08`, `T09`)

* **Thao tác & Góc quay:**
  * Chỉ chuột vào cửa sổ Terminal đang chạy liên tục mỗi 0.5 giây:
    `[UART RX ESP32-S3] Smoke: <~180-400> | Flame: 0 | Temp: <~27-30> C | AI Risk: 0.x% | Trang thai: AN TOAN | Anomaly: 0`
* **Lời thoại gợi ý (Voiceover):**
  > *"Trên cửa sổ Terminal, thầy có thể thấy Local Gateway (**T08**) đang nhận dữ liệu từ ESP32-S3 đều đặn mỗi nửa giây rồi đẩy lên ThingsBoard qua MQTT QoS 1.*
  > *Điểm nhóm em đầu tư kỹ là hệ thống chạy song song 2 tầng AI: ngay trên chip ESP32-S3 có mô hình TinyML (**T04**) nội suy rủi ro cháy liên tục mỗi 100 mili-giây; còn khi dữ liệu về tới Gateway trên máy tính, mô hình **Isolation Forest** (**T09**) lại tiếp tục phân tích đồng thời 3 thông số khói, nhiệt độ và lửa để chấm điểm bất thường. Hiện tại môi trường đang sạch nên cả `AI Risk` của TinyML lẫn cờ `Anomaly` của Isolation Forest đều ở mức an toàn."*

#### Bước 2.2: Giới thiệu giao diện SCADA cục bộ (`http://localhost:5050` — `T10`, `T09`, `N06`)

* **Thao tác & Góc quay:**
  * Mở Tab 1 (`http://localhost:5050`).
  * Rê chuột qua 4 đèn báo trạng thái trên thanh tiêu đề: `Mode: Hardware (UART ESP32-S3)`, **`CoreIOT: Connected`** (xanh), **`End Node: Online`** (xanh), **`Buffer: 0`**.
  * Rê lần lượt qua 5 thẻ đo: `Smoke Concentration` (< 1800 ADC, thanh xanh), `Ambient Temperature` (< 35°C), `Flame Optical Sensor` (`SAFE`), `Emergency Fire Door` (`0 degrees`), `AI Isolation Forest` (`NORMAL` + `Anomaly Score: 0.xx`).
  * Cuộn nhẹ xuống chỉ vào bảng **`Real-Time Station Event Log`** ở cuối trang.
* **Lời thoại gợi ý (Voiceover):**
  > *"Chuyển sang tab trình duyệt đầu tiên ở địa chỉ `localhost:5050` — đây là trang giám sát và điều khiển tại chỗ chạy ngay trên Local Gateway, đáp ứng tiêu chí **T10** và cũng là giao diện tự thiết kế cho tiêu chí nâng cao **N06**.*
  > *Trên thanh tiêu đề có 4 đèn báo trạng thái giúp người vận hành nhìn vào là nắm được ngay hệ thống đang chạy chế độ UART, kết nối với CoreIOT/ThingsBoard đang xanh, mạch End Node đang online và bộ nhớ lưu tạm bằng 0.*
  > *Bên dưới là 5 ô hiển thị cập nhật mỗi giây: nồng độ khói MQ-2 đang nằm dưới ngưỡng an toàn `1800 ADC`, nhiệt độ phòng DHT11 dưới `35 độ C`, cảm biến lửa báo `SAFE`, cửa ngăn cháy đang mở ở `0 độ`, và ô `AI Isolation Forest` (**T09**) báo `NORMAL` với điểm bất thường rất thấp. Ngoài ra ở cuối trang có bảng `Real-Time Station Event Log` để tự động ghi lại lịch sử các sự kiện kèm mốc thời gian phục vụ tiêu chí **N06**."*

#### Bước 2.3: Giới thiệu ThingsBoard Industrial Dashboard (`http://localhost:9090` — `T11`)

* **Thao tác & Góc quay:**
  * Chuyển sang Tab 2 (`http://localhost:9090`).
  * Lia chuột từ trên xuống dưới chỉ các widget chính:
    * Hàng trên: `MQ-2 Raw ADC`, `Flame Detector Status`, `Ambient Temperature`, `AI Anomaly Status`, `Isolation Forest Anomaly Score`.
    * Hàng giữa: Biểu đồ `Environmental Telemetry History` (4 đường `MQ-2 ADC`, `Temperature (C)`, `Flame Status`, `Anomaly Score`) + 3 công tắc RPC bên phải (`Master Alarm Override`, `Alarm Siren Buzzer`, `Strobe LED Beacon`).
* **Lời thoại gợi ý (Voiceover):**
  > *"Còn ở tab thứ hai là Dashboard công nghiệp trên ThingsBoard Local cổng `9090`, được nhóm em dựng từ các widget template chuẩn theo tiêu chí **T11**.*
  > *Trên lưới 24 cột, hàng đầu tiên hiển thị trực quan đồng hồ đo khói `MQ-2 Raw ADC`, trạng thái lửa, nhiệt độ phòng và 2 đồng hồ theo dõi kết quả AI Isolation Forest. Hàng giữa là biểu đồ lịch sử thời gian thực vẽ liên tục cả 4 kênh dữ liệu, đặt cạnh 3 công tắc điều khiển từ xa RPC.*
  > *Vừa rồi là trạng thái hoạt động bình thường. Tiếp theo, em sẽ thử kích hoạt nguồn lửa thật ngay trước cảm biến để thầy xem toàn bộ hệ thống phản ứng khi có cháy như thế nào ạ."*

* **Ảnh minh chứng cần chụp (`captured_picture/`):**
  * `captured_picture/T09_1.png`: Thẻ `AI Isolation Forest` ở trạng thái `NORMAL` kèm `Anomaly Score` thấp.
  * `captured_picture/T10.png`: Toàn cảnh giao diện Local SCADA Web Monitor (`http://localhost:5050`) ở trạng thái bình thường.
  * `captured_picture/T11.png`: Toàn cảnh ThingsBoard Industrial Dashboard cập nhật biểu đồ real-time.
  * `captured_picture/N06.png`: Khung `Real-Time Station Event Log` trên giao diện Local SCADA.

---

### Phân cảnh 3: Kích hoạt kịch bản cháy/khói, Suy luận TinyML & Tự động hóa Rule Chain *(3:00 – 4:45)*

* **Tiêu chí demo:** **T04**, **T09**, **T11**, **T12**, **T13** *(Bổ sung)*, **N06**.

#### Bước 3.1: Quẹt lửa / tạo khói & Quan sát phản ứng phần cứng (`T04`)

* **Thao tác & Góc quay:**
  * Đưa bật lửa (đốt trước cảm biến lửa chân GPIO 9 kéo `LOW`, hoặc xì gas/khói vào MQ-2 vượt `1800 ADC`).
  * **Giữ camera phần cứng 5–7 giây:** quay rõ màn hình TFT đổi nền đỏ (`ILI9341_RED`) hiện **`CANH BAO CHAY!`**, `LUA: PHAT HIEN`, **`TinyML: 9x.x% (CRITICAL)`**; nghe rõ còi Buzzer 500Hz kêu, đèn LED đỏ sáng, và Servo xoay sang **`180°`** (đóng cửa ngăn cháy) kèm log `[CANH BAO CHAY] Servo dong cua`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Bây giờ em sẽ dùng bật lửa đưa lại gần cụm cảm biến để mô phỏng tình huống có cháy thật.*
  > *Thầy có thể thấy ngay lập tức ở góc camera phần cứng: cảm biến phát hiện lửa, mô hình TinyML trên chip ESP32-S3 (**T04**) nhảy xác suất nguy cơ cháy lên trên 90% ở mức `CRITICAL`. Màn hình TFT lập tức chuyển sang nền đỏ báo **`CANH BAO CHAY!`**, còi Buzzer 500Hz hú vang, đèn LED đỏ sáng lên, và động cơ Servo lập tức xoay sang góc **`180 độ`** để đóng cửa ngăn cháy, cô lập khói lửa không cho lan sang khu vực khác."*

#### Bước 3.2: Quan sát cảnh báo trên SCADA Local & ThingsBoard (`T09`, `N06`)

* **Thao tác & Góc quay:**
  * Khi đang báo cháy, lia chuột nhanh qua Tab 1 (`localhost:5050`):
    * Banner đỏ trên cùng: `ALARM WARNING: HIGH SMOKE CONCENTRATION OR FLAME INCIDENT DETECTED!`.
    * Thẻ `Flame Optical Sensor` báo đỏ `FLAME DETECTED`, `Emergency Fire Door` báo `Fire Partition Locked [Closed]`.
    * Thẻ `AI Isolation Forest` báo đỏ **`ANOMALY DETECTED`** với `Anomaly Score >= 0.90`.
  * Chuyển sang Tab 2 (`localhost:9090`):
    * Đồng hồ và biểu đồ nhảy vọt lên vùng đỏ.
    * Bấm nhanh vào mục **Alarms** cho thấy Alarm mức `CRITICAL` vừa được tạo.
* **Lời thoại gợi ý (Voiceover):**
  > *"Cùng lúc đó trên màn hình máy tính, ở trang Local SCADA `5050` (**N06**) lập tức bật thanh cảnh báo đỏ rực trên đầu trang, trạng thái cửa báo đã khóa ngăn cháy, và đặc biệt ô AI Isolation Forest (**T09**) chuyển đỏ `ANOMALY DETECTED` với điểm bất thường trên `0.90`.*
  > *Còn bên Dashboard ThingsBoard, đồng hồ và biểu đồ tăng vọt ngay tức thì, đồng thời hệ thống tự động tạo mới một cảnh báo mức `CRITICAL` trong danh sách Alarms của ThingsBoard."*

#### Bước 3.3: Giải thích Rule Chain & Phục hồi trạng thái an toàn (`T12`)

* **Thao tác & Góc quay:**
  * Mở mục **Rule Chains -> Fire Alarm Rule Chain** trên ThingsBoard, rê chuột dọc theo sơ đồ: `Filter Telemetry` $\rightarrow$ `Save Telemetry` & `Evaluate Fire Risk` $\rightarrow$ nhánh `True` (`Create Fire Alarm`) / nhánh `False` (`Clear Fire Alarm`).
  * Đưa bật lửa/khói ra xa để cảm biến hạ dưới ngưỡng hysteresis (`MQ-2 <= 1650`, `Flame = 0`, `Temp <= 34°C`).
  * **Quay nhanh camera phần cứng + Dashboard:** TFT tự chuyển về nền xanh `"HE THONG AN TOAN"`, `TinyML` về `SAFE`, Servo xoay lại `0°` mở cửa, còi/LED tắt, Rule Chain tự xóa Alarm.
* **Lời thoại gợi ý (Voiceover):**
  > *"Tất cả luồng xử lý thông minh phía server đều do **Rule Chain** đảm nhiệm — đây là tiêu chí **T12**. Như thầy thấy trên sơ đồ `Fire Alarm Rule Chain`, gói tin đi qua node `Filter Telemetry` sẽ vừa được lưu vào lịch sử qua `Save Telemetry`, vừa đưa qua node `Evaluate Fire Risk` để đánh giá ngưỡng cháy và kết quả AI. Nếu vượt ngưỡng sẽ đi nhánh `True` kích hoạt `Create Fire Alarm`, còn khi môi trường an toàn trở lại sẽ tự đi nhánh `False` sang `Clear Fire Alarm`.*
  > *Bây giờ em đưa bật lửa ra xa để cảm biến hạ xuống dưới ngưỡng an toàn. Thầy thấy màn hình TFT tự động quay lại nền xanh `HE THONG AN TOAN`, cửa Servo mở lại về `0 độ`, còi và đèn tự động tắt, còn trên ThingsBoard thì Alarm cũng được tự động xóa."*

#### Bước 3.4 *(Bổ sung)*: Tích hợp 4 Cấp Độ Báo Động & Dispatch Email tới Customer A, B, C (`T13`)

* **Thao tác & Góc quay:**
  * Khi cháy xảy ra, chỉ chuột vào cửa sổ Terminal của Local Gateway hiển thị khung phát tán email:
    ```
    ======================================================================
    [TIER 4 NOTIFICATION] DISPATCHING EMERGENCY FIRE EMAILS TO CUSTOMERS A, B, C
     -> Email successfully dispatched to: customera@gmail.com
     -> Email successfully dispatched to: customerb@gmail.com
     -> Email successfully dispatched to: customerc@gmail.com
    ======================================================================
    ```
  * Mở file `03_CoreIOT_Config/email_dispatch_log.txt` (hoặc chạy lệnh `python 03_CoreIOT_Config/scripts/setup_customer_notifications.py --test-email`).
  * Chỉ rõ trong file log: Mốc thời gian, Severity: `CRITICAL FIRE HAZARD`, Target Emails, các chỉ số cảm biến (`Smoke`, `Temp`, `Flame`, `TinyML Risk`), và 4 cấp độ hành động.
  * Chuyển nhanh qua tab `localhost:5050` mục **Real-Time Station Event Log** chỉ dòng:  
    `[TIER 4 BROADCAST] Emergency email dispatched to: customera@gmail.com, customerb@gmail.com, customerc@gmail.com`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Đặc biệt, để nâng cấp khả năng ứng phó sự cố và đáp ứng tiêu chí **T13** về Notification cảnh báo khi vượt ngưỡng, nhóm em đã tích hợp mô hình cảnh báo 4 cấp độ đồng bộ:*  
  > *Cấp 1 là phần cứng End-Node, Cấp 2 là SCADA 5050, Cấp 3 là Rule Chain Cloud. Và ở **Cấp độ 4**, hệ thống tự động kích hoạt Notification Center và Email Dispatcher: ngay khi có cháy, Gateway lập tức phát email khẩn cấp đến 3 đối tượng khách hàng là `Customer A` (căn hộ dân cư), `Customer B` (văn phòng thương mại), và `Customer C` (đội phòng cháy chữa cháy).*  
  > *Toàn bộ nội dung email kèm thông số đo đạc thời gian thực được ghi nhận minh bạch vào file kiểm toán `email_dispatch_log.txt` như thầy thấy trên màn hình."*

* **Ảnh minh chứng cần chụp (`captured_picture/`):**
  * `captured_picture/T04_2.jpg`: Cận cảnh màn hình TFT nền đỏ `"CANH BAO CHAY!"` kèm `TinyML: 9x.x% (CRITICAL)` và Servo đã xoay sang góc đóng cửa ngăn cháy.
  * `captured_picture/T04_3.png`: Terminal ghi lại quá trình chuyển trạng thái từ `AN TOAN` sang `CANH BAO` kèm `AI Risk` tăng vọt.
  * `captured_picture/T09_2.png`: Thẻ `AI Isolation Forest` chuyển đỏ `ANOMALY DETECTED` kèm `Anomaly Score >= 0.90`.
  * `captured_picture/T12.png`: Sơ đồ `Fire Alarm Rule Chain` trên giao diện ThingsBoard.
  * `captured_picture/T13.png` *(Bổ sung)*: Terminal hiển thị bảng dispatch email tới Customer A, B, C & nội dung file `email_dispatch_log.txt`.

---

### Phân cảnh 4: Điều khiển 2 chiều (RPC) & Kiểm thử các tính năng bổ sung/ngoại tuyến *(4:45 – 7:00)*

* **Tiêu chí demo:** **T08**, **T11**, **T10**, **N06**, **T15**, **N07**, **T03**.

#### Bước 4.1: Điều khiển 2 chiều từ xa qua ThingsBoard RPC & SCADA tại chỗ (`T08`, `T11`, `T10`, `N06`)

* **Thao tác & Góc quay:**
  * Mở Tab 2 (`localhost:9090`), bật rồi tắt lần lượt 3 công tắc RPC (quay đồng thời camera phần cứng + Terminal):
    1. **`Alarm Siren Buzzer`** (`manualSetBuzzer(1)` / `0`) $\rightarrow$ còi kêu rồi tắt.
    2. **`Strobe LED Beacon`** (`manualSetLed(1)` / `0`) $\rightarrow$ đèn LED sáng rồi tắt.
    3. **`Master Alarm Override (ON=Force, OFF=Auto)`** (`setAlarmOverride(true)` / `false`) $\rightarrow$ TFT đỏ, Servo đóng `180°`, còi + LED cùng bật cưỡng bức; tắt đi để trả về tự động.
  * Chỉ vào Terminal hiện dòng `[CoreIOT Device RPC] Cloud Command: ... -> [UART Serial TX -> ESP32-S3] {...}` và `[ACK]`.
  * Chuyển nhanh sang Tab 1 (`localhost:5050`), bấm **`CLOSE [90 deg]`** rồi **`OPEN [0 deg]`** ở mục `Fire Partition Door [Servo Motor]` (hoặc `TRIGGER EMERGENCY LOCKDOWN` / `RESTORE NORMAL OPERATION`).
  * Chỉ xuống bảng **`Real-Time Station Event Log`** đã ghi lại `[HH:MM:SS] Dispatched command: {"servo":90}`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Trước hết, để kiểm chứng khả năng điều khiển hai chiều từ xa qua RPC của tiêu chí **T08** và **T11**, em sẽ thao tác trực tiếp trên 3 công tắc ở Dashboard ThingsBoard.*
  > *Em bật công tắc `Alarm Siren Buzzer` — còi trên mạch kêu ngay lập tức, rồi em tắt đi. Tiếp theo là bật tắt `Strobe LED Beacon` — đèn LED đỏ phản hồi gần như tức thì. Còn công tắc `Master Alarm Override` dùng trong trường hợp người trực muốn kích hoạt báo động khẩn cấp bằng tay: khi bật lên, màn hình chuyển đỏ, cửa ngăn cháy Servo lập tức đóng lại `180 độ`, còi đèn bật hết; khi tắt đi thì hệ thống trả về chế độ tự động bình thường.*
  > *Ở cửa sổ Terminal, thầy có thể thấy lệnh RPC đi từ ThingsBoard qua Gateway rồi truyền xuống ESP32-S3 và nhận `[ACK]` về rất nhanh — trong phần đo thực nghiệm `latency_results.csv`, độ trễ phản hồi MQTT khoảng 2 mili-giây và tổng vòng lặp RPC chỉ khoảng 88 đến 113 mili-giây.*
  > *Ngoài ra, ngay trên trang SCADA cục bộ `localhost:5050` (**T10**), người vận hành vẫn có thể bấm đóng mở riêng cửa Servo `90 độ` — lệnh góc 90 độ trên web sẽ được firmware tự nhân đôi thành góc quay thực tế 180 độ để đóng kín cửa — và mọi lệnh bấm đều được lưu vết ngay vào bảng `Real-Time Station Event Log` phía dưới kèm giờ phút giây cho tiêu chí **N06**."*

#### Bước 4.2: Đồng bộ IoT Gateway & Chịu lỗi khi mất kết nối server bằng SQLite WAL (`T15`, `N07`)

* **Thao tác & Góc quay:**
  * Trên ThingsBoard, mở nhanh **Devices -> `FireAlarm_Gateway`** chỉ rõ cờ **`Is gateway: TRUE`** *(nếu đang chạy thêm `--gateway-api`, bấm sang tab **Relations** chỉ `Contains -> YOLOUNO_FIRE_NODE_01`)*.
  * Mở cửa sổ PowerShell thứ 2, gõ lệnh giả lập rớt kết nối broker:
    ```powershell
    docker pause thingsboard-local
    ```
    *(Hoặc tắt Wi-Fi nếu đang chạy với `app.coreiot.io`)*.
  * Chờ 3–5 giây, chỉ rõ 3 dấu hiệu:
    * Terminal Gateway báo `[CoreIOT Cloud] Connection lost (code: 7). Switching to local offline buffering mode.`
    * Trên `localhost:5050`, đèn báo đổi đỏ **`CoreIOT: Offline (Buffering)`** và số **`Buffer: 1, 2, 3, 4...`** tăng dần.
    * Bấm thử nút bật/tắt LED hoặc Servo trên `localhost:5050` $\rightarrow$ phần cứng vẫn chạy bình thường dù mất server.
  * Khôi phục lại broker bằng lệnh:
    ```powershell
    docker unpause thingsboard-local
    ```
    *(Bấm F5 làm mới tab `localhost:9090` nếu biểu đồ chưa tự vẽ nối tiếp ngay sau 3 giây)*.
  * Chờ 3 giây, chỉ Terminal in `[CoreIOT Cloud] Connected successfully...` và `[Buffer Sync] Synchronized X buffered records to CoreIOT.`, đèn báo trên `localhost:5050` xanh lại **`CoreIOT: Connected`**, **`Buffer: 0`**, và đồ thị trên ThingsBoard cập nhật nối tiếp liền mạch.
* **Lời thoại gợi ý (Voiceover):**
  > *"Tiếp theo là phần quan trọng cho tiêu chí **T15** về đồng bộ giữa Local Gateway với IoT Gateway trên ThingsBoard. Trước hết, trong mục Devices của ThingsBoard, thiết bị `FireAlarm_Gateway` đã được cấu hình chuẩn cờ **`Is gateway: TRUE`**, hỗ trợ cả giao thức Gateway MQTT API và đồng bộ dữ liệu hai chiều.*
  > *Bây giờ, để chứng minh hệ thống không bị mất dữ liệu khi rớt mạng hoặc mất kết nối tới server, em sẽ chạy lệnh `docker pause thingsboard-local` để ngắt tạm broker ThingsBoard.*
  > *Thầy để ý ngay trên Terminal và trang `localhost:5050`: đèn báo lập tức chuyển đỏ `CoreIOT: Offline (Buffering)`, đồng thời bộ đếm `Buffer` nhảy tăng dần `1, 2, 3, 4...`. Toàn bộ dữ liệu cảm biến trong lúc mất mạng đều được Gateway tự động lưu tạm vào cơ sở dữ liệu SQLite chế độ WAL (`gateway_hardware_buffer.db`) dưới máy để không bị mất gói tin nào. Đặc biệt là lúc này em vẫn bấm điều khiển phần cứng ngay tại trang local `5050` hoàn toàn bình thường.*
  > *Bây giờ em mở lại kết nối bằng lệnh `docker unpause thingsboard-local`. Chỉ sau vài giây, Gateway tự kết nối lại, tiến trình đồng bộ tự động đẩy bù hết các bản ghi đang lưu tạm lên ThingsBoard — thầy thấy dòng `[Buffer Sync] Synchronized...` trên Terminal, số `Buffer` trên web tụt về `0`, và biểu đồ trên ThingsBoard vẽ nối tiếp liền mạch không bị đứt đoạn."*

#### Bước 4.3: Vận hành hoàn toàn không dây qua Bluetooth BLE (`T03`) & Kết thúc

* **Thao tác & Góc quay:**
  * Nhấn `Ctrl+C` dừng phiên UART cũ.
  * **Quay rõ camera phần cứng:** Rút hẳn cáp USB khỏi laptop, cắm mạch ESP32-S3 vào **pin dự phòng / củ sạc rời** (cho thấy không còn dây nối vào máy tính).
  * Đảm bảo đã bật Bluetooth trên Windows, chạy lệnh:
    ```powershell
    python run_system.py --ble
    ```
  * Chờ Terminal in `[BLE Scanner] Scanning for BLE device named 'YoloUNO_FireNode'...` $\rightarrow$ `[BLE Adapter] SUCCESS: Connected to YoloUNO_FireNode [...]` $\rightarrow$ `[BLE Adapter] Subscribed to Telemetry (UUID: beb5483e-...)` và dữ liệu đổ về `[BLE RX ESP32-S3] ...`.
  * Chỉ nhanh trên `localhost:5050`: đèn chế độ đổi thành **`Mode: Wireless BLE (YoloUNO_FireNode)`**.
  * Bấm thử 1 nút bật/tắt LED hoặc Servo trên Dashboard $\rightarrow$ Terminal hiện `[BLE Adapter TX -> ESP32-S3] {...}` và mạch phản hồi không dây ngay lập tức.
* **Lời thoại gợi ý (Voiceover):**
  > *"Và tính năng kết nối không dây của tiêu chí **T03** là giao tiếp cảm biến qua Bluetooth Low Energy (BLE). Em dừng chế độ UART, rút hẳn dây USB ra khỏi máy tính và cấp nguồn cho mạch ESP32-S3 bằng nguồn rời để thầy thấy hai bên hoàn toàn không nối dây với nhau.*
  > *Bây giờ em chạy lại hệ thống với cờ không dây `python run_system.py --ble`. Thư viện `bleak` trên Local Gateway tự động quét và kết nối tới thiết bị `YoloUNO_FireNode`, đăng ký nhận dữ liệu qua BLE GATT Notify. Như thầy thấy trên Terminal, dòng `[BLE RX ESP32-S3]` đã bắt đầu chảy về đều đặn và cập nhật lên cả hai Dashboard với chế độ hiển thị `Wireless BLE`. Em thử bấm bật đèn/cửa trên web thì lệnh cũng truyền ngược không dây qua BLE (`[BLE Adapter TX -> ESP32-S3]`) xuống mạch thực thi ngay lập tức."*

* **Ảnh minh chứng cần chụp (`captured_picture/`):**
  * `captured_picture/T15_1.png`: Màn hình ThingsBoard Device `FireAlarm_Gateway` thể hiện `Is gateway: TRUE` (và tab `Relations` nếu dùng `--gateway-api`).
  * `captured_picture/T15_2.png`: Terminal & giao diện `localhost:5050` khi `docker pause` hiển thị `CoreIOT: Offline (Buffering)` và `Buffer: X` tăng dần.
  * `captured_picture/T15_3.png`: Terminal hiển thị `[Buffer Sync] Synchronized X buffered records to CoreIOT` và `Buffer: 0` sau khi `docker unpause`.
  * `captured_picture/T03_1.png`: Terminal chạy `python run_system.py --ble` hiển thị kết nối thành công tới `YoloUNO_FireNode`, nhận `[BLE RX ESP32-S3]` và truyền `[BLE Adapter TX -> ESP32-S3]`.
  * `captured_picture/T03_2.jpg`: Ảnh chụp thực tế mạch ESP32-S3 cấp nguồn bằng pin dự phòng/củ sạc (không cắm dây USB vào laptop) nhưng Dashboard trên laptop vẫn nhận dữ liệu thời gian thực.

---

### Phân cảnh 5 *(Bổ sung Mới)*: Nâng cấp Firmware Over-The-Air (OTA) Không Dây qua Wi-Fi / ThingsBoard (`T14`) *(7:00 – 8:15)*

* **Tiêu chí demo:** **T14**, **T03**, **T08**.

#### Bước 5.1: Bối cảnh mạch chạy độc lập & Chuẩn bị OTA (`T14`)
* **Thao tác & Góc quay:**
  * Quay camera phần cứng: Mạch ESP32-S3 đang đặt từ xa, cấp nguồn bằng pin sạc/sạc rời (không cắm dây USB vào máy tính).
  * Mạch đang kết nối BLE truyền telemetry với Gateway bình thường, đồng thời kết nối Wi-Fi nền (`172.20.10.5`).
  * Màn hình TFT 320x240 hiển thị phiên bản hiện tại là `v1.0.1`.
* **Lời thoại gợi ý (Voiceover):**
  > *"Để hoàn thiện tiêu chí công nghệ nâng cấp firmware từ xa **T14** (2.0 điểm), nhóm em xin demo tính năng nạp Firmware OTA hoàn toàn không dây.*  
  > *Trong các tòa nhà thông minh, mạch cảm biến báo cháy gắn trên trần cao hoặc phòng kỹ thuật không thể tháo dỡ để cắm cáp nạp lại. Hiện tại mạch YoloUNO đang chạy phiên bản `v1.0.1`, vừa kết nối BLE với Gateway vừa duy trì kết nối Wi-Fi nền sẵn sàng nhận cập nhật OTA từ ThingsBoard."*

#### Bước 5.2: Phân phối Firmware v1.0.2 và Nạp từ xa qua Wi-Fi
* **Thao tác & Góc quay:**
  * Mở cửa sổ PowerShell mới, chạy script gán firmware phiên bản mới `v1.0.2`:
    ```powershell
    python 02_Local_Gateway/dashboard/upload_ota_firmware.py
    ```
  * Chỉ chuột vào màn hình Terminal của Local Gateway:
    - Gateway tự động phát hiện bản `v1.0.2`: `[CoreIOT Web OTA] New firmware package assigned from Web UI!`.
    - Thông báo trạng thái: `DOWNLOADING...` $\rightarrow$ Tải file `firmware_ota.bin` (842,784 bytes) $\rightarrow$ Xác thực SHA256.
    - Tiến hành nạp: `Pushing binary over Wi-Fi via ArduinoOTA to 172.20.10.5:3232...`.
    - Hoàn tất: `Wireless ArduinoOTA flash succeeded! Device updated to v1.0.2`.
  * **Quay camera phần cứng:** Mạch ESP32-S3 tự động khởi động lại không dây, màn hình TFT sáng lên với dòng chữ phiên bản mới **`v1.0.2 (OTA)`**, đèn Warning LED nhấp nháy chu kỳ 500ms (tính năng mới của bản 1.0.2) chứng minh bản firmware mới đã được nạp thành công 100% qua sóng Wi-Fi.
* **Lời thoại gợi ý (Voiceover):**
  > *"Khi bản firmware `v1.0.2` được phân phối từ ThingsBoard, Gateway tự động tải về, kiểm tra mã băm SHA256 và truyền trực tiếp qua sóng Wi-Fi vào mạch ESP32-S3 qua giao thức ArduinoOTA trên cổng 3232.*  
  > *Mạch tự khởi động lại và như thầy thấy ở góc camera, màn hình TFT lập tức hiển thị phiên bản mới `v1.0.2 (OTA)` cùng nhịp đèn LED nhấp nháy heartbeat — toàn bộ quá trình diễn ra hoàn toàn không dây mà không cần cắm lại bất kỳ sợi cáp nào vào máy tính."*

#### Bước 5.3: Lời kết video demo
* **Lời thoại gợi ý (Voiceover):**
  > *"Như vậy, nhóm em đã trình bày và kiểm chứng thực tế toàn bộ các tiêu chí: Triển khai ThingsBoard Local Docker (**N07**), quy trình huấn luyện và chạy Dual-AI TinyML + Isolation Forest (**T04, T05, T09**), Local Gateway giao tiếp UART/BLE không dây (**T03, T08**), SCADA Dashboard tự thiết kế ghi nhận sự kiện (**T10, N06**), Rule Chain thông minh (**T11, T12**), cảnh báo khẩn cấp 4 cấp độ gửi email tới khách hàng (**T13**), chịu lỗi mất mạng đồng bộ SQLite WAL (**T15**), và nâng cấp firmware OTA từ xa (**T14**).*  
  > *Nhóm em xin chân thành cảm ơn thầy Lê Trọng Nhân và quý thầy cô đã theo dõi video báo cáo của nhóm ạ!"*

* **Ảnh minh chứng cần chụp (`captured_picture/`):**
  * `captured_picture/T14_1.png`: Terminal Gateway hiển thị các bước OTA: DOWNLOADING, VERIFIED, ArduinoOTA push thành công và cập nhật lên `v1.0.2`.
  * `captured_picture/T14_2.jpg`: Ảnh chụp cận cảnh màn hình TFT hiển thị phiên bản mới `v1.0.2 (OTA)` sau khi nạp không dây.

---

## Phần 3: Các điểm cần chỉnh sửa / lưu ý từ Codebase Audit để đạt điểm tối đa

Trước khi bấm máy quay demo, nhóm nên rà soát lại các điểm kỹ thuật sau để video chạy mượt mà:

1. **Tiêu chí `T12` (`03_CoreIOT_Config/rule_chains/fire_alarm_rule_chain.json` & `setup_rule_chain.py`):**
   * File `fire_alarm_rule_chain.json` đã được cập nhật kiểm tra đầy đủ cả `msg.smoke`, `msg.smoke_level`, `msg.flame`, `msg.temperature` và cờ TinyML, đồng thời tự động lưu vết danh sách email khách hàng nhận tin khẩn cấp `customera@gmail.com, customerb@gmail.com, customerc@gmail.com`.
   * Script `setup_rule_chain.py` hỗ trợ nạp tự động lên ThingsBoard cổng `9090`.
2. **Tiêu chí `T13` (Notification Center & Email Dispatch):**
   * Chạy script `python 03_CoreIOT_Config/scripts/setup_customer_notifications.py --test-email` để kiểm tra việc ghi nhận log vào `03_CoreIOT_Config/email_dispatch_log.txt` trước khi quay.
3. **Tiêu chí `T14` (Firmware OTA):**
   * Đảm bảo laptop và ESP32-S3 đang kết nối cùng mạng Wi-Fi (hoặc phát Wi-Fi từ điện thoại với SSID `Pham Trung` / `14052006`).
   * Hai file firmware nhị phân đã biên dịch sẵn trong `01_Firmware_EndNode/`: `firmware_v1.0.1.bin` và `firmware_v1.0.2.bin`.
4. **Tiêu chí `T03` (Bluetooth Low Energy):**
   * Local Gateway tự động dò tìm theo cả tên `YoloUNO_FireNode` và địa chỉ MAC `10:20:BA:06:57:7D`, kết nối nhanh trong vòng 1 giây trên Windows.
5. **Tiêu chí `N03` (LVGL):**
   * Không ghi `N03` vào Bảng tự đánh giá trong báo cáo vì firmware hiện dùng `Adafruit_ILI9341` (dù có file `lv_conf.h`). Nhóm đã đạt tối đa **1.0/1.0 điểm Nâng cao** từ **`N06` + `N07`** mà không cần `N03`.

---

## Phần 4: Checklist kiểm tra nhanh trước khi quay video

- [ ] **Docker Desktop:** Container `thingsboard-local` đang chạy (`localhost:9090` và `localhost:1883`).
- [ ] **Rule Chain & Notifications:** Đã kiểm tra Rule Chain và Notification Center hoạt động trơn tru.
- [ ] **Hardware:** Mạch **ESP32-S3 YoloUNO** đã nạp sẵn firmware v1.0.1, màn hình TFT hiển thị rõ nét `TinyML: X.X% (SAFE)`.
- [ ] **Dụng cụ thử nghiệm:** Bật lửa gas (để thử cảm biến lửa và khói), pin dự phòng hoặc sạc điện thoại rời (cho demo BLE không dây và OTA).
- [ ] **Kết nối mạng:** Laptop đã bật Bluetooth; mạng Wi-Fi phát trùng SSID và mật khẩu đã cấu hình trong firmware (`Pham Trung` / `14052006`).
- [ ] **Màn hình máy tính:** Sắp xếp cửa sổ Terminal bên trái, trình duyệt 3 tab bên phải (`localhost:5050`, `localhost:9090`, và thư mục kiểm toán log).
- [ ] **Kiểm tra ảnh minh chứng cần chụp:** `T03_1.png`, `T03_2.jpg`, `T13.png`, `T14_1.png`, `T14_2.jpg`, `T15_1.png`, `T15_2.png`, `T15_3.png`.
- [ ] **Phần mềm quay video:** OBS Studio hoặc phím tắt `Windows + Alt + R` (Game Bar), micro thu âm rõ ràng.
