 # KỊCH BẢN QUAY VIDEO DEMO BÀI TẬP LỚN IOT (CO3054)
**ĐỀ TÀI: HỆ THỐNG BÁO CHÁY VÀ ĐIỀU KHIỂN THOÁT HIỂM THÔNG MINH**
* **Nền tảng**: ESP32-S3 YoloUNO + Local IoT Gateway (PC/Python) + ThingsBoard (Docker Localhost & CoreIOT)
* **Thời lượng video khuyến nghị**: 6 – 8 phút (Phù hợp quy định 5 – 10 phút của Khoa)
* **Mục tiêu điểm số**: Đạt trọn vẹn **8.0/8.0 điểm Công nghệ** (Tổng tích lũy 9.5 điểm, dư 1.5 điểm an toàn) + **1.0 điểm Nâng cao** + **2.0 điểm Báo cáo** $\rightarrow$ **10.0/10 ĐIỂM TỐI ĐA**.

---

## 1. BẢNG MỤC TIÊU TIÊU CHÍ CÔNG NGHỆ MINH CHỨNG TRONG VIDEO

| Mã | Tên Tiêu Chí Trong Đề Bài (TS. Lê Trọng Nhân) | Điểm | Vị Trí Minh Chứng Trong Video |
| :---: | :--- | :---: | :--- |
| **T05** | Công cụ thu thập dữ liệu, huấn luyện và export ra model TinyML (`train_tinyml.py`) | **1.0** | **Phân cảnh 1** (0:45 - 1:30) |
| **N07** | Tự triển khai (deploy) ThingsBoard trên máy local bằng Docker | **1.0 (Cộng)**| **Phân cảnh 1** (0:20 - 0:45) |
| **T08** | IoT Gateway trên PC: nhận telemetry UART từ ESP32-S3, gửi MQTT, nhận RPC điều khiển 2 chiều | **1.0** | **Phân cảnh 2 & 5** |
| **T04** | Thông tin nội suy từ AI: TinyML chạy trực tiếp trên vi điều khiển ESP32-S3 (`tinyml_fire_model.h`) | **1.0** | **Phân cảnh 2 & 3** |
| **T09** | Chức năng AI chạy trên IoT Gateway local (Isolation Forest Anomaly Detection) | **1.0** | **Phân cảnh 2 & 3** |
| **T10** | Giao diện giám sát – điều khiển trên IoT Gateway local (`http://localhost:5050`) | **1.0** | **Phân cảnh 2 & 5** |
| **T11** | Sử dụng template thiết kế Dashboard công nghiệp giám sát và điều khiển từ xa | **1.0** | **Phân cảnh 2, 3, 5** |
| **T12** | Sử dụng RuleChain để phát triển tính năng thông minh (phân loại 3 cấp độ & tự động kích hoạt) | **1.0** | **Phân cảnh 3** |
| **T13** | Gửi cảnh báo bằng notification tức thời khi vượt ngưỡng qua Telegram Bot API | **0.5** | **Phân cảnh 3** |
| **T15** | IoT Gateway CoreIOT đồng bộ với Gateway local + Cơ chế đệm ngoại tuyến SQLite WAL | **2.0** | **Phân cảnh 4** (Trọng tâm) |
| **N06** | Dashboard thiết kế riêng ghi nhận và hiển thị các sự kiện (Event Logging) | **1.0 (Cộng)**| **Phân cảnh 2 & 4** |

---

## 2. BỐ CỤC KHUNG HÌNH KHI QUAY VIDEO
* **Màn hình quay chính (Screen Capture)**:
  * Bên trái: Cửa sổ Terminal / PowerShell chạy hệ thống.
  * Bên phải: Hai tab trình duyệt:
    * Tab 1: **Local SCADA Web Monitor** (`http://localhost:5050`) gồm 5 thẻ cảm biến và bảng điều khiển.
    * Tab 2: **ThingsBoard Industrial Dashboard** (`http://localhost:9090`) gồm 9 widget cân đối.
* **Camera quay phần cứng (Webcam góc nhỏ hoặc Camera điện thoại)**:
  * Mạch **ESP32-S3 YoloUNO** nối cáp USB Type-C với máy tính.
  * Màn hình màu **TFT LCD 320x240** (hiển thị trạng thái SAFE/CRITICAL, thông số cảm biến và % TinyML).
  * Cụm cảm biến: **MQ-2** (Khói/Gas), **Flame Sensor** (Lửa), **DHT11** (Nhiệt/Ẩm).
  * Cơ cấu chấp hành: **Động cơ Servo** (cửa thoát hiểm), **Còi Buzzer**, **Đèn LED cảnh báo**.
  * Màn hình điện thoại đặt cạnh mạch để quay cảnh nhận tin nhắn **Telegram**.

---

## 3. CHI TIẾT KỊCH BẢN VÀ LỜI THOẠI TỪNG PHÂN CẢNH

### 🎬 PHÂN CẢNH 1: GIỚI THIỆU & CÔNG CỤ TINYML PIPELINE (0:00 – 1:30)
* **Hình ảnh & Thao tác**:
  1. Trình chiếu Slide / Bìa báo cáo: Nêu tên đề tài, giảng viên hướng dẫn (TS. Lê Trọng Nhân), danh sách thành viên nhóm.
  2. Mở ứng dụng **Docker Desktop**: Quay container `thingsboard-local` đang chạy cổng 9090 & 1883 (**Minh chứng N07**).
  3. Mở Terminal chạy script huấn luyện AI TinyML (**Minh chứng T05**):
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
  > *Tiếp theo, để đáp ứng tiêu chí T05 về công cụ TinyML, nhóm đã phát triển script `train_tinyml.py`. Công cụ này tổng hợp 2,500 mẫu dữ liệu vật lý đa chiều gồm khói, nhiệt độ, độ ẩm và lửa, huấn luyện mô hình phân loại đạt độ chính xác 100%, và tự động xuất ra file mã nguồn C `tinyml_fire_model.h` để nạp trực tiếp vào vi điều khiển.*  
  > *Bây giờ, nhóm em khởi động toàn bộ hệ thống chỉ với một lệnh duy nhất: `python run_system.py`. Hệ thống tự động nhận diện mạch ESP32-S3 qua cổng COM và mở đồng thời cả hai bảng điều khiển."*

---

### 🎬 PHÂN CẢNH 2: TRẠNG THÁI AN TOÀN & KIẾN TRÚC DUAL-AI (1:30 – 2:45)
* **Hình ảnh & Thao tác**:
  1. Trình duyệt tự động mở 2 Dashboard:
     * **Tab 1 - Local SCADA Web Monitor** (`http://localhost:5050` - **T10, N06**): Chỉ vào 5 ô thẻ: Khói MQ-2 (~180 ADC), Nhiệt độ phòng (~28°C), Cảm biến Lửa (SAFE), Servo (0°), và AI Isolation Forest (NORMAL).
     * **Tab 2 - ThingsBoard Dashboard** (`http://localhost:9090` - **T11**): Chỉ vào 9 widget được bố trí lưới 24 cột gồm: Đồng hồ khói ADC, Ô trạng thái lửa, Card nhiệt độ phòng có icon nhiệt kế, 2 widget AI Anomaly, biểu đồ Telemetry và 3 switch điều khiển.
  2. Quay camera vào mạch phần cứng:
     * Màn hình TFT màu hiển thị nền **Màu Xanh ("HE THONG AN TOAN")**.
     * Dòng thứ 4 trên TFT hiển thị: `TinyML: 0.1% (SAFE)` (**Minh chứng T04**).
     * Servo ở góc $0^\circ$ (cửa đóng an toàn), còi im lặng, đèn LED tắt.
  3. Chỉ vào Terminal: Dòng telemetry in đều đặn mỗi 500ms:
     `MQ-2 ADC: 180 | Lua: KHONG | Nhiet do: 28.5 C | Do am: 65% | AI Risk: 0.1% | Trang thai: AN TOAN`.
* **Lời thoại thuyết minh mẫu**:
  > *"Khi ở điều kiện bình thường, cảm biến MQ-2 đọc không khí sạch khoảng 180 ADC, cảm biến lửa báo 0, nhiệt độ phòng 28.5 độ C.*  
  > *Đặc biệt, hệ thống của nhóm sở hữu kiến trúc Dual-AI: Một mô hình TinyML chạy trực tiếp trên chip ESP32-S3 (tiêu chí T04) nội suy ra rủi ro cháy chỉ 0.1% hiển thị trực tiếp trên màn hình TFT; song song đó, một mô hình Isolation Forest chạy trên Local Gateway PC (tiêu chí T09) liên tục đánh giá điểm bất thường Anomaly Score ở mức an toàn 0.05.*  
  > *Toàn bộ dữ liệu được hiển thị trực quan đồng thời trên giao diện SCADA Local 5050 (tiêu chí T10) và ThingsBoard Dashboard công nghiệp (tiêu chí T11)."*

---

### 🎬 PHÂN CẢNH 3: KÍCH HOẠT BÁO CHÁY, RULE CHAIN & TELEGRAM SOS (2:45 – 4:30)
* **Hình ảnh & Thao tác**:
  1. Dùng bật lửa quẹt tạo lửa trước đầu cảm biến Flame Sensor (hoặc xịt khói vào MQ-2).
  2. Quay đồng thời màn hình máy tính và phần cứng:
     * **Tại Mạch ESP32-S3**:
       * Màn hình TFT lập tức đổi sang **Màu Đỏ rực ("CANH BAO CHAY!")**.
       * Dòng chữ TinyML nhảy vọt: `TinyML: 98.8% (CRITICAL)`!
       * Còi Buzzer hú to, đèn LED đỏ nháy liên tục.
       * Động cơ Servo lập tức quay **$90^\circ$** mở toang cửa thoát hiểm!
     * **Tại Local Gateway**:
       * Banner đỏ xuất hiện trên giao diện 5050: `ALARM WARNING: HIGH SMOKE CONCENTRATION OR FLAME DETECTED`.
       * Isolation Forest phát hiện bất thường: `Anomaly Flag: 1`, `Anomaly Score: 0.95`.
     * **Tại ThingsBoard Dashboard**:
       * Bảng Alarms nhảy dòng báo động đỏ: `FIRE_ALARM_CRITICAL`.
     * **Tại Điện thoại**:
       * Telegram lập tức phát chuông và nhận được tin nhắn SOS (**Minh chứng T13**):
         `[CRITICAL FIRE ALARM] Device: FireAlarm_Gateway | Smoke: 850 | Flame: 1 | Temp: 32.0 C | AI Anomaly Score: 0.95 | Auto Action: Servo=90 (Closed), Buzzer=ON, LED=ON`.
  3. Bấm vào tab **Rule Chain** (`Fire_Alarm_Rule_Chain`) trên ThingsBoard để giải thích luồng xử lý (**Minh chứng T12**).
* **Lời thoại thuyết minh mẫu**:
  > *"Bây giờ nhóm em tiến hành mô phỏng sự cố cháy bằng cách đưa ngọn lửa lại gần cảm biến.*  
  > *Ngay lập tức, mô hình TinyML trên ESP32-S3 phát hiện nguy cơ cháy vọt lên 98.8%! Mạch tự động chuyển màn hình sang cảnh báo đỏ, còi hú vang, đèn LED sáng và động cơ Servo lập tức quay 90 độ mở cửa thoát hiểm.*  
  > *Tại ThingsBoard, bộ não thông minh Rule Chain (tiêu chí T12) phân loại sự kiện vào cấp độ 'Critical'. Rule Chain tự động ghi nhận báo động, điều phối lệnh RPC và gọi REST API gửi ngay tin nhắn SOS khẩn cấp về Telegram của ban quản lý (tiêu chí T13). Như thầy thấy trên màn hình điện thoại, tin nhắn Telegram hiển thị đầy đủ thông số môi trường và điểm số AI."*

---

### 🎬 PHÂN CẢNH 4: PHỤC HỒI & ĐỆM NGOẠI TUYẾN KHI MẤT MẠNG (4:30 – 6:15)
* **Hình ảnh & Thao tác**:
  1. Đưa bật lửa ra xa: Môi trường an toàn trở lại $\rightarrow$ Rule Chain tự động xóa Alarm, gửi tin nhắn Telegram `[RESOLVED] Fire Alarm Cleared`, Servo quay về $0^\circ$, còi tắt êm ái.
  2. **Thử nghiệm mất mạng (Minh chứng tiêu chí T15 - 2.0 điểm - Điểm nhấn kỹ thuật)**:
     * Rút dây mạng LAN hoặc ngắt kết nối WiFi trên máy tính (hoặc tắt broker).
     * Quan sát giao diện Local SCADA (`localhost:5050`):
       * Huy hiệu Cloud chuyển sang màu đỏ: **"CoreIOT: Offline (Buffering)"**.
     * Quan sát màn hình Terminal:
       * Gateway in dòng thông báo: `Connection lost. Switching to local offline buffering mode.`
       * Dữ liệu telemetry vẫn tiếp tục nhận từ ESP32-S3 và được ghi vào CSDL SQLite Write-Ahead Logging `gateway_hardware_buffer.db`.
       * Huy hiệu Buffer trên web tăng dần: `Buffer: 1, 2, 3, 4, 5...`
     * Cắm lại dây mạng LAN / kết nối lại WiFi:
       * Terminal báo: `Connected successfully to broker.`
       * Tiến trình `sync_worker` tự động phát hiện mạng và in ra: `Synchronized 15 buffered records to CoreIOT.`
       * Toàn bộ dữ liệu trong thời gian mất mạng được đẩy bù trọn vẹn lên ThingsBoard, số Buffer quay về `0`!
* **Lời thoại thuyết minh mẫu**:
  > *"Sau khi môi trường an toàn, hệ thống tự động giải tỏa báo động và còi tắt.*  
  > *Bây giờ, nhóm em xin chứng minh tiêu chí T15 (trị giá 2.0 điểm): Khả năng đồng bộ Gateway và cơ chế lưu đệm ngoại tuyến (Offline Store & Forward). Em tiến hành ngắt kết nối Internet của máy tính.*  
  > *Lúc này, Gateway nhận biết sự cố mất mạng và lập tức chuyển sang chế độ đệm ngoại tuyến. Toàn bộ dữ liệu cảm biến được bảo vệ trong CSDL SQLite chế độ Write-Ahead Logging (WAL) để đảm bảo không bị mất mát dữ liệu.*  
  > *Khi em kết nối mạng trở lại, tiến trình Sync Worker tự động đồng bộ đẩy toàn bộ các bản ghi tồn đọng lên ThingsBoard. Cơ chế này đảm bảo tính toàn vẹn thông tin 100% theo tiêu chuẩn IoT công nghiệp."*

---

### 🎬 PHÂN CẢNH 5: ĐIỀU KHIỂN TAY 2 CHIỀU & TỔNG KẾT ĐIỂM (6:15 – 7:30)
* **Hình ảnh & Thao tác**:
  1. Trên **Local SCADA Web Monitor** (`localhost:5050`) hoặc **ThingsBoard**:
     * Bấm nút **ACTIVATE** còi Buzzer $\rightarrow$ Quay camera vào mạch: Còi kêu ngay lập tức!
     * Bấm nút **SILENCE** $\rightarrow$ Còi tắt!
     * Bấm nút đóng/mở **Servo 90° / 0°** $\rightarrow$ Servo quay theo lệnh RPC (**Minh chứng T08 điều khiển hai chiều**).
  2. Mở file [Báo cáo mẫu](file:///c:/261/IOT/CO3054-IoT-BTL-FireAlarm/02_Local_Gateway/Guideline/Temple_report.md) và trình chiếu Bảng tự đánh giá các yếu tố công nghệ (đạt trọn vẹn 8.0/8.0 điểm công nghệ và 1.0 điểm nâng cao).
* **Lời thoại thuyết minh mẫu**:
  > *"Bên cạnh cơ chế tự động, người vận hành có thể điều khiển trực tiếp các cơ cấu chấp hành từ xa qua giao diện Web SCADA hoặc ThingsBoard Dashboard. Khi em nhấn nút kích hoạt còi hoặc xoay servo, lệnh RPC được truyền tức thời xuống mạch ESP32-S3 qua giao tiếp UART 2 chiều.*  
  > *Tổng kết lại, dự án Báo cháy thông minh của nhóm đã hiện thực thành công vượt mức: 9.5 điểm các tiêu chí công nghệ T04, T05, T08, T09, T10, T11, T12, T13, T15 cùng các tiêu chí nâng cao N06, N07. Nhóm em xin chân thành cảm ơn thầy Lê Trọng Nhân đã theo dõi video demo!"*

---

## 4. CHECKLIST 5 PHÚT TRƯỚC KHI BẤM QUAY
- [ ] ESP32-S3 đã cắm cáp USB vào máy tính (kiểm tra nhận đúng cổng COM, ví dụ COM4).
- [ ] Đã nạp firmware mới nhất: `pio run -d 01_Firmware_EndNode -e yolo_uno --target upload --upload-port COM4 -j 1`.
- [ ] Docker Desktop đang bật và container `thingsboard-local` đang chạy (Port 9090 & 1883).
- [ ] Chuẩn bị sẵn bật lửa (hoặc que nhang).
- [ ] Mở sẵn app Telegram trên điện thoại để nhận thông báo.
- [ ] Bật phần mềm quay màn hình OBS / Bandicam / Windows Game Bar (`Win + Alt + R`).

---

## 5. HƯỚNG DẪN CHỤP ẢNH MINH CHỨNG CHO 11 TIÊU CHÍ (ĐÍNH KÈM BÁO CÁO BTL)

Dưới đây là cẩm nang hướng dẫn chụp ảnh minh chứng sắc nét để chèn vào file Báo cáo `Temple_report.md` (hoặc xuất PDF) theo yêu cầu của thầy Lê Trọng Nhân:

### 1. Tiêu chí N07: Triển Khai ThingsBoard Local Trên Docker (+1.0 điểm cộng)
* **Loại ảnh**: Chụp màn hình máy tính (Screenshot).
* **Cách lấy ảnh**:
  1. Mở phần mềm **Docker Desktop** trên Windows $\rightarrow$ Bấm vào mục **Containers**.
  2. Mở Terminal chạy lệnh: `docker ps` để hiển thị container `thingsboard-local`.
* **Điểm cần khoanh đỏ trong ảnh**: Container `thingsboard-local`, trạng thái `Running / Up`, các cổng `0.0.0.0:9090->9090/tcp, 0.0.0.0:1883->1883/tcp`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Triển khai thành công cụm ThingsBoard CE 3.x trên Docker Localhost (cổng 9090 và 1883 MQTT).*

---

### 2. Tiêu chí T05: Công Cụ Huấn Luyện & Xuất Model TinyML (1.0 điểm)
* **Loại ảnh**: Chụp màn hình Terminal (Screenshot).
* **Cách lấy ảnh**:
  1. Mở Terminal tại thư mục gốc dự án và chạy:
     ```powershell
     python 01_Firmware_EndNode\tinyml\train_tinyml.py
     ```
  2. Chụp toàn bộ bảng kết quả in ra trên màn hình console.
* **Điểm cần khoanh đỏ trong ảnh**:
  * Dòng `Dataset Size: 2500 samples`.
  * Dòng `Overall Accuracy: 100.00%`.
  * Bảng `Confusion Matrix` và `Classification Report`.
  * Dòng thông báo màu xanh: `[OK] Successfully exported TinyML C header to: tinyml_fire_model.h`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Kết quả huấn luyện bộ phân loại TinyML và xuất tự động ra file header C `tinyml_fire_model.h`.*

---

### 3. Tiêu chí T04: Nội Suy AI TinyML Chạy Trực Tiếp Trên ESP32-S3 (1.0 điểm)
* **Loại ảnh**: Cần **2 ảnh** (1 ảnh chụp phần cứng + 1 ảnh chụp Terminal/Log).
* **Cách lấy ảnh**:
  * **Ảnh 3A (Phần cứng lúc bình thường)**: Dùng điện thoại chụp cận cảnh màn hình TFT trên mạch ESP32.
    * *Khoanh đỏ*: Dòng chữ `TinyML: 0.1% (SAFE)` trên màn hình nền xanh lá.
  * **Ảnh 3B (Phần cứng khi có cháy)**: Quẹt bật lửa trước cảm biến lửa, chụp màn hình TFT chuyển sang màu đỏ.
    * *Khoanh đỏ*: Dòng chữ `TinyML: 98.8% (CRITICAL)` trên màn hình nền đỏ.
  * **Ảnh 3C (Log Serial)**: Chụp màn hình dòng log in trên Terminal:
    `... | AI Risk: 0.1% | Trang thai: AN TOAN` nhảy sang `... | AI Risk: 98.8% | Trang thai: CANH BAO`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Xác suất rủi ro cháy được mô hình TinyML nội suy thời gian thực (< 0.1ms) trực tiếp trên chip ESP32-S3.*

---

### 4. Tiêu chí T08: IoT Gateway Trên PC Giao Tiếp UART Hai Chiều (1.0 điểm)
* **Loại ảnh**: Chụp màn hình Terminal chạy `run_system.py`.
* **Cách lấy ảnh**:
  1. Chạy `python run_system.py`.
  2. Bấm nút bật còi hoặc mở Servo từ web để sinh ra log 2 chiều.
* **Điểm cần khoanh đỏ trong ảnh**:
  * Dòng mở cổng: `[UART Serial] Opened port COM4 at 115200 baud.`
  * Chiều Upstream (Node $\rightarrow$ PC): `[UART RX ESP32-S3] Smoke: ... | Flame: ... | Temp: ...`
  * Chiều Downstream (PC $\rightarrow$ Node): `[UART Serial TX -> ESP32-S3] {"servo": 90}` hoặc `{"buzzer": 1}`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Luồng truyền nhận dữ liệu UART hai chiều giữa vi điều khiển ESP32-S3 và Local Gateway trên PC.*

---

### 5. Tiêu chí T09: AI Isolation Forest Chạy Trên Local Gateway (1.0 điểm)
* **Loại ảnh**: Chụp màn hình giao diện Local SCADA (`http://localhost:5050`) và Terminal.
* **Cách lấy ảnh**:
  1. Khi môi trường bình thường: Chụp ô thẻ **AI Isolation Forest** hiển thị `NORMAL` kèm `Anomaly Score: 0.05`.
  2. Khi quẹt lửa/thổi khói: Chụp ô thẻ đổi sang `ANOMALY DETECTED` màu đỏ kèm `Anomaly Score: 0.95`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Kết quả phát hiện bất thường đa biến thời gian thực bằng thuật toán Machine Learning Isolation Forest trên Gateway.*

---

### 6. Tiêu chí T10: Giao Diện SCADA Giám Sát & Điều Khiển Cục Bộ (1.0 điểm)
* **Loại ảnh**: Chụp toàn màn hình trình duyệt trang `http://localhost:5050`.
* **Cách lấy ảnh**: Mở trình duyệt ở chế độ toàn màn hình (`F11`), chụp trọn vẹn giao diện Keen Dashboards.
* **Điểm cần khoanh đỏ trong ảnh**:
  * 5 thẻ đo: Khói MQ-2, **Nhiệt độ phòng (Ambient Temperature)**, Cảm biến Lửa, Cửa Servo, AI Isolation Forest.
  * Bảng nút bấm điều khiển tay tại chỗ: Audio Siren Buzzer, Visual Warning LED, Fire Partition Door Servo.
* **Chú thích ảnh báo cáo**: *Hình x.x: Giao diện SCADA Web Monitor chuẩn công nghiệp trên Local Gateway (cổng 5050).*

---

### 7. Tiêu chí T11: Dashboard ThingsBoard Giám Sát & Điều Khiển Từ Xa (1.0 điểm)
* **Loại ảnh**: Chụp toàn màn hình trình duyệt trang `http://localhost:9090/dashboards/47c220e0-e55d-11f1-b536-af039a103c55`.
* **Điểm cần khoanh đỏ trong ảnh**:
  * Lưới 9 widget cân đối: Đồng hồ Analog đo khói ADC, Ô cảnh báo lửa, **Thẻ Ambient Temperature Value Card (icon nhiệt kế)**, Biểu đồ đa kênh Telemetry History, và 3 công tắc RPC điều khiển từ xa.
* **Chú thích ảnh báo cáo**: *Hình x.x: Industrial Fire Alarm Dashboard trên nền tảng ThingsBoard với đầy đủ widget đo đạc và điều khiển RPC.*

---

### 8. Tiêu chí T12: Rule Chain Thông Minh Phân Loại 3 Cấp Độ (1.0 điểm)
* **Loại ảnh**: Chụp màn hình giao diện Rule Chain trên ThingsBoard: `http://localhost:9090/ruleChains/5f1b3a20-e62e-11f1-909b-e971979a256c`.
* **Điểm cần khoanh đỏ trong ảnh**:
  * Node `Fire Level Classifier` (Switch TBEL & JS).
  * 3 nhánh rẽ: nhánh `Critical` (nối sang Tạo Alarm, sinh lệnh RPC setServo(90), setBuzzer(1)), nhánh `Warning`, và nhánh `Safe` (nối sang Xóa Alarm và Reset RPC).
* **Chú thích ảnh báo cáo**: *Hình x.x: Sơ đồ cấu hình 21 Node xử lý trong ThingsBoard Rule Chain tự động hóa kịch bản ứng phó sự cố cháy.*

---

### 9. Tiêu chí T13: Gửi Cảnh Báo Tức Thời Qua Telegram Bot (0.5 điểm)
* **Loại ảnh**: Chụp màn hình ứng dụng Telegram trên điện thoại hoặc máy tính.
* **Cách lấy ảnh**: Kích hoạt ngọn lửa trước cảm biến để nhận tin nhắn cảnh báo cứu hỏa.
* **Điểm cần khoanh đỏ trong ảnh**:
  * Tin nhắn báo cháy: `[CRITICAL FIRE ALARM] Device: FireAlarm_Gateway | Smoke: ... ppm | Flame: 1 | Temp: ... C | AI Anomaly Score: 0.95`.
  * Tin nhắn giải tỏa: `[RESOLVED] Fire Alarm Cleared - System Safe`.
* **Chú thích ảnh báo cáo**: *Hình x.x: Thông báo khẩn cấp tức thời gửi qua Telegram Bot API kèm đầy đủ thông số cảm biến và điểm AI.*

---

### 10. Tiêu chí T15: Gateway Đồng Bộ & Cơ Chế Đệm Ngoại Tuyến SQLite WAL (2.0 điểm - Điểm Nhấn)
* **Loại ảnh**: Cần **2 ảnh chụp Terminal & Web khi ngắt mạng**:
  * **Ảnh 10A (Khi mất mạng)**:
    * Rút dây mạng/ngắt WiFi.
    * Chụp Terminal hiện log: `Connection lost. Switching to local offline buffering mode.`
    * Giao diện `localhost:5050` hiển thị huy hiệu: `CoreIOT: Offline (Buffering)` và `Buffer: 5, 6, 7...`
  * **Ảnh 10B (Khi có mạng lại)**:
    * Cắm lại dây mạng.
    * Chụp Terminal hiện log: `Connected successfully to broker.` và `Synchronized X buffered records to CoreIOT.`
* **Chú thích ảnh báo cáo**: *Hình x.x: Cơ chế Store & Forward đệm ngoại tuyến bằng CSDL SQLite Write-Ahead Logging (WAL) đảm bảo tính toàn vẹn dữ liệu khi mất kết nối Cloud.*

---

### 11. Tiêu chí N06: Giao Diện Dashboard Tự Thiết Kế Ghi Nhận Sự Kiện (+1.0 điểm cộng)
* **Loại ảnh**: Chụp vùng bảng **Real-Time Station Event Log** trên giao diện `http://localhost:5050`.
* **Điểm cần khoanh đỏ trong ảnh**: Bảng danh sách log thời gian thực lưu vết các sự kiện kèm timestamp (ví dụ: `[17:30:15] Inbound sensor update`, `[17:30:20] Dispatched command: {"servo": 90}`).
* **Chú thích ảnh báo cáo**: *Hình x.x: Bảng lưu vết sự kiện (Audit Trail Event Log) thời gian thực trên giao diện Local SCADA.*

