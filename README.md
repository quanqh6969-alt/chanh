# NIR Size Sorting — 4 Slot Encoder Software-Trigger

Hệ thống phân loại size (S/L) và defect/pass cho chanh dây, chạy trên PC
công nghiệp: camera Huaray (IMV SDK) → YOLOv8-seg (ONNX) → PLC Mitsubishi
FX3U qua Modbus RTU, xử lý song song 4 slot.

**Kiến trúc định vị bằng encoder (v3):** PLC đếm xung encoder, chốt vị trí
từng quả và phát event latch (M120–M127) tại đúng vị trí chụp → Python
polling phát hiện event → **software-trigger camera** → ACK về PLC
(M130–M137). Gate mở/đóng hoàn toàn theo xung encoder, không còn timer,
không còn `sleep` định vị trong Python. Tốc độ băng tải thay đổi → vị trí
chụp/gate vẫn đúng.

Ladder tương ứng: `Ladder_4Slot_Encoder_SoftTrig.md` (encoder 1 pha) /
`Ladder_4Slot_Encoder_AB_SoftTrig.md` (encoder A/B quadrature) trong folder
`PLC_GXWorks2` của project.

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
| Camera Huaray/Irayple GigE | có (nếu chạy thật) | 2448×2048, hỗ trợ TriggerMode=On/Software |
| PLC FX3U + cáp RS-485/USB | có (nếu chạy thật) | Modbus RTU 9600 8N1, slave ID 1 |
| Encoder + **ladder encoder** đã nạp vào PLC | có (nếu chạy thật) | Python chờ event M120–M127 từ PLC — ladder cũ (timer) sẽ không phát event nào |
| GPU NVIDIA | không | `config.py` đang đặt `ONNX_DEVICE = "0"` (GPU). Máy không có CUDA thì code tự lùi về CPU + warning. Cài đặt GPU xem mục 2.2 và 6 |

Không có camera/PLC vẫn test được phần AI bằng `python classifier.py <ảnh>`.

---

## 2. Cài đặt trên máy mới

### 2.1. Tải code về

```bash
git clone https://github.com/quanqh6969-alt/chanh.git
cd chanh
```

Không dùng git thì vào trang repo → nút xanh **Code** → **Download ZIP** →
giải nén → mở terminal trong thư mục vừa giải nén.

> Repo đã kèm `best.pt` / `best.onnx` (~18 MB) nên clone về là chạy được,
> không cần tải model riêng.

### 2.2. Tạo môi trường ảo và cài thư viện — KHÔNG tốn ổ C

Mặc định `pip install` đổ thư viện vào site-packages của Python (thường ở
ổ C) và cache pip nằm ở `C:\Users\<bạn>\AppData\Local\pip\cache`. Làm như
sau để **toàn bộ thư viện nằm trong folder clone** (ví dụ clone vào `D:\chanh`):

```bat
cd /d D:\chanh

:: 1. venv ngay trong folder — mọi thư viện nằm ở D:\chanh\.venv
python -m venv .venv
.venv\Scripts\activate

:: 2. chuyển pip cache sang ổ D (mặc định nằm ở ổ C)
set PIP_CACHE_DIR=D:\pip-cache

:: 3a. Máy CÓ GPU NVIDIA (driver + CUDA 12.x + cuDNN 9):
pip install -r requirements-gpu.txt

:: 3b. Máy chỉ chạy CPU:
pip install -r requirements.txt
```

- `requirements-gpu.txt` cài đúng bộ GPU: `onnxruntime-gpu==1.24.4` +
  `torch==2.9.1` bản **cu124** (tự lấy từ index của PyTorch) — không phải
  uninstall/gõ tay từng gói như trước.
- Dòng `set PIP_CACHE_DIR=...` chỉ có hiệu lực trong cửa sổ cmd đó. Muốn
  vĩnh viễn: **System Properties → Environment Variables → New user
  variable**: `PIP_CACHE_DIR = D:\pip-cache`.
- Repo đã kèm `best.onnx` nên có thể cài nhẹ hơn bằng cách bỏ 3 dòng
  `torch` / `onnx` / `onnxslim` (tiết kiệm ~2.5 GB). Chỉ cần chúng khi
  muốn tự export lại `best.pt` → `best.onnx`. **Lưu ý máy GPU:** ultralytics
  hậu xử lý mask bằng torch — nếu bỏ torch thì phải cài riêng tối thiểu
  `torch` bản cu124.

### 2.3. Cài SDK camera

Cài **Huaray MV Viewer** (bản x64) từ nhà cung cấp camera. `IMVApi.py`
nạp DLL từ đường dẫn cố định:

```
C:\Program Files\HuarayTech\MV Viewer\Runtime\x64\MVSDKmd.dll
C:\Program Files\HuarayTech\MV Viewer\Application\x64   (fallback PATH)
```

Nếu cài vào ổ/thư mục khác thì sửa `_DLL_DIR` / `_APP_DLL_DIR` trong
`IMVApi.py`. Mở MV Viewer thấy camera là SDK đã ổn. Kiểm tra nhanh:
`python test_dll.py`.

### 2.4. Sửa cấu hình cho máy mới

Mở `config.py`, kiểm tra các chỗ hay phải đổi nhất:

```python
MODBUS_PORT = "COM8"        # Device Manager -> Ports (COM & LPT)
CAMERA_INDEX = 0            # nếu có nhiều camera
ONNX_DEVICE = "0"           # "0" = GPU đầu tiên; "cpu" = CPU
```

### 2.5. Đo và điền ENCODER_CONFIG — BẮT BUỘC trước khi chạy thật

Các giá trị trong `Config.ENCODER_CONFIG` hiện là **placeholder**. Phải đo
trên máy thật:

1. **Đo `PULSES_PER_MM`:** chạy băng tải một quãng đã biết (vd 2 m), đọc
   Δ encoder count trong GX Works2 → `pulses_per_mm = Δcount / 2000 mm`.
   - Encoder A/B dùng C255 (4x): `pulses_per_mm = PPR × 4 × tỉ_lệ / chu_vi_mm`
   - Encoder 1 pha dùng C236: `pulses_per_mm = PPR × tỉ_lệ / chu_vi_mm`
2. **Đo khoảng cách trên máy (mm):** sensor→camera (vị trí shot 1, shot 2),
   sensor→gate S, sensor→gate L, độ rộng mở gate, camera→gate (để đặt
   AI_DEADLINE sao cho inference kịp trước khi quả tới gate).
3. **Quy đổi sang pulses** và điền vào `ENCODER_CONFIG` (D222–D239).
   `gate_settings.py` sẽ tự kiểm tra thứ tự
   (SHOT1 < SHOT2 < ACK_TIMEOUT < AI_DEADLINE < GATE < RELEASE) và báo lỗi
   nếu điền sai.
4. **`EVENT_LEAD_PULSES`:** bù latency software-trigger (polling + Modbus +
   SDK, ước 20–90 ms). Khởi điểm: `v_max(mm/s) × 0.05 × pulses_per_mm`,
   tinh chỉnh theo ảnh thật.

### 2.6. Chạy

```bash
python gate_settings.py --write   # ghi ENCODER_CONFIG xuống PLC, đọc lại xác nhận
python main.py
```

Ctrl+C để dừng. Log ghi ra `logs/` và in ra màn hình. Ảnh kết quả lưu vào
`captured_images/` (tên file dạng `slot{i}_obj_{id}_{timestamp}_size{n}_{pass|reject}.jpg`,
cả hai thư mục tự tạo, đã bị `.gitignore` bỏ qua).

---

## 3. Kiểm tra từng phần khi có lỗi

Mỗi module chạy độc lập được, giúp khoanh vùng lỗi nhanh:

```bash
python check_gpu.py              # GPU + onnxruntime providers + torch CUDA
python camera.py                 # chụp 1 tấm (gửi TriggerSoftware) -> captured_images/test_capture.jpg
python classifier.py <ảnh>       # in PASS/DEFECT, size, area_ratio
python plc_client.py             # đọc D101-D130, chạy heartbeat 5s
python gate_settings.py          # xem ENCODER_CONFIG D222-D239 hiện tại trên PLC
python gate_settings.py --write  # ghi theo config.py rồi đọc lại xác nhận
```

Thứ tự chẩn đoán khi `main.py` báo "Initialization failed": chạy
`classifier.py` → `camera.py` → `plc_client.py`, cái nào fail thì lỗi ở đó.

**Log đặc trưng của chế độ encoder** khi chạy bình thường:

```
[Slot0] SPAWNED (ObjID=123)
  [Slot0] Shot1 event received (waited 430ms, ObjID=123)
  [Slot0] Shot1 captured (85ms trigger->frame) + ACK M130
  [Slot0] Shot1: PASS size=L conf=0.87 inf=210ms
  [Slot0] Shot2 event received ...
  [Slot0] MERGED: PASS size=2 conf=0.81 total=1150ms
```

Nếu thấy `Shot1 event TIMEOUT` lặp lại: PLC chưa phát M120 — kiểm tra
ladder encoder đã nạp chưa, encoder có đếm không (monitor C236/C255 trong
GX Works2 khi băng tải chạy), và `SHOT_EVENT_TIMEOUT_S` có ngắn hơn thời
gian quả đi từ sensor đến camera không.

---

## 4. Cấu trúc file

| File | Vai trò |
|---|---|
| `main.py` | Entry point duy nhất |
| `config.py` | **Toàn bộ tham số — chỉ cần sửa file này** |
| `app.py` | Vòng lặp chính: poll D101–D130 + block coil M120–M137, điều phối state machine 4 slot |
| `slot_processor.py` | Xử lý 1 slot: chờ shot event → software-trigger → classify → trả kết quả PLC |
| `camera.py` | Camera Huaray IMV SDK, **software-trigger mode** (TriggerMode=On) |
| `classifier.py` | Load ONNX, phân loại defect/pass + size S/L, tự chọn CPU/GPU |
| `plc_client.py` | Modbus RTU + heartbeat thread + `read_coils` (FC01) |
| `gate_settings.py` | Ghi/giám sát ENCODER_CONFIG D222–D239 (pulses 32-bit) + ordering check |
| `image_saver.py` | Vẽ overlay, ghép 2 shot và lưu ảnh ở thread riêng |
| `logger_setup.py` | Logging dùng chung (file + console, UTF-8) |
| `check_gpu.py` | Chẩn đoán GPU/CUDA/onnxruntime providers |
| `test_dll.py` | Chẩn đoán load MVSDKmd.dll |
| `IMVApi.py`, `IMVDefines.py` | Wrapper ctypes của Huaray SDK (có `IMV_ExecuteCommandFeature` cho TriggerSoftware) |
| `requirements.txt` | Cài đặt bản CPU |
| `requirements-gpu.txt` | Cài đặt bản GPU (onnxruntime-gpu + torch cu124) |
| `best.pt`, `best.onnx` | Model YOLOv8-seg đã train (`imgsz=1280`) |

---

## 5. Luồng hoạt động (encoder software-trigger)

```
X000/X003 sensor → PLC chốt ObjectID + EncoderAtSensor (D112-D115, D302-D309)
      → PLC set D10x=1 (object request)
Python: poll thấy D10x=1 → spawn thread slot, ACK M1x
      → encoder đạt SHOT1_OFFSET → PLC set M12x (event LATCH)
Python: poll block M120-M137 thấy M12x → set threading.Event
Thread slot: TriggerSoftware → GetFrame → ghi ACK M13x NGAY (trước inference)
      → PLC thấy ACK → xóa event, đánh dấu shot 1 complete
      → encoder đạt SHOT2_OFFSET → PLC set M12(x+4) → như trên → frame 2
Thread slot: ghép 2 frame → YOLO → ghi D10x size + D1xx decision → Mx2
PLC: chốt M5x (pass) / M6x (reject)
      → encoder đạt GATE_OFFSET → Y000/Y001 mở, hết GATE_WIDTH → đóng
      → encoder đạt RELEASE → giải phóng slot
An toàn:
  - quá AI_DEADLINE chưa có kết quả → PLC tự reject (M15x)
  - quá SHOT_ACK_TIMEOUT Python chưa ACK → PLC chặn pass (M16x)
  - thread Python lỗi → tự ACK cả 2 shot + object để không treo slot
```

Nguyên tắc quan trọng: **inference không được chặn vòng poll PLC** — poll
chạy ở thread chính, capture + inference chạy ở thread slot. Event trên PLC
là latch nên poll trễ vài chục ms không làm mất event, chỉ tăng latency
(bù bằng `EVENT_LEAD_PULSES`).

---

## 6. Thông số quan trọng

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

**ENCODER_CONFIG (D222–D239)** — các cặp thanh ghi 32-bit (little-endian:
D[n]=low word, D[n+1]=high word), đơn vị **pulses**. Ladder encoder xóa vùng
này ở rung M8002 mỗi lần PLC STOP→RUN; Python ghi lại lúc khởi động và có
watchdog đọc mỗi 2 s, phát hiện lệch (PLC restart / sửa tay bằng GX) thì
ghi lại + log warning.

**Hiệu năng** — ONNX `imgsz=1280`: CPU ~2.4–2.9 s/ảnh; GPU ~0.1–0.3 s/ảnh.
Với encoder, inference chậm không làm **sai vị trí chụp/gate** (vị trí do
encoder quyết) nhưng phải xong trước `AI_DEADLINE` — nếu không PLC tự
reject quả đó. Chậm thì tăng khoảng cách camera→gate hoặc dùng GPU (mục 7).

---

## 7. Chạy bằng GPU (NVIDIA)

`config.py` của repo này **đã đặt sẵn**:

```python
ONNX_DEVICE = "0"      # GPU đầu tiên; "cuda:1" = GPU thứ hai; "cpu" = CPU
```

Không phải sửa `classifier.py` hay export lại model — `best.onnx` chạy được
cả CPU và GPU, cùng một file. Máy thiếu CUDA thì code **tự lùi về CPU**
(kèm warning trong log, không crash).

Cài đặt môi trường GPU: dùng `requirements-gpu.txt` (mục 2.2) — đã gồm
`onnxruntime-gpu==1.24.4` và `torch==2.9.1+cu124`. Nếu cài tay từng bước:

### 7.1. Driver + CUDA

Driver NVIDIA mới, **CUDA 12.x** và **cuDNN 9** (yêu cầu của onnxruntime
1.24). Kiểm tra: `nvidia-smi` phải hiện được tên GPU.

### 7.2. onnxruntime bản GPU

Gói `onnxruntime` thường **không có** CUDAExecutionProvider, phải thay bằng
`onnxruntime-gpu`:

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-gpu==1.24.4
```

Phải `uninstall` trước. Nếu để cả hai cùng tồn tại, Python import trúng gói
CPU và GPU không bao giờ được dùng, trong khi không có lỗi nào báo ra.

Kiểm tra:

```bash
python check_gpu.py
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

Phải thấy `CUDAExecutionProvider` trong danh sách.

### 7.3. torch bản CUDA

Ultralytics dùng torch để hậu xử lý mask. `classifier.py` của bản này chỉ
yêu cầu ONNX Runtime có CUDAExecutionProvider (không cần `torch.cuda`),
nhưng nên cài torch bản CUDA cho đồng bộ:

```bash
pip uninstall -y torch torchvision
pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu124
```

### 7.4. Xác nhận đang chạy GPU thật

```bash
python classifier.py <ảnh>
```

Dòng `device :` phải là `0` chứ không phải `cpu`, và `thời gian` giảm rõ rệt
so với CPU. `main.py` cũng in `=== DEVICE=... ===` lúc khởi động.

### 7.5. Lưu ý khi chạy GPU

- Lần inference đầu trên GPU tốn vài giây dựng CUDA context — đã xử lý bằng
  `WARMUP_ON_LOAD = True`.
- 4 slot chạy song song trên **cùng một GPU**; camera chỉ có 1 nên capture
  vẫn serialize qua camera lock. VRAM ≥ 4 GB là thoải mái ở `imgsz=1280`.
- GPU nhanh hơn nghĩa là kết quả về sớm hơn nhiều so với `AI_DEADLINE` —
  có thể thu hẹp khoảng cách camera→gate (giảm `GATE_*_OFFSET`) nếu cơ khí
  cho phép.
- Ngưỡng `SIZE_THRESHOLD_RATIO` **không đổi** khi chuyển CPU→GPU.

---

## 8. Bản đồ register / coil PLC (khớp ladder encoder)

| Địa chỉ | Hướng | Ý nghĩa |
|---|---|---|
| D101–D104 | PLC → Python | Object request từng slot (1 = có vật) |
| D105 | Python → PLC | Heartbeat counter |
| D106–D109 | Python → PLC | Size result từng slot (1 = S, 2 = L) |
| D110, D111, D122, D123 | Python → PLC | Decision từng slot (1 = pass, 2 = reject) |
| D112–D115 | PLC → Python | Object ID từng slot |
| D222:D223 | Python → PLC | GATE_S_OFFSET (pulses, 32-bit) |
| D224:D225 | Python → PLC | GATE_S_WIDTH |
| D226:D227 | Python → PLC | GATE_L_OFFSET |
| D228:D229 | Python → PLC | GATE_L_WIDTH |
| D230:D231 | Python → PLC | SHOT1_OFFSET |
| D232:D233 | Python → PLC | SHOT2_OFFSET |
| D234:D235 | Python → PLC | AI_DEADLINE_OFFSET |
| D236:D237 | Python → PLC | SHOT_ACK_TIMEOUT |
| D238:D239 | Python → PLC | RELEASE_OFFSET |
| D242:D243, D244:D245 | PLC tự tính | GATE_S_END, GATE_L_END |
| M11, M21, M31, M41 | Python → PLC | ACK object từng slot |
| M12, M22, M32, M42 | Python → PLC | Result ready từng slot |
| M100–M103 | PLC → Python | Request pending (đọc qua D10x là đủ) |
| **M120–M123** | **PLC → Python** | **EVENT shot 1 (latch) slot 0–3** |
| **M124–M127** | **PLC → Python** | **EVENT shot 2 (latch) slot 0–3** |
| **M130–M133** | **Python → PLC** | **ACK shot 1 slot 0–3** |
| **M134–M137** | **Python → PLC** | **ACK shot 2 slot 0–3** |
| M150–M153 | PLC nội bộ | Object in flight (busy thật của slot) |
| M154–M157 | PLC nội bộ | AI deadline timeout → reject |
| M160–M163 | PLC nội bộ | Camera ACK timeout → chặn pass |
| Y000 / Y001 | PLC | Gate S / Gate L |

Python đọc M120–M137 gộp trong **1 Modbus transaction** mỗi vòng poll
(FC01, `SHOT_COIL_READ_START=120`, `COUNT=18`), không đọc lẻ từng bit.
