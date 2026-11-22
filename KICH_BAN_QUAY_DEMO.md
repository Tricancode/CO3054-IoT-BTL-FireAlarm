# KỊCH BẢN QUAY VIDEO DEMO BÀI TẬP LỚN IOT (CO3054)
**ĐỀ TÀI: HỆ THỐNG BÁO CHÁY VÀ ĐIỀU KHIỂN THOÁT HIỂM THÔNG MINH**
* **Nền tảng**: ESP32-S3 (YoloUNO) + Local Gateway (PC/Python) + ThingsBoard (Docker & Cloud)
* **Thời lượng đề xuất**: 6 – 8 phút (Chuẩn theo yêu cầu Đề.md: 5–10 phút)
* **Mục tiêu**: Chứng minh đạt trọn vẹn **7.5 điểm công nghệ** (T08, T09, T10, T11, T12, T13, T15) + **Điểm cộng nâng cao** (N06, N07).

---

## TỔNG HỢP CÁC TIÊU CHÍ MINH CHỨNG TRONG VIDEO

| Mã Tiêu Chí | Yếu tố công nghệ đã hiện thực | Phân cảnh trong Video | Điểm |
| :---: | :--- | :--- | :---: |
| **N07** | Tự triển khai (deploy) ThingsBoard trên máy local bằng Docker | Phân cảnh 1: Khởi động hệ thống | 1.0 (Cộng) |
| **T05** | Công cụ thu thập dữ liệu, huấn luyện và export ra model TinyML (`train_tinyml.py`) | Phân cảnh 1: Công cụ AI | 1.0 |
| **T04** | Thông tin được nội suy từ AI: TinyML chạy trực tiếp trên ESP32-S3 (`tinyml_fire_model.h`) | Phân cảnh 2 & 3 | 1.0 |
| **T08** | IoT Gateway trên PC: nhận telemetry UART từ ESP32-S3, gửi MQTT lên Cloud, nhận lệnh RPC | Phân cảnh 2 & 3 | 1.0 |
| **T09** | AI Anomaly Detection (Isolation Forest) chạy tại Local Gateway | Phân cảnh 2 & 3 | 1.0 |
| **T10** | Giao diện SCADA Web Monitor tại chỗ (`localhost:5050`) giám sát & điều khiển tay | Phân cảnh 2 & 5 | 1.0 |
| **T11** | ThingsBoard Industrial Dashboard trực quan hóa số liệu và điều khiển từ xa | Phân cảnh 2, 3, 5 | 1.0 |
| **T12** | Rule Chain thông minh: Phân loại 3 cấp độ (Safe/Warn/Crit) & tự động kích hoạt RPC | Phân cảnh 3 | 1.0 |
| **T13** | Gửi cảnh báo notification tức thời qua Telegram Bot API khi có cháy | Phân cảnh 3 | 0.5 |
| **T15** | Đồng bộ Gateway CoreIOT + Cơ chế đệm ngoại tuyến (Offline SQLite Store & Forward) | Phân cảnh 4 | 2.0 |
| **N06** | Dashboard thiết kế riêng ghi nhận và hiển thị các sự kiện (Event Logging) | Phân cảnh 2 & 4 | 1.0 (Cộng) |

---

## BỐ CỤC KHUNG HÌNH (GỢI Ý KHI QUAY)
* **Nửa màn hình trái**: Màn hình máy tính hiển thị Terminal chạy lệnh, giao diện `http://localhost:5050` (Local SCADA) và `http://localhost:9090` (ThingsBoard Dashboard).
* **Nửa màn hình phải (hoặc Webcam PIP)**: Quay cận cảnh mô hình phần cứng gồm:
  * Mạch ESP32-S3 YoloUNO cắm USB vào PC.
  * Màn hình màu TFT hiển thị trạng thái xanh/đỏ và thông số cảm biến.
  * Cảm biến khói MQ-2, cảm biến lửa Flame Sensor, cảm biến nhiệt DHT11.
  * Cơ cấu chấp hành: Động cơ Servo (cửa thoát hiểm), Còi Buzzer, Đèn LED cảnh báo.
  * Màn hình điện thoại mở sẵn ứng dụng Telegram nhận tin nhắn.

---

## CHI TIẾT KỊCH BẢN TỪNG PHÂN CẢNH

### PHÂN CẢNH 1: GIỚI THIỆU & KHỞI ĐỘNG HỆ THỐNG (0:00 - 1:15)
* **Hình ảnh hiển thị**:
  1. Giới thiệu đề tài, danh sách thành viên nhóm và sơ đồ khối 3 lớp: End-Node (ESP32-S3) $\rightarrow$ Local Gateway (PC) $\rightarrow$ Cloud (ThingsBoard).
  2. Bật Docker Desktop, chỉ vào container `thingsboard-local` đang chạy cổng 9090 & 1883 (**Minh chứng N07**).
  3. Mở Terminal tại thư mục gốc dự án và chạy đúng 1 lệnh duy nhất:
     ```powershell
     python run_system.py
     ```
* **Lời thoại thuyết minh**:
  > *"Kính chào thầy và các bạn! Hôm nay nhóm em xin trình bày video demo Bài tập lớn môn Internet of Things. Đề tài của nhóm là 'Hệ thống báo cháy và điều khiển thoát hiểm thông minh'.*  
  > *Hệ thống của nhóm gồm 3 lớp hoàn chỉnh: Node phần cứng ESP32-S3 YoloUNO, Local IoT Gateway chạy trên máy tính, và nền tảng ThingsBoard do nhóm tự triển khai bằng Docker trên máy local để đạt điểm nâng cao N07.*  
  > *Toàn bộ hệ thống được khởi động thông qua một file runner duy nhất `run_system.py`. Gateway sẽ tự động phát hiện cổng COM của mạch ESP32-S3, kết nối tới Broker MQTT và mở đồng thời cả hai giao diện giám sát."*

---

### PHÂN CẢNH 2: TRẠNG THÁI BÌNH THƯỜNG & AI LOCAL GATEWAY (1:15 - 2:30)
* **Hình ảnh hiển thị**:
  1. Trình duyệt tự động mở ra 2 tab:
     * Tab 1: **Local SCADA Web Monitor** (`http://localhost:5050`) (**Minh chứng T10, N06**).
     * Tab 2: **ThingsBoard Industrial Dashboard** (`http://localhost:9090`) (**Minh chứng T11**).
  2. Quay phần cứng:
     * Màn hình TFT trên mạch sáng màu xanh lá: **"HE THONG AN TOAN"**.
     * Servo giữ ở góc $0^\circ$ (cửa đóng bình thường).
     * Còi im lặng, đèn LED tắt.
  3. Zoom vào Terminal và Dashboard:
     * Dòng log: `[UART RX ESP32-S3] Smoke: 150 | Flame: 0 | Temp: 28.5 C | Anomaly: 0`.
     * Đồng hồ đo khói hiển thị giá trị thực tế (~150 ADC).
     * Điểm số **AI Anomaly Detection** (Isolation Forest) đang hiển thị an toàn (~0.05 - 0.15) (**Minh chứng T09**).
* **Lời thoại thuyết minh**:
  > *"Khi ở điều kiện bình thường, cảm biến khói MQ-2 đọc giá trị không khí sạch khoảng 150 ADC, cảm biến lửa báo 0. Màn hình LCD trên mạch hiển thị trạng thái An toàn màu xanh, còi và đèn đều tắt, servo ở vị trí 0 độ.*  
  > *Tại Local Gateway, dữ liệu nhận qua UART được đưa ngay vào mô hình học máy Isolation Forest (đáp ứng tiêu chí T09). Mô hình liên tục đánh giá đa biến gồm khói, lửa và nhiệt độ. Lúc này điểm bất thường AI Anomaly Score xấp xỉ 0, hệ thống phân loại là Normal.*  
  > *Giao diện Local Monitor trên cổng 5050 đáp ứng tiêu chí T10 được thiết kế theo chuẩn Keen Dashboards, cho phép theo dõi toàn bộ trạng thái cục bộ tại nhà máy."*

---

### PHÂN CẢNH 3: KÍCH HOẠT SỰ CỐ CHÁY & THÔNG MINH RULE CHAIN (2:30 - 4:15)
* **Thao tác thực tế**:
  1. Dùng bật lửa quẹt tạo lửa trước cảm biến Flame Sensor hoặc thổi khí gas/khói vào đầu cảm biến MQ-2 (ADC vọt lên $> 1800$).
  2. Quan sát phản ứng đồng thời của toàn bộ hệ thống:
     * **Tại Mạch phần cứng**: Màn hình TFT chuyển ngay sang **Màu Đỏ ("CANH BAO CHAY!")**, còi Buzzer hú to, đèn LED đỏ nhấp nháy, động cơ Servo lập tức quay **$90^\circ$** mở cửa thoát hiểm.
     * **Tại Local Gateway**: Log hiển thị `Flame: 1`, `Anomaly: 1` với `Anomaly Score: 0.95`!
     * **Tại ThingsBoard Dashboard**: Cột khói nhảy vọt, đèn cảnh báo Fire Alarm nhấp nháy đỏ, mục Alarms xuất hiện dòng báo động `FIRE_ALARM_CRITICAL`.
     * **Tại Điện thoại**: Telegram ting ting nhận được tin nhắn cảnh báo cứu hỏa tức thời (**Minh chứng T13**).
  3. Mở tab **Rule Chain** trên ThingsBoard (`Fire_Alarm_Rule_Chain`) để giải thích luồng xử lý (**Minh chứng T12**).
* **Lời thoại thuyết minh**:
  > *"Bây giờ nhóm em tiến hành giả lập sự cố cháy bằng cách đưa ngọn lửa lại gần cảm biến.*  
  > *Ngay lập tức, cảm biến lửa phát hiện tín hiệu! Tại Node ESP32-S3, màn hình lập tức chuyển sang màu đỏ báo động, còi hú vang, đèn LED sáng và động cơ Servo lập tức quay 90 độ để mở chốt cửa thoát hiểm khẩn cấp.*  
  > *Đồng thời, gói tin được đẩy lên ThingsBoard. Bộ não Rule Chain (tiêu chí T12) lập tức kích hoạt nhánh 'Critical'. Rule Chain tự động tạo Alarm khẩn cấp, bắn lệnh RPC xác nhận điều khiển phần cứng và gọi REST API gửi ngay tin nhắn cảnh báo đến Telegram của ban quản lý (tiêu chí T13). Như thầy thấy trên điện thoại, tin nhắn Telegram ghi rõ tên thiết bị, nồng độ khói, nhiệt độ và điểm số AI Anomaly!"*

---

### PHÂN CẢNH 4: KHÔI PHỤC AN TOÀN & CƠ CHẾ ĐỆM NGOẠI TUYẾN OFFLINE (4:15 - 6:00)
* **Thao tác thực tế**:
  1. Đưa ngọn lửa ra xa $\rightarrow$ Môi trường trở về an toàn $\rightarrow$ Rule Chain tự động xóa Alarm, gửi tin nhắn Telegram `[RESOLVED] Fire Alarm Cleared`, Servo quay về $0^\circ$, còi tắt.
  2. **Thử nghiệm mất mạng (Minh chứng tiêu chí T15 - 2.0 điểm)**:
     * Rút dây mạng hoặc ngắt kết nối Internet/tắt tạm broker.
     * Trên giao diện Local Monitor (`localhost:5050`), huy hiệu Cloud chuyển sang **"OFFLINE - LOCAL BUFFERING"**.
     * Xem màn hình console: Gateway thông báo chuyển sang chế độ lưu đệm SQLite Write-Ahead Logging (`gateway_hardware_buffer.db`).
     * Chỉ vào số đếm: `Buffer Count: 5, 6, 7...` tăng dần khi có dữ liệu mới.
     * Bật lại mạng Internet / Cloud: Gateway báo `Connected successfully`. Worker nền `sync_worker` tự động đồng bộ đẩy toàn bộ các bản ghi lưu đệm lên ThingsBoard mà không mất gói tin nào!
* **Lời thoại thuyết minh**:
  > *"Sau khi dập tắt lửa, hệ thống tự động đưa cơ cấu chấp hành về trạng thái an toàn và gửi thông báo giải tỏa báo động qua Telegram.*  
  > *Tiếp theo, nhóm xin chứng minh tiêu chí T15: Cơ chế đồng bộ Gateway và đệm dữ liệu ngoại tuyến khi đứt cáp mạng. Nhóm ngắt kết nối mạng lên Cloud. Lúc này, Gateway phát hiện mất kết nối và lập tức kích hoạt bộ lưu đệm CSDL SQLite WAL cục bộ. Toàn bộ dữ liệu cảm biến vẫn được ghi nhận đầy đủ vào database mà không bị mất mát.*  
  > *Khi kết nối mạng được phục hồi, tiến trình Sync Worker tự động đồng bộ toàn bộ dữ liệu tồn đọng lên ThingsBoard, đảm bảo tính toàn vẹn thông tin theo tiêu chuẩn công nghiệp."*

---

### PHÂN CẢNH 5: ĐIỀU KHIỂN TAY HAI CHIỀU & TỔNG KẾT (6:00 - 7:30)
* **Thao tác thực tế**:
  1. Trên giao diện **ThingsBoard Dashboard** hoặc **Local SCADA Web Monitor**:
     * Bấm nút gạt **Servo: 90 / 0** $\rightarrow$ Quay camera vào mạch, Servo quay ngay lập tức theo lệnh.
     * Bấm nút gạt **Buzzer: ON / OFF** $\rightarrow$ Còi kêu / tắt theo lệnh RPC downstream (**Minh chứng T08 hai chiều**).
  2. Mở file báo cáo và trình chiếu bảng tự đánh giá điểm (đạt đủ 8 điểm công nghệ và điểm cộng nâng cao).
* **Lời thoại thuyết minh**:
  > *"Ngoài khả năng tự động hóa, người vận hành có thể điều khiển trực tiếp các cơ cấu chấp hành từ xa thông qua giao diện Web SCADA hoặc ThingsBoard Dashboard. Khi nhóm nhấn nút kích hoạt còi hoặc mở servo, lệnh RPC được gửi qua Gateway và truyền thẳng xuống mạch UART để thực thi tức thời.*  
  > *Tổng kết lại, dự án Báo cháy của nhóm đã hoàn thành xuất sắc các tiêu chí: T08, T09, T10, T11, T12, T13, T15 cùng các tiêu chí nâng cao N06, N07. Em xin chân thành cảm ơn thầy đã theo dõi video demo!"*

---

## CHECKLIST TRƯỚC KHI BẮT ĐẦU BẤM QUAY
- [ ] ESP32-S3 đã cắm vào cổng USB (kiểm tra nhận đúng COM4 hoặc Auto-detect).
- [ ] Docker Desktop đã bật và container `thingsboard-local` đang chạy (Port 9090).
- [ ] Chuẩn bị sẵn 1 chiếc bật lửa (hoặc que nhang có khói) để kích hoạt cảm biến.
- [ ] Mở sẵn app Telegram trên điện thoại để nhận thông báo.
- [ ] Mở sẵn phần mềm quay màn hình (OBS Studio hoặc Bandicam / Windows Game Bar `Win + G`).
