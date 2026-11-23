# KỊCH BẢN QUAY VIDEO DEMO BÀI TẬP LỚN IOT (CO3054)
**ĐỀ TÀI: HỆ THỐNG BÁO CHÁY VÀ ĐIỀU KHIỂN THOÁT HIỂM THÔNG MINH**
* **Nền tảng**: ESP32-S3 YoloUNO + Local IoT Gateway (PC/Python) + ThingsBoard (Docker Localhost & CoreIOT)
* **Thời lượng video khuyến nghị**: 5 – 7 phút (Phù hợp quy định 5 – 10 phút của Khoa)
* **Mục tiêu điểm số**: Đạt trọn vẹn **8.0/8.0 điểm Công nghệ** (Tổng tích lũy 9.5 điểm, dư 1.5 điểm an toàn dự phòng) + **1.0 điểm Nâng cao** + **2.0 điểm Báo cáo** $\rightarrow$ **10.0/10 ĐIỂM TỐI ĐA**.

---

## 1. BẢNG MỤC TIÊU TIÊU CHÍ CÔNG NGHỆ MINH CHỨNG TRONG VIDEO

| Mã | Tên Tiêu Chí Trong Đề Bài (TS. Lê Trọng Nhân) | Điểm | File Ảnh Minh Chứng | Vị Trí Trong Video |
| :---: | :--- | :---: | :--- | :---: |
| **N07** | Tự triển khai (deploy) ThingsBoard trên máy local bằng Docker | **1.0 (Cộng)**| `captured_picture/N07.png` | **Phân cảnh 1** (0:20 - 0:45) |
| **T05** | Công cụ thu thập dữ liệu, huấn luyện và export ra model TinyML (`train_tinyml.py`) | **1.0** | `captured_picture/T05.png` | **Phân cảnh 1** (0:45 - 1:30) |
| **T04** | Thông tin nội suy từ AI: TinyML chạy trực tiếp trên vi điều khiển ESP32-S3 | **1.0** | `captured_picture/T04_1.jpg`<br/>`captured_picture/T04_2.jpg`<br/>`captured_picture/T04_3.png` | **Phân cảnh 2 & 3** |
| **T08** | IoT Gateway trên PC: nhận telemetry UART từ ESP32-S3, gửi MQTT, nhận RPC điều khiển 2 chiều | **1.0** | `captured_picture/T08.png` | **Phân cảnh 2 & 5** |
| **T09** | Chức năng AI chạy trên IoT Gateway local (Isolation Forest Anomaly Detection) | **1.0** | `captured_picture/T09_1.png`<br/>`captured_picture/T09_2.png` | **Phân cảnh 2 & 3** |
| **T10** | Giao diện giám sát – điều khiển trên IoT Gateway local (`http://localhost:5050`) | **1.0** | `captured_picture/T10.png` | **Phân cảnh 2 & 5** |
| **T11** | Sử dụng template thiết kế Dashboard công nghiệp giám sát và điều khiển từ xa | **1.0** | `captured_picture/T11.png` | **Phân cảnh 2, 3, 5** |
| **T12** | Sử dụng RuleChain để phát triển tính năng thông minh (phân loại 3 cấp độ & tự động kích hoạt) | **1.0** | `captured_picture/T12.png` | **Phân cảnh 3** |
| **T13** | Gửi cảnh báo bằng notification khi dữ liệu vượt ngưỡng (Widget Notification trên Dashboard) | **0.5** | *(Chụp Widget 10 trên Dashboard)* | **Phân cảnh 3** |
| **T15** | IoT Gateway CoreIOT đồng bộ với Gateway local + Cơ chế đệm ngoại tuyến SQLite WAL | **2.0** | *(Chụp log Offline Buffer khi ngắt mạng)* | **Phân cảnh 4** (Trọng tâm) |
| **N06** | Dashboard thiết kế riêng ghi nhận và hiển thị các sự kiện (Event Logging) | **1.0 (Cộng)**| `captured_picture/N06.png` | **Phân cảnh 2 & 4** |

> **Tổng kết điểm số**:
> * Tổng điểm Công nghệ tích lũy: $T04 (1.0) + T05 (1.0) + T08 (1.0) + T09 (1.0) + T10 (1.0) + T11 (1.0) + T12 (1.0) + T13 (0.5) + T15 (2.0) = \mathbf{9.5\text{ điểm}}$.
> * Điểm Công nghệ tính theo trần quy chế: $\min(8.0;\ 9.5) = \mathbf{8.0 / 8.0\text{ điểm}}$ (Dư 1.5 điểm an toàn dự phòng).
> * Điểm Nâng cao tích lũy: $N06 (1.0) + N07 (1.0) = 2.0\text{ điểm} \rightarrow \min(1.0;\ 2.0) = \mathbf{1.0 / 1.0\text{ điểm}}$ tối đa.
> * Điểm Báo cáo: $\mathbf{2.0 / 2.0\text{ điểm}}$.
> * **Tổng điểm toàn diện**: $\mathbf{8.0 + 1.0 + 2.0 = 10.0 / 10\text{ ĐIỂM TUYỆT ĐỐI}}$.

---

## 2. BỐ CỤC KHUNG HÌNH KHI QUAY VIDEO
* **Màn hình quay chính (Screen Capture)**:
  * Bên trái: Cửa sổ Terminal / PowerShell chạy hệ thống.
  * Bên phải: Hai tab trình duyệt:
    * Tab 1: **Local SCADA Web Monitor** (`http://localhost:5050`) gồm 5 thẻ cảm biến và bảng điều khiển.
    * Tab 2: **ThingsBoard Industrial Dashboard** (`http://localhost:9090`) gồm 10 widget cân đối (trong đó có Widget Notification T13 ở dưới cùng).
* **Camera quay phần cứng (Webcam góc nhỏ hoặc Camera điện thoại)**:
  * Mạch **ESP32-S3 YoloUNO** nối cáp USB Type-C với máy tính.
  * Màn hình màu **TFT LCD 320x240** (hiển thị trạng thái SAFE/CRITICAL, thông số cảm biến và % TinyML).
  * Cụm cảm biến: **MQ-2** (Khói/Gas), **Flame Sensor** (Lửa), **DHT11** (Nhiệt/Ẩm).
  * Cơ cấu chấp hành: **Động cơ Servo** (cửa thoát hiểm), **Còi Buzzer**, **Đèn LED cảnh báo**.

---

## 3. CHI TIẾT KỊCH BẢN VÀ LỜI THOẠI TỪNG PHÂN CẢNH

### 🎬 PHÂN CẢNH 1: GIỚI THIỆU & CÔNG CỤ HUẤN LUYỆN TINYML (0:00 – 1:30)
* **Hình ảnh & Thao tác**:
  1. Trình chiếu Slide / Bìa báo cáo: Nêu tên đề tài, giảng viên hướng dẫn (TS. Lê Trọng Nhân), danh sách thành viên nhóm.
  2. Mở ứng dụng **Docker Desktop**: Quay container `thingsboard-local` đang chạy cổng 9090 & 1883 (**Minh chứng N07** - `captured_picture/N07.png`).
  3. Mở Terminal chạy script huấn luyện AI TinyML (**Minh chứng T05** - `captured_picture/T05.png`):
     ```powershell
     python 01_Firmware_EndNode\tinyml\train_tinyml.py
     ```
     * Chỉ chuột vào kết quả in ra: Tập dữ liệu 2,500 mẫu, Accuracy **100.00%**, xuất ra file C Header `tinyml_fire_model.h`.
  4. Chạy script khởi động toàn bộ hệ thống bằng 1 file duy nhất:
     ```powershell
     python run_system.py
     ```
* **Lời thoại thuyết minh mẫu**:
  > *"Kính chào thầy và các bạn! Hôm nay nhóm em xin trình bày video nghiệm thu Bài tập lớn môn Internet of Things. Đề tài của nhóm là: 'Hệ thống báo cháy và điều khiển thoát hiểm thông minh ứng dụng kiến trúc Dual-AI và Gateway đệm ngoại tuyến'.*  
  > *Đầu tiên, về nền tảng hạ tầng, nhóm em tự triển khai toàn bộ máy chủ ThingsBoard CE cục bộ bằng Docker Desktop để đáp ứng tiêu chí nâng cao N07.*  
  > *Tiếp theo, để đáp ứng tiêu chí T05 về công cụ TinyML, nhóm đã phát triển script `train_tinyml.py`. Công cụ này tổng hợp 2,500 mẫu dữ liệu vật lý đa chiều gồm khói, nhiệt độ, độ ẩm và lửa, huấn luyện mô hình phân loại đạt độ chính xác 100%, và tự động xuất ra file mã nguồn C `tinyml_fire_model.h` độc lập để nhúng trực tiếp vào firmware vi điều khiển.*  
  > *Bây giờ, nhóm em khởi động toàn bộ hệ thống chỉ với một lệnh duy nhất: `python run_system.py`. Hệ thống tự động nhận diện mạch ESP32-S3 qua cổng COM và mở đồng thời cả hai bảng điều khiển."*

---

### 🎬 PHÂN CẢNH 2: TRẠNG THÁI AN TOÀN & KIẾN TRÚC DUAL-AI (1:30 – 2:45)
* **Hình ảnh & Thao tác**:
  1. Trình duyệt tự động mở 2 Dashboard:
     * **Tab 1 - Local SCADA Web Monitor** (`http://localhost:5050` - **T10, N06** - `captured_picture/T10.png`, `captured_picture/N06.png`): Chỉ vào 5 ô thẻ: Khói MQ-2 (~180 ADC), Nhiệt độ phòng (~28°C), Cảm biến Lửa (SAFE), Servo (0°), và AI Isolation Forest (NORMAL).
     * **Tab 2 - ThingsBoard Dashboard** (`http://localhost:9090` - **T11, T13** - `captured_picture/T11.png`): Chỉ vào lưới 10 widget được bố trí 24 cột gồm: Đồng hồ khói ADC, Ô trạng thái lửa, Card nhiệt độ phòng có icon nhiệt kế, 2 widget AI Anomaly, biểu đồ Telemetry, 3 switch điều khiển, và **Widget 10: Emergency Notification Feed** đang báo trạng thái an toàn: `[SAFE] System normal. Sensors reading clean air & safe ambient temperature.`
  2. Quay camera vào mạch phần cứng:
     * Màn hình TFT màu hiển thị nền **Màu Xanh ("HE THONG AN TOAN")**.
     * Dòng thứ 4 trên TFT hiển thị: `TinyML: 0.1% (SAFE)` (**Minh chứng T04** - `captured_picture/T04_1.jpg`).
     * Servo ở góc $0^\circ$ (cửa đóng an toàn), còi im lặng, đèn LED tắt.
  3. Chỉ vào Terminal: Dòng telemetry in đều đặn mỗi chu kỳ (**Minh chứng T08** - `captured_picture/T08.png`):
     `MQ-2 ADC: 180 | Lua: KHONG | Nhiet do: 28.5 C | Do am: 65% | AI Risk: 0.1% | Trang thai: AN TOAN`.
* **Lời thoại thuyết minh mẫu**:
  > *"Khi ở điều kiện bình thường, cảm biến MQ-2 đọc không khí sạch khoảng 180 ADC, cảm biến lửa báo 0, nhiệt độ phòng 28.5 độ C.*  
  > *Đặc biệt, hệ thống của nhóm sở hữu kiến trúc Dual-AI: Một mô hình TinyML chạy trực tiếp trên vi điều khiển ESP32-S3 (tiêu chí T04) nội suy ra rủi ro cháy chỉ 0.1% hiển thị trực tiếp trên màn hình TFT; song song đó, một mô hình Isolation Forest chạy trên Local Gateway PC (tiêu chí T09) liên tục đánh giá điểm bất thường Anomaly Score ở mức an toàn 0.05.*  
  > *Toàn bộ dữ liệu được hiển thị trực quan đồng thời trên giao diện SCADA Local 5050 (tiêu chí T10) và ThingsBoard Dashboard công nghiệp 10 widget (tiêu chí T11)."*

---

### 🎬 PHÂN CẢNH 3: KÍCH HOẠT BÁO CHÁY, NOTIFICATION WEB T13 & RULE CHAIN (2:45 – 4:00)
* **Hình ảnh & Thao tác**:
  1. Dùng bật lửa quẹt tạo lửa trước đầu cảm biến Flame Sensor (hoặc xịt khói vào MQ-2).
  2. Quay đồng thời màn hình máy tính và phần cứng:
     * **Tại Mạch ESP32-S3**:
       * Màn hình TFT lập tức đổi sang **Màu Đỏ rực ("CANH BAO CHAY!")** (**Minh chứng T04** - `captured_picture/T04_2.jpg`).
       * Dòng chữ TinyML nhảy vọt: `TinyML: 98.8% (CRITICAL)`!
       * Còi Buzzer hú to, đèn LED đỏ nháy liên tục.
       * Động cơ Servo lập tức quay **$90^\circ$** mở toang cửa thoát hiểm!
     * **Tại ThingsBoard Dashboard (Minh chứng T13)**:
       * **Widget 10 (Emergency Notification Feed)** lập tức bắn ra dòng thông báo khẩn cấp màu đỏ:  
         `[CRITICAL NOTIFICATION] Fire detected! Smoke: 2150 ADC, Temp: 32.5C. Auto lockdown active!`
       * Bảng Alarms của ThingsBoard nhảy dòng báo động đỏ: `FIRE_ALARM_CRITICAL`.
     * **Tại Local Gateway**:
       * Banner đỏ xuất hiện trên giao diện 5050: `ALARM WARNING: HIGH SMOKE CONCENTRATION OR FLAME DETECTED`.
       * Isolation Forest phát hiện bất thường: `Anomaly Flag: 1`, `Anomaly Score: 0.95` (**Minh chứng T09** - `captured_picture/T09_2.png`).
  3. Bấm vào tab **Rule Chain** (`Fire_Alarm_Rule_Chain`) trên ThingsBoard để giải thích luồng xử lý (**Minh chứng T12** - `captured_picture/T12.png`):
     * Chỉ vào Switch Node phân loại 3 cấp độ: `Safe`, `Warning`, `Critical`.
     * Chỉ vào các Node tự động dispatch lệnh RPC: `setServo(90)` để mở cửa thoát hiểm, `setBuzzer(1)` và `setLed(1)`.
  4. Đưa bật lửa ra xa: Môi trường an toàn trở lại $\rightarrow$ Rule Chain tự động Clear Alarm, Widget 10 đổi lại thông báo an toàn màu xanh, Servo quay về $0^\circ$, còi tắt êm ái.
* **Lời thoại thuyết minh mẫu**:
  > *"Bây giờ nhóm em tiến hành kích hoạt cháy thực nghiệm bằng cách quẹt lửa trước cảm biến.*  
  > *Ngay lập tức, thuật toán TinyML trên chip ESP32-S3 phát hiện xác suất cháy đạt 98.8%, màn hình TFT đổi sang màu đỏ rực. Đồng thời, mô hình Isolation Forest trên Gateway cảnh báo Anomaly Score nhảy vọt lên 0.95.*  
  > *Tại ThingsBoard Dashboard, tiêu chí T13 được thể hiện rõ nét qua Widget Notification thời gian thực: Hệ thống lập tức bắn ra thông báo khẩn cấp đỏ rực cảnh báo nguy cơ cháy và quy trình mở cửa thoát hiểm.*  
  > *Đồng thời, bộ não thông minh Rule Chain (tiêu chí T12) phân loại sự kiện vào cấp độ 'Critical', tự động tạo Alarm khẩn cấp và điều phối tức thì 3 lệnh RPC xuống thiết bị: Động cơ Servo lập tức quay 90 độ mở toang cửa thoát hiểm, còi hú to và đèn LED chớp liên tục để cảnh báo sơ tán.*  
  > *Khi ngọn lửa biến mất và môi trường trở lại an toàn, Rule Chain tự động nhận diện và xóa Alarm, trả cửa Servo về vị trí đóng an toàn ban đầu và khôi phục thông báo an toàn trên Dashboard."*

---

### 🎬 PHÂN CẢNH 4: ĐỒNG BỘ COREIOT GATEWAY & CƠ CHẾ ĐỆM NGOẠI TUYẾN SQLITE WAL (4:00 – 5:15)
* **Tiêu chí Đánh giá Trọng tâm**: **T15 (2.0 điểm)** — *IoT Gateway trên CoreIOT đồng bộ toàn diện với IoT Gateway local.*
* **Hình ảnh & Thao tác**:
  1. **Yếu tố 1: Khai báo chuẩn Gateway & Đồng bộ Cấu trúc Thiết bị Con (Topology & Auto-Provisioning)**:
     * Trên ThingsBoard: Mở menu **Device Groups / Devices**, bấm vào thiết bị `FireAlarm_Gateway`:
       * Chỉ chuột vào ô thuộc tính đã tích chọn: **`Is gateway: TRUE`** (Khai báo đúng chuẩn Gateway công nghiệp).
       * Chỉ chuột vào tab **Relations**: Hiển thị quan hệ phân cấp sở hữu thiết bị con: `Contains -> YOLOUNO_FIRE_NODE_01` (được CoreIOT tự động tạo và quản lý dưới Gateway khi nhận topic `v1/gateway/connect` và `v1/gateway/telemetry`).
     * Chỉ chuột vào Terminal Gateway: Hiện rõ các dòng đăng ký chuẩn Gateway API:
       `[Gateway Core] Connected to ThingsBoard Gateway MQTT Broker.`
       `[Gateway Core] Subscribed to Gateway RPC topic: v1/gateway/rpc`
       `[Gateway Core] Registered End-Node: YOLOUNO_FIRE_NODE_01 via v1/gateway/connect`
  2. **Yếu tố 2: Đồng bộ Dữ liệu Uplink & Chịu lỗi Ngoại tuyến (Offline Store & Forward SQLite WAL)**:
     * **Mô phỏng sự cố đứt kết nối mạng giữa Gateway và CoreIOT Cloud**:
       * *Trường hợp A (Nếu kết nối Cloud Online `app.coreiot.io`)*: Tắt Wi-Fi máy tính.
       * *Trường hợp B (Chuẩn nhất - Khi chạy ThingsBoard Local Docker `localhost:1883`)*:  
         > **Lưu ý kỹ thuật quan trọng**: Do ThingsBoard chạy trên Docker localhost (`127.0.0.1`), card mạng ảo Loopback của Windows không phụ thuộc vào sóng Wi-Fi ngoài. Vì vậy, để mô phỏng rớt kết nối broker chuẩn xác và an toàn nhất (không làm rớt mạng trình duyệt), MemBau chỉ cần mở một tab PowerShell gõ:
         > ```powershell
         > docker pause thingsboard-local
         > ```
     * **Quan sát phản ứng tức thời của hệ thống**:
       * Terminal Gateway lập tức hiện dòng cảnh báo:  
         `[CoreIOT Cloud] Connection lost (code: 7). Switching to local offline buffering mode.`
       * Trên giao diện Local SCADA (`http://localhost:5050`): Thanh Navbar đổi sang huy hiệu màu cam **`CoreIOT: Offline (Buffering)`**.
       * Chỉ số **`Buffer: 1, 2, 3, 4, 5...`** nhảy tăng dần theo từng chu kỳ lấy mẫu từ ESP32-S3.
       * Mọi dữ liệu đo đạc vẫn được ghi nhận an toàn 100% vào CSDL SQLite Write-Ahead Logging `gateway_hardware_buffer.db`.
     * **Khôi phục kết nối**:
       * Gõ lệnh khôi phục container (hoặc bật lại Wi-Fi):
         > ```powershell
         > docker unpause thingsboard-local
         > ```
       * Terminal Gateway lập tức kết nối lại và kích hoạt tiến trình đồng bộ bù:  
         `[CoreIOT Cloud] Connected successfully to broker.`  
         `[Buffer Sync] Synchronized X buffered records to CoreIOT via v1/gateway/telemetry.`
       * Trên giao diện SCADA 5050: Huy hiệu đổi lại màu xanh **`CoreIOT: Online`**, bộ đệm được giải phóng về **`Buffer: 0`**.
       * Mở tab ThingsBoard Dashboard: Đồ thị Telemetry History cập nhật đầy đủ toàn bộ các điểm dữ liệu liên tục, vẽ liền mạch 100% không hề bị đứt đoạn hay mất mát bất kỳ gói tin nào.
  3. **Yếu tố 3: Đồng bộ Lệnh Điều khiển Downlink (Gateway RPC Routing 2 Chiều)**:
     * Thao tác bật/tắt thiết bị trên Dashboard ThingsBoard $\rightarrow$ CoreIOT tự động định tuyến lệnh RPC xuống topic `v1/gateway/rpc` $\rightarrow$ Gateway nhận lệnh, chuyển tiếp xuống UART ESP32-S3 và phản hồi trạng thái ngược lại Cloud.
* **Lời thoại thuyết minh mẫu**:
  > *"Kính thưa thầy, tiêu chí T15 là tiêu chí có trọng số cao nhất (2.0 điểm). Để đạt trọn vẹn điểm tối đa, hệ thống của nhóm em không chỉ gửi nhận dữ liệu đơn thuần mà đáp ứng trọn vẹn 3 trụ cột 'Đồng bộ Gateway' theo đúng chuẩn công nghiệp của CoreIOT / ThingsBoard:*  
  > *Thứ nhất là Đồng bộ chuẩn Gateway và Cấu trúc thiết bị con: Thiết bị `FireAlarm_Gateway` trên CoreIOT được cấu hình cờ 'Is gateway', sử dụng bộ Gateway MQTT API chuẩn gồm `v1/gateway/connect`, `v1/gateway/telemetry`, và `v1/gateway/rpc`. Khi Gateway gửi dữ liệu định dạng thiết bị con `YOLOUNO_FIRE_NODE_01`, CoreIOT tự động nhận diện và gắn quan hệ phân cấp cha-con.*  
  > *Thứ hai là Đồng bộ dữ liệu Uplink và Khả năng chịu lỗi ngoại tuyến: Khi nhóm ngắt kết nối mạng Internet, Gateway lập tức chuyển sang chế độ đệm ngoại tuyến SQLite WAL, số bản ghi đệm tăng dần trên SCADA Local. Ngay khi mạng phục hồi, tiến trình `sync_worker` tự động đẩy bù toàn bộ dữ liệu lên CoreIOT qua topic `v1/gateway/telemetry`, đảm bảo tính toàn vẹn 100% không rớt bất kỳ gói tin nào.*  
  > *Thứ ba là Đồng bộ lệnh điều khiển Downlink: Toàn bộ lệnh điều khiển từ xa được CoreIOT định tuyến qua topic `v1/gateway/rpc`, chuyển tiếp xuống vi điều khiển và phản hồi trạng thái 2 chiều với độ trễ tức thời."*

---

### 🎬 PHÂN CẢNH 5: ĐIỀU KHIỂN HAI CHIỀU TỪ XA QUA THINGSBOARD RPC (5:15 – 6:15)
* **Hình ảnh & Thao tác**:
  1. Mở tab **ThingsBoard Industrial Dashboard**:
     * Bấm công tắc **Emergency Partition Door Switch** $\rightarrow$ Servo quay $90^\circ$.
     * Bấm công tắc **Audio Siren Switch** $\rightarrow$ Còi kêu tít tít.
     * Bấm công tắc **Visual Flasher Switch** $\rightarrow$ Đèn LED sáng.
  2. Bấm tắt các công tắc: Thiết bị trở lại trạng thái ban đầu.
  3. Chỉ vào Terminal: In rõ dòng nhận RPC: `[RPC Received] Method: setServo, Params: 90 -> Sent to UART ESP32-S3`.
* **Lời thoại thuyết minh mẫu**:
  > *"Cuối cùng, tiêu chí T08 và T11 được thể hiện qua khả năng điều khiển hai chiều. Người quản trị có thể trực tiếp bật tắt còi, đèn và điều khiển cửa thoát hiểm từ xa ngay trên ThingsBoard Dashboard. Lệnh điều khiển được chuyển tiếp qua Gateway PC, truyền xuống ESP32-S3 qua giao tiếp UART và thực thi với độ trễ gần như bằng 0."*

---

### 🎬 PHÂN CẢNH 6: TỔNG KẾT & KẾT THÚC (6:15 – 6:45)
* Trình chiếu lại Slide tổng kết: Nêu bật các kết quả đã đạt:
  * 8.0/8.0 điểm Công nghệ (T04, T05, T08, T09, T10, T11, T12, T13, T15 - Tổng tích lũy 9.5 điểm).
  * 1.0 điểm Nâng cao (N06, N07).
  * 2.0 điểm Báo cáo kỹ thuật.
  * Tổng điểm dự án: 10.0/10.
* Lời cảm ơn thầy cô và người xem.

---

## 4. CHECKLIST TRƯỚC KHI BẤM MÁY QUAY VIDEO

- [ ] Docker Desktop đã bật và container `thingsboard-local` đang ở trạng thái `Running`.
- [ ] Cáp USB cắm chắc chắn vào bo mạch ESP32-S3 YoloUNO (nhận cổng COM, ví dụ: `COM4`).
- [ ] Chuẩn bị sẵn bật lửa (hoặc que nhang/bông gòn ẩm tạo khói).
- [ ] Đặt sẵn 2 tab trình duyệt: `http://localhost:5050` và `http://localhost:9090`.
- [ ] Mở sẵn cửa sổ Terminal / PowerShell sạch sẽ tại thư mục dự án.
- [ ] Bật phần mềm quay màn hình OBS / Bandicam / Windows Game Bar (`Win + Alt + R`).

---

## 5. HƯỚNG DẪN CHỤP ẢNH MINH CHỨNG CHO TỪNG TIÊU CHÍ (ĐÍNH KÈM BÁO CÁO BTL)

Tất cả các tiêu chí đã hoàn thành đều có ảnh minh chứng sắc nét tương ứng trong thư mục [captured_picture/](file:///c:/261/IOT/CO3054-IoT-BTL-FireAlarm/captured_picture) để chèn vào file Báo cáo `Temple_report.md`:

### 1. Tiêu chí N07: Triển Khai ThingsBoard Local Trên Docker (+1.0 điểm cộng)
* **File ảnh minh chứng**: `captured_picture/N07.png`
* **Điểm cần khoanh đỏ trong ảnh**: Container `thingsboard-local`, trạng thái `Running / Up`, các cổng `0.0.0.0:9090->9090/tcp, 0.0.0.0:1883->1883/tcp`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Triển khai thành công cụm ThingsBoard CE 3.x trên Docker Localhost (cổng 9090 và 1883 MQTT).*

---

### 2. Tiêu chí T05: Công Cụ Huấn Luyện & Xuất Model TinyML (1.0 điểm)
* **File ảnh minh chứng**: `captured_picture/T05.png`
* **Điểm cần khoanh đỏ trong ảnh**:
  * Dòng `Dataset Size: 2500 samples`.
  * Dòng `Overall Accuracy: 100.00%`.
  * Bảng `Confusion Matrix` và `Classification Report`.
  * Dòng thông báo màu xanh: `[OK] Successfully exported TinyML C header to: tinyml_fire_model.h`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Kết quả huấn luyện bộ phân loại TinyML và xuất tự động ra file header C `tinyml_fire_model.h`.*

---

### 3. Tiêu chí T04: Nội Suy AI TinyML Chạy Trực Tiếp Trên ESP32-S3 (1.0 điểm)
* **File ảnh minh chứng**: Gồm **3 ảnh**:
  * `captured_picture/T04_1.jpg`: Chụp cận cảnh màn hình TFT trên mạch ESP32 lúc bình thường.
    * *Khoanh đỏ*: Dòng chữ `TinyML: 0.1% (SAFE)` trên màn hình nền xanh lá.
  * `captured_picture/T04_2.jpg`: Chụp cận cảnh màn hình TFT khi quẹt lửa có cháy.
    * *Khoanh đỏ*: Dòng chữ `TinyML: 98.8% (CRITICAL)` trên màn hình nền đỏ.
  * `captured_picture/T04_3.png`: Chụp dòng log in trên Terminal:
    * *Khoanh đỏ*: `... | AI Risk: 0.1% | Trang thai: AN TOAN` chuyển sang `... | AI Risk: 98.8% | Trang thai: CANH BAO`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Xác suất rủi ro cháy được mô hình TinyML nội suy thời gian thực (< 0.1ms) trực tiếp trên chip ESP32-S3.*

---

### 4. Tiêu chí T08: IoT Gateway Trên PC Giao Tiếp UART Hai Chiều (1.0 điểm)
* **File ảnh minh chứng**: `captured_picture/T08.png`
* **Điểm cần khoanh đỏ trong ảnh**:
  * Dòng mở cổng: `[UART Serial] Opened port COM4 at 115200 baud.`
  * Chiều Upstream (Node $\rightarrow$ PC): `[UART RX ESP32-S3] Smoke: ... | Flame: ... | Temp: ...`
  * Chiều Downstream (PC $\rightarrow$ Node): `[UART Serial TX -> ESP32-S3] {"servo": 90}` hoặc `{"buzzer": 1}`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Luồng truyền nhận dữ liệu UART hai chiều giữa vi điều khiển ESP32-S3 và Local Gateway trên PC.*

---

### 5. Tiêu chí T09: AI Isolation Forest Chạy Trên Local Gateway (1.0 điểm)
* **File ảnh minh chứng**: Gồm **2 ảnh**:
  * `captured_picture/T09_1.png`: Ô thẻ **AI Isolation Forest** trên web hiển thị `NORMAL` kèm `Anomaly Score: 0.05`.
  * `captured_picture/T09_2.png`: Ô thẻ đổi sang `ANOMALY DETECTED` màu đỏ kèm `Anomaly Score: 0.95`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Kết quả phát hiện bất thường đa biến thời gian thực bằng thuật toán Machine Learning Isolation Forest trên Gateway.*

---

### 6. Tiêu chí T10: Giao Diện SCADA Giám Sát & Điều Khiển Cục Bộ (1.0 điểm)
* **File ảnh minh chứng**: `captured_picture/T10.png`
* **Điểm cần khoanh đỏ trong ảnh**:
  * 5 thẻ đo: Khói MQ-2, **Nhiệt độ phòng (Ambient Temperature)**, Cảm biến Lửa, Cửa Servo, AI Isolation Forest.
  * Bảng nút bấm điều khiển tay tại chỗ: Audio Siren Buzzer, Visual Warning LED, Fire Partition Door Servo.
* **Chú thích ảnh báo cáo**: *Hình x.x: Giao diện SCADA Web Monitor chuẩn công nghiệp trên Local Gateway (cổng 5050).*

---

### 7. Tiêu chí T11: Dashboard ThingsBoard Giám Sát & Điều Khiển Từ Xa (1.0 điểm)
* **File ảnh minh chứng**: `captured_picture/T11.png`
* **Điểm cần khoanh đỏ trong ảnh**:
  * Lưới widget cân đối: Đồng hồ Analog đo khói ADC, Ô cảnh báo lửa, **Thẻ Ambient Temperature Value Card (icon nhiệt kế)**, Biểu đồ đa kênh Telemetry History, và 3 công tắc RPC điều khiển từ xa.
* **Chú thích ảnh báo cáo**: *Hình x.x: Industrial Fire Alarm Dashboard trên nền tảng ThingsBoard với đầy đủ widget đo đạc và điều khiển RPC.*

---

### 8. Tiêu chí T12: Rule Chain Thông Minh Phân Loại 3 Cấp Độ (1.0 điểm)
* **File ảnh minh chứng**: `captured_picture/T12.png`
* **Điểm cần khoanh đỏ trong ảnh**:
  * Node `Fire Level Classifier` (Switch TBEL & JS).
  * 3 nhánh rẽ: nhánh `Critical` (nối sang Tạo Alarm, sinh lệnh RPC setServo(90), setBuzzer(1)), nhánh `Warning`, và nhánh `Safe` (nối sang Xóa Alarm và Reset RPC).
* **Chú thích ảnh báo cáo**: *Hình x.x: Sơ đồ cấu hình các Node xử lý trong ThingsBoard Rule Chain tự động hóa kịch bản ứng phó sự cố cháy.*

---

### 9. Tiêu chí T13: Gửi Cảnh Báo Bằng Notification Vượt Ngưỡng Trên Dashboard (0.5 điểm)
* **File ảnh minh chứng**: Chụp **Widget 10 (Emergency Notification Feed)** trên ThingsBoard Dashboard (`http://localhost:9090`):
  * **Ảnh 9A (Lúc bình thường)**: Widget 10 hiển thị màu xanh:  
    `[SAFE] System normal. Sensors reading clean air & safe ambient temperature.`
  * **Ảnh 9B (Lúc có cháy)**: Quẹt bật lửa, Widget 10 lập tức cập nhật thông báo khẩn cấp màu đỏ:  
    `[CRITICAL NOTIFICATION] Fire detected! Smoke: ... ADC, Temp: ... C. Auto lockdown active!`
* **Điểm cần khoanh đỏ trong ảnh**: Widget `T13: Emergency Alarm Notification (In-App Feed)` và dòng thông báo thời gian thực được đẩy từ ESP32-S3 lên Web.
* **Chú thích ảnh báo cáo**: *Hình x.x: Hệ thống cảnh báo Notification thời gian thực trực tiếp trên giao diện ThingsBoard Web Dashboard khi cảm biến vượt ngưỡng nguy hiểm (Tiêu chí T13).*

---

### 10. Tiêu chí T15: IoT Gateway CoreIOT Đồng Bộ Toàn Diện Với Gateway Local (2.0 điểm - Điểm Nhấn)
* **Loại ảnh**: Cần **3 ảnh minh chứng** thể hiện trọn vẹn 3 trụ cột đồng bộ Gateway:
  * **Ảnh 10A (Chuẩn Gateway & Topology Thiết Bị Con)**:
    * Chụp màn hình ThingsBoard mục **Devices $\rightarrow$ FireAlarm_Gateway**:
      * *Khoanh đỏ*: Ô thuộc tính `Is gateway: TRUE`.
      * *Khoanh đỏ*: Tab **Relations** hiển thị quan hệ phân cấp thiết bị con: `Contains -> YOLOUNO_FIRE_NODE_01`.
  * **Ảnh 10B (Đồng Bộ Uplink & Chế Độ Đệm Ngoại Tuyến Khi Mất Mạng)**:
    * Chạy lệnh mô phỏng ngắt broker: `docker pause thingsboard-local` (hoặc ngắt Wi-Fi nếu dùng Cloud online).
    * Chụp màn hình Terminal và giao diện `localhost:5050`:
      * *Khoanh đỏ*: Terminal hiện log: `[CoreIOT Cloud] Connection lost (code: 7). Switching to local offline buffering mode.`
      * *Khoanh đỏ*: Huy hiệu màu cam `CoreIOT: Offline (Buffering)` và chỉ số `Buffer: 5, 6, 7...` tăng dần trong CSDL SQLite WAL `gateway_hardware_buffer.db`.
  * **Ảnh 10C (Đồng Bộ Khôi Phục Liền Mạch & Gateway RPC Downlink)**:
    * Chạy lệnh khôi phục broker: `docker unpause thingsboard-local` (hoặc bật lại Wi-Fi).
    * Chụp Terminal và Dashboard ThingsBoard:
      * *Khoanh đỏ*: Log đồng bộ: `[Buffer Sync] Synchronized X buffered records to CoreIOT via v1/gateway/telemetry.`
      * *Khoanh đỏ*: Log nhận lệnh: `Subscribed to Gateway RPC topic: v1/gateway/rpc`.
      * *Khoanh đỏ*: Biểu đồ Telemetry History vẽ nối tiếp liền mạch 100% không mất mát dữ liệu.
* **Chú thích ảnh báo cáo**: *Hình x.x: Đồng bộ toàn diện IoT Gateway chuẩn CoreIOT gồm cấu trúc phân cấp End Node, cơ chế đệm ngoại tuyến Store & Forward SQLite WAL, và điều khiển Gateway RPC 2 chiều.*

---

### 11. Tiêu chí N06: Giao Diện Dashboard Tự Thiết Kế Ghi Nhận Sự Kiện (+1.0 điểm cộng)
* **File ảnh minh chứng**: `captured_picture/N06.png`
* **Điểm cần khoanh đỏ trong ảnh**: Bảng danh sách log thời gian thực lưu vết các sự kiện kèm timestamp (ví dụ: `[17:30:15] Inbound sensor update`, `[17:30:20] Dispatched command: {"servo": 90}`).
* **Chú thích ảnh báo cáo**: *Hình x.x: Bảng lưu vết sự kiện (Audit Trail Event Log) thời gian thực trên giao diện Local SCADA.*
