from pathlib import Path

# Thư mục chứa chính file này — cũng là gốc của repo Inference
BASE_DIR = Path(__file__).resolve().parent
# Thư mục cha (trong cây project gốc là Python\ chứa IMVApi.py, IMVDefines.py).
# Repo standalone đã có bản copy IMVApi/IMVDefines trong BASE_DIR nên
# PARENT_DIR chỉ còn là fallback.
PARENT_DIR = BASE_DIR.parent
# Thư mục gốc project (chỉ dùng khi chạy trong cây project gốc)
PROJECT_DIR = PARENT_DIR.parent


class Config:
    # ===== PLC MODBUS RTU =====
    MODBUS_PORT      = "COM8"
    MODBUS_BAUDRATE  = 9600
    MODBUS_PARITY    = "N"
    MODBUS_STOPBITS  = 1
    MODBUS_BYTESIZE  = 8
    MODBUS_TIMEOUT   = 1.0
    MODBUS_SLAVE_ID  = 1

    # ===== 4-SLOT REGISTERS =====
    NUM_SLOTS        = 4
    TRIGGER_REGS     = [101, 102, 103, 104]    # D101-D104: request per slot (PLC->Py)
    SIZE_REGS        = [106, 107, 108, 109]    # D106-D109: size result (Py->PLC)
    DECISION_REGS    = [110, 111, 122, 123]    # D110,D111,D122,D123: decision (Py->PLC)
    OBJID_REGS       = [112, 113, 114, 115]    # D112-D115: object ID per slot (PLC)
    ACK_COILS        = [11, 21, 31, 41]        # M11,M21,M31,M41: ack object (Py->PLC)
    RESULT_COILS     = [12, 22, 32, 42]        # M12,M22,M32,M42: result ready (Py->PLC)
    REG_HEARTBEAT    = 105                      # D105: heartbeat counter

    # ===== ENCODER SHOT EVENT (software-trigger) =====
    # Ladder phát event latch khi encoder đến đúng vị trí; Python polling thấy
    # -> software-trigger camera -> lấy frame -> ghi ACK. PLC xóa event khi ACK.
    SHOT1_EVENT_COILS = [120, 121, 122, 123]   # M120-M123: yêu cầu shot 1 (PLC->Py)
    SHOT2_EVENT_COILS = [124, 125, 126, 127]   # M124-M127: yêu cầu shot 2 (PLC->Py)
    SHOT1_ACK_COILS   = [130, 131, 132, 133]   # M130-M133: ACK shot 1 (Py->PLC)
    SHOT2_ACK_COILS   = [134, 135, 136, 137]   # M134-M137: ACK shot 2 (Py->PLC)

    # Vùng coil đọc gộp trong 1 transaction (FC01). Trải M120-M137.
    SHOT_COIL_READ_START = 120
    SHOT_COIL_READ_COUNT = 18                  # M120-M137

    # Thời gian chờ 1 shot event từ lúc nhận request (s). Quá -> bỏ qua object
    # (sensor kích sai / encoder chưa tới). KHÔNG dùng để định vị — PLC mới
    # là nơi quyết định vị trí; đây chỉ là lưới an toàn chống treo thread.
    SHOT_EVENT_TIMEOUT_S = 8.0

    # ===== CAMERA =====
    CAMERA_INDEX         = 0
    CAMERA_EXPOSURE_US   = 400
    CAMERA_GAIN_DB       = 1.0
    CAMERA_WIDTH         = 2448
    CAMERA_HEIGHT        = 2048
    CAMERA_AUTO_WHITE_BALANCE = "Continuous"

    # ENCODER MODE: camera chạy software-trigger, KHÔNG free-running.
    # PLC phát event theo vị trí encoder -> Python gọi TriggerSoftware.
    # CAPTURE_DELAY_S (cũ) đã bỏ — vị trí chụp do encoder quyết định.
    CAMERA_TRIGGER_MODE  = "On"          # "On" = software trigger; "Off" = free-running (cũ)
    CAMERA_TRIGGER_SOURCE = "Software"
    CAPTURE_TIMEOUT_MS   = 1000          # chờ frame sau khi gửi TriggerSoftware

    # ===== MULTI-CAPTURE =====
    NUM_CAPTURES            = 2          # vẫn 2 shot, nhưng thời điểm do PLC event
    # DELAY_BETWEEN_CAPTURES (cũ) đã bỏ — khoảng cách 2 shot = SHOT2_OFFSET - SHOT1_OFFSET (encoder)

    # ===== AI MODEL =====
    MODEL_PATH_PT   = str(BASE_DIR / "best.pt")
    MODEL_PATH_ONNX = str(BASE_DIR / "best.onnx")
    AUTO_EXPORT_ONNX = True

    ONNX_IMG_SIZE   = 1280

    # ===== CPU / GPU =====
    # "cpu"      -> ONNX Runtime CPUExecutionProvider (mặc định, chắc chắn chạy)
    # 0          -> GPU NVIDIA đầu tiên (CUDAExecutionProvider)
    # "cuda:1"   -> GPU thứ 2
    #
    # Đặt GPU mà máy không có CUDA thì code tự lùi về CPU + log warning,
    # KHÔNG raise (tránh chết cả dây chuyền khi mang sang máy khác).
    # Muốn dùng GPU thật thì máy phải có ĐỦ 3 thứ, xem README mục 6:
    #   1. driver NVIDIA + CUDA 12.x + cuDNN 9
    #   2. pip uninstall onnxruntime  &&  pip install onnxruntime-gpu
    #   3. torch bản CUDA (torch==2.9.1+cu124), KHÔNG phải bản +cpu
    ONNX_DEVICE = "0"

    # Chạy 1 lần inference giả lúc load model. Trên GPU lần predict đầu
    # tốn vài giây để dựng CUDA context + tune kernel; warmup ở đây để vật
    # đầu tiên trên băng tải không bị trễ trong lúc PLC đang chờ.
    WARMUP_ON_LOAD = True

    CONFIDENCE_THRESHOLD = 0.5
    IOU_THRESHOLD        = 0.45
    MIN_MASK_AREA_PX     = 500

    # Ngưỡng phân biệt size S/L theo TỈ LỆ diện tích mask trên diện tích ảnh:
    #     area_ratio = area_px / (img_w * img_h)
    SIZE_THRESHOLD_RATIO = 0.0733

    # ===== LƯU ẢNH =====
    # Nằm TRONG folder repo để clone sang máy khác là chạy được ngay
    # (trước kia trỏ ra PROJECT_DIR, thư mục đó không tồn tại khi clone lẻ).
    IMAGE_SAVE_DIR = BASE_DIR / "captured_images"
    SAVE_IMAGES = True

    SAVE_NO_DETECTION_IMAGES = False

    # ===== TIMING =====
    HEARTBEAT_INTERVAL = 0.2
    POLLING_INTERVAL   = 0.02       # 20ms polling
    RESULT_HOLD_S      = 0.1        # giữ M1x2 ON bao lâu trước khi tắt lại
    REACK_TIMEOUT      = 2.0        # D10x kẹt 1 quá lâu -> ACK có thể mất, gửi lại

    # ===== BULK REGISTER =====
    BULK_READ_START = 101
    BULK_READ_COUNT = 30             # D101-D130

    # ===== ENCODER CONFIG (Python -> PLC, ghi đè giá trị M8002) =====
    # Ladder encoder: mọi giá trị là 32-bit (2 thanh ghi D liên tiếp),
    # đơn vị PULSES. Quy đổi: pulses = mm x PULSES_PER_MM.
    #
    #   PULSES_PER_MM = (PPR x 4 x tỉ_lệ_truyền) / chu_vi_con_lăn_mm  [A/B 4x]
    #   PULSES_PER_MM = PPR / chu_vi_con_lăn_mm                        [1 pha]
    #
    # GIÁ TRỊ DƯỚI ĐÂY LÀ PLACEHOLDER — phải đo trên máy thật rồi điền lại.
    # Thứ tự bắt buộc: SHOT1 < SHOT2 < SHOT_ACK_TIMEOUT < AI_DEADLINE
    #                  < GATE_*_OFFSET < GATE_*_OFFSET+WIDTH < RELEASE
    PULSES_PER_MM = 20.0          # ví dụ: encoder 1000 PPR A/B 4x, chu vi 200mm

    ENCODER_CONFIG = {
        # start_addr: (value_pulses, nhãn)  — ghi 32-bit little-endian word:
        # D[n]=low word, D[n+1]=high word
        222: (40_000,  "GATE_S_OFFSET"),    # sensor -> gate S        (đo mm x PPM)
        224: (1_000,   "GATE_S_WIDTH"),     # độ rộng mở gate S
        226: (45_000,  "GATE_L_OFFSET"),    # sensor -> gate L
        228: (1_000,   "GATE_L_WIDTH"),     # độ rộng mở gate L
        230: (7_500,   "SHOT1_OFFSET"),     # sensor -> event shot 1 (đã trừ EventLead)
        232: (10_000,  "SHOT2_OFFSET"),     # sensor -> event shot 2
        234: (30_000,  "AI_DEADLINE"),      # muộn nhất phải có kết quả AI
        236: (12_000,  "SHOT_ACK_TIMEOUT"), # muộn nhất Python phải ACK shot (giữa SHOT2 và AI_DEADLINE)
        238: (46_500,  "RELEASE"),          # giải phóng slot (sau gate end + biên)
    }
    # D242:D243 / D244:D245 (GATE_S_END / GATE_L_END) do PLC tự tính, không ghi.

    # EventLead bù latency software-trigger (polling + Modbus + SDK):
    # đặt SHOT1_OFFSET = vị trí_chụp_mong_muốn - EVENT_LEAD_PULSES.
    # Tinh chỉnh theo ảnh thật sau khi đo latency (log trong slot_processor).
    EVENT_LEAD_PULSES = 1_000     # ví dụ: 50ms x 1000mm/s x 20 pulses/mm

    # Ghi encoder config xuống PLC lúc khởi động (ghi đè M8002).
    WRITE_GATE_SETTINGS = True

    GATE_SETTINGS_WATCH = True
    GATE_SETTINGS_CHECK_INTERVAL = 2.0    # giây

    # ===== CLASS NAMES =====
    CLASS_NAMES = {0: "defect", 1: "pass"}

    # ===== LOG =====
    LOG_FILE = BASE_DIR / "logs" / "size_sorting_4slot_v2.log"
