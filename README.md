# NIR Size Sorting — 4 Slot Inference

Hệ thống phân loại size (S/L) và defect/pass cho chanh dây, chạy trên PC
công nghiệp: camera Huaray (IMV SDK) → YOLOv8-seg (ONNX) → PLC Mitsubishi
FX3U qua Modbus RTU, xử lý song song 4 slot.

Chỉ cần chạy **một file duy nhất**:

```bash
python main.py
```

---

## 1. Yêu cầu phần cứng / phần mềm

| Thành phần | Bắt buộc | Ghi chú |
|---|---|---|
| Python 3.12 (64-bit) | có | Đã kiểm chứng trên 3.12.6. 3.10/3.11 cũng chạy được |
| Huaray MV Viewer SDK | có (nếu dùng camera) | Cung cấp `MVSDKmd.dll` |
| Camera Huaray/Irayple GigE | có (nếu chạy thật) | 2448×2048 |
| PLC FX3U + cáp RS-485/USB | có (nếu chạy thật) | Modbus RTU 9600 8N1, slave ID 1 |
| GPU NVIDIA | không | Mặc định chạy CPU. Muốn dùng GPU xem mục 6 |

Không có camera/PLC vẫn test được phần AI bằng `python classifier.py <ảnh>`.

---

## 2. Cài đặt trên máy mới

### 2.1. Tải code về

```bash
git clone https://github.com/quanqh6969-alt/passion-fruit.git
cd passion-fruit
```

Không dùng git thì vào trang repo → nút xanh **Code** → **Download ZIP** →
giải nén → mở terminal trong thư mục vừa giải nén.

### 2.2. Tạo môi trường ảo và cài thư viện

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Repo đã kèm sẵn `best.onnx` nên có thể cài nhẹ hơn bằng cách bỏ 3 dòng
`torch` / `onnx` / `onnxslim` trong `requirements.txt` (tiết kiệm ~2.5 GB).
Chỉ cần chúng khi muốn tự export lại `best.pt` → `best.onnx`.

### 2.3. Cài SDK camera

Cài **Huaray MV Viewer** (bản x64) từ nhà cung cấp camera. `IMVApi.py`
nạp DLL từ đường dẫn cố định:

```
C:\Program Files\HuarayTech\MV Viewer\Runtime\x64\MVSDKmd.dll
```

Nếu cài vào ổ/thư mục khác thì sửa `_DLL_DIR` trong `IMVApi.py`.
Mở MV Viewer thấy camera là SDK đã ổn.

### 2.4. Sửa cấu hình cho máy mới

Mở `config.py`, kiểm tra 2 chỗ hay phải đổi nhất:

```python
MODBUS_PORT = "COM4"        # Device Manager -> Ports (COM & LPT)
CAMERA_INDEX = 0            # nếu có nhiều camera
```

### 2.5. Chạy

```bash
python main.py
```

Ctrl+C để dừng. Log ghi ra `logs/` và in ra màn hình. Ảnh kết quả lưu vào
`captured_images/` (cả hai thư mục tự tạo, đã bị `.gitignore` bỏ qua).

---

## 3. Kiểm tra từng phần khi có lỗi

Mỗi module chạy độc lập được, giúp khoanh vùng lỗi nhanh:

```bash
python camera.py                 # chụp 1 tấm -> captured_images/test_capture.jpg
python classifier.py <ảnh>       # in PASS/DEFECT, size, area_ratio
python plc_client.py             # đọc D101-D130, chạy heartbeat 5s
python gate_settings.py          # xem D222-D225 hiện tại
python gate_settings.py --write  # ghi theo config.py rồi đọc lại xác nhận
```

Thứ tự chẩn đoán khi `main.py` báo "Initialization failed": chạy
`classifier.py` → `camera.py` → `plc_client.py`, cái nào fail thì lỗi ở đó.

---

## 4. Cấu trúc file

| File | Vai trò |
|---|---|
| `main.py` | Entry point duy nhất |
| `config.py` | **Toàn bộ tham số — chỉ cần sửa file này** |
| `app.py` | Vòng lặp chính, state machine 4 slot (level-trigger) |
| `slot_processor.py` | Xử lý 1 slot: capture → classify → trả kết quả PLC |
| `camera.py` | Camera Huaray IMV SDK, free-running |
| `classifier.py` | Load ONNX, phân loại defect/pass + size S/L |
| `plc_client.py` | Modbus RTU + heartbeat thread |
| `gate_settings.py` | Ghi/giám sát D222–D225 (delay + độ rộng xung gate) |
| `image_saver.py` | Vẽ overlay và lưu ảnh ở thread riêng |
| `logger_setup.py` | Logging dùng chung (file + console, UTF-8) |
| `IMVApi.py`, `IMVDefines.py` | Wrapper ctypes của Huaray SDK |
| `best.pt`, `best.onnx` | Model YOLOv8-seg đã train (`imgsz=1280`) |

---

## 5. Thông số quan trọng

**Ngưỡng size** — dùng **tỉ lệ diện tích**, không dùng số pixel:

```python
SIZE_THRESHOLD_RATIO = 0.0733     # area_px / (img_w * img_h)
```

Đo từ 143 ảnh thật ở 2448×2048: nhóm nhỏ 0.0404–0.0627 (trung vị 0.0499),
nhóm lớn 0.0839–0.1212 (trung vị 0.1005) — hai nhóm tách hẳn nhau, ngưỡng
0.0733 nằm giữa khoảng trống. Vì `masks.xy` của ultralytics trả về theo hệ
toạ độ **ảnh gốc**, số pixel tuyệt đối đổi theo độ phân giải còn tỉ lệ thì
không → đổi camera hay đổi `imgsz` vẫn dùng được cùng ngưỡng.

**`ONNX_IMG_SIZE = 1280`** phải khớp `imgsz` lúc train. Đổi số này mà không
export lại model sẽ làm giảm độ chính xác.

**Gate settings (D222–D225)** — trong ladder các register này được gán sau
`M8002` (chỉ chạy 1 scan khi PLC STOP→RUN). Python ghi đè được, nhưng mỗi
lần PLC restart thì ladder ghi lại giá trị mặc định. Vì vậy có watchdog đọc
lại mỗi 2 s, phát hiện lệch thì ghi lại và log warning. Đơn vị timer FX3U:
1 count = 100 ms (60 = 6.0 s).

**Hiệu năng** — ONNX ở `imgsz=1280` trên CPU mất khoảng 2.4–2.9 s/ảnh, với
`NUM_CAPTURES=2` là ~5–6 s mỗi vật; 4 slot dùng chung CPU nên còn chậm hơn.
Muốn nhanh hơn thì chuyển sang GPU — xem mục 6.

---

## 6. Chạy bằng GPU (NVIDIA)

Trong code **chỉ đổi một dòng** trong `config.py`:

```python
ONNX_DEVICE = 0          # thay cho "cpu"
```

`0` = GPU đầu tiên, `"cuda:1"` = GPU thứ hai, `"cpu"` = quay lại CPU.
Không phải sửa `classifier.py` hay export lại model — `best.onnx` chạy được
cả CPU và GPU, cùng một file.

Nhưng đổi dòng đó **chưa đủ**. Môi trường phải có đủ 3 thứ, thiếu một cái là
code tự lùi về CPU (kèm warning trong log, không crash):

### 6.1. Driver + CUDA

Driver NVIDIA mới, **CUDA 12.x** và **cuDNN 9** (yêu cầu của onnxruntime
1.24). Kiểm tra: `nvidia-smi` phải hiện được tên GPU.

### 6.2. Đổi onnxruntime sang bản GPU

Đây là bước hay bị bỏ sót nhất. Gói `onnxruntime` thường **không có**
CUDAExecutionProvider, phải thay bằng `onnxruntime-gpu`:

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-gpu==1.24.4
```

Phải `uninstall` trước. Nếu để cả hai cùng tồn tại, Python import trúng gói
CPU và GPU không bao giờ được dùng, trong khi không có lỗi nào báo ra.

Kiểm tra:

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

Phải thấy `CUDAExecutionProvider` trong danh sách. Chỉ thấy
`['AzureExecutionProvider', 'CPUExecutionProvider']` là chưa được.

### 6.3. Đổi torch sang bản CUDA

`requirements.txt` mặc định cài `torch==2.9.1` bản CPU. Ultralytics dùng
torch để hậu xử lý mask nên cần bản CUDA:

```bash
pip uninstall -y torch torchvision
pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu124
```

Kiểm tra:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Phải in ra `2.9.1+cu124 True`. Nếu là `2.9.1+cpu False` thì vẫn đang bản CPU.

### 6.4. Xác nhận đang chạy GPU thật

```bash
python classifier.py <ảnh>
```

Dòng `device :` phải là `0` chứ không phải `cpu`, và `thời gian` giảm rõ rệt
so với CPU. Nếu log hiện:

```
Yêu cầu GPU (ONNX_DEVICE=0) nhưng KHÔNG dùng được -> tự lùi về CPU. Lý do: ...
```

thì phần "Lý do" chỉ đúng chỗ còn thiếu (torch bản CPU, hay onnxruntime
thiếu provider). `main.py` cũng in `=== DEVICE=... ===` lúc khởi động.

### 6.5. Lưu ý khi chạy GPU

- Lần inference đầu trên GPU tốn vài giây để dựng CUDA context. Đã xử lý sẵn
  bằng `WARMUP_ON_LOAD = True` — chạy 1 ảnh giả lúc init, để vật đầu tiên
  trên băng tải không bị trễ trong lúc PLC đang chờ.
- 4 slot chạy song song trên **cùng một GPU**. VRAM ≥ 4 GB là thoải mái ở
  `imgsz=1280`. Nếu gặp lỗi hết VRAM thì giảm `NUM_CAPTURES` về 1.
- Sau khi chuyển sang GPU nên xem lại `CAPTURE_DELAY_S` và các thông số gate
  `D222–D225`: xử lý nhanh hơn nghĩa là kết quả về sớm hơn, thời điểm mở gate
  tính theo băng tải có thể phải chỉnh lại.
- Ngưỡng `SIZE_THRESHOLD_RATIO` **không đổi** khi chuyển CPU→GPU. Cùng model,
  cùng `imgsz`, cùng kết quả — chỉ khác tốc độ.

---

## 7. Bản đồ register / coil PLC

| Địa chỉ | Hướng | Ý nghĩa |
|---|---|---|
| D101–D104 | PLC → Python | Trigger từng slot (1 = có vật) |
| D105 | Python → PLC | Heartbeat counter |
| D106–D109 | Python → PLC | Size result từng slot (1 = S, 2 = L) |
| D110, D111, D122, D123 | Python → PLC | Decision từng slot |
| D112–D115 | PLC → Python | Object ID từng slot |
| D222–D225 | Python → PLC | Gate 1/2: delay + độ rộng xung |
| M11, M21, M31, M41 | Python → PLC | ACK từng slot |
| M12, M22, M32, M42 | Python → PLC | Result ready từng slot |
