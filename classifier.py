"""
classifier.py — Load model ONNX và phân loại defect/pass + size S/L.

Tách riêng để test AI không cần camera/PLC:
    python classifier.py <đường_dẫn_ảnh>
    python classifier.py E:/Lon/Pic_xxx.bmp
"""

import os
import sys

import cv2
import numpy as np

from config import Config
from logger_setup import logger


# ======================================================================
# CHỌN THIẾT BỊ CHẠY (CPU / GPU)
# ======================================================================
def resolve_device():
    """Chọn device cho ONNX dựa trên ONNX Runtime, không phụ thuộc PyTorch CUDA.

    ONNX model được chạy bằng ONNX Runtime. Vì vậy chỉ cần
    CUDAExecutionProvider tồn tại; PyTorch CPU vẫn có thể được giữ lại.
    """
    want = Config.ONNX_DEVICE

    if isinstance(want, str) and want.strip().lower() in ("cpu", ""):
        logger.info("Device: CPU (Config.ONNX_DEVICE='cpu')")
        return "cpu"

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()

        if "CUDAExecutionProvider" not in providers:
            logger.warning(
                f"Yêu cầu GPU (ONNX_DEVICE={want!r}) nhưng ONNX Runtime "
                f"không có CUDAExecutionProvider -> tự lùi về CPU. "
                f"Providers hiện có: {providers}"
            )
            return "cpu"

        logger.info(
            f"Device: GPU (ONNX_DEVICE={want!r}, "
            f"CUDAExecutionProvider OK)"
        )
        return want

    except Exception as e:
        logger.warning(
            f"Không kiểm tra được ONNX Runtime GPU: {e} -> tự lùi về CPU"
        )
        return "cpu"


# ======================================================================
# ONNX EXPORT HELPER
# ======================================================================
def ensure_onnx_exists():
    """Tự export .pt -> .onnx nếu chưa có file ONNX."""
    if not Config.AUTO_EXPORT_ONNX:
        return

    if os.path.exists(Config.MODEL_PATH_ONNX):
        logger.info(f"ONNX model found: {Config.MODEL_PATH_ONNX}")
        return

    if not os.path.exists(Config.MODEL_PATH_PT):
        logger.warning(
            f"No .pt file at {Config.MODEL_PATH_PT}, skip ONNX export"
        )
        return

    try:
        from ultralytics import YOLO

        logger.info(f"Exporting ONNX from {Config.MODEL_PATH_PT} ...")

        model = YOLO(Config.MODEL_PATH_PT)

        model.export(
            format="onnx",
            imgsz=Config.ONNX_IMG_SIZE,
            opset=13,
            simplify=True,
        )

        exported = Config.MODEL_PATH_PT.replace(".pt", ".onnx")

        if os.path.exists(exported) and exported != Config.MODEL_PATH_ONNX:
            os.replace(exported, Config.MODEL_PATH_ONNX)

        logger.info(f"ONNX exported: {Config.MODEL_PATH_ONNX}")

    except Exception as e:
        logger.error(f"ONNX export failed: {e}")


# ======================================================================
# ONNX INFERENCE
# ======================================================================

class ONNXClassifier:
    """YOLOv8-seg chạy trực tiếp bằng ONNX Runtime.

    Không dùng Ultralytics YOLO.predict() cho inference vì project đang giữ
    torch bản CPU-only. ONNX Runtime sẽ tự chạy CUDAExecutionProvider.
    """

    def __init__(self):
        self.session = None
        self.input_name = None
        self.input_size = int(Config.ONNX_IMG_SIZE)
        self.names = Config.CLASS_NAMES
        self.device = "cpu"
        self.mask_dim = 32

    def load(self):
        try:
            import onnxruntime as ort

            # Load CUDA/cuDNN DLL từ các package pip mà không cần CUDA Toolkit.
            ort.preload_dlls()

            ensure_onnx_exists()

            if not os.path.exists(Config.MODEL_PATH_ONNX):
                logger.error(
                    f"ONNX model not found: {Config.MODEL_PATH_ONNX}"
                )
                return False

            self.device = resolve_device()

            if self.device == "cpu":
                providers = ["CPUExecutionProvider"]
                provider_options = None
            else:
                # Hỗ trợ cả 0 và "cuda:1".
                device_id = 0
                try:
                    s = str(self.device).strip().lower()
                    if s.startswith("cuda:"):
                        device_id = int(s.split(":", 1)[1])
                    elif s.isdigit():
                        device_id = int(s)
                except Exception:
                    device_id = 0

                providers = [
                    "CUDAExecutionProvider",
                    "CPUExecutionProvider",
                ]
                provider_options = [
                    {"device_id": device_id},
                    {},
                ]

            if provider_options is None:
                self.session = ort.InferenceSession(
                    Config.MODEL_PATH_ONNX,
                    providers=providers,
                )
            else:
                self.session = ort.InferenceSession(
                    Config.MODEL_PATH_ONNX,
                    providers=providers,
                    provider_options=provider_options,
                )

            active = self.session.get_providers()
            logger.info(
                f"ONNX Runtime session loaded: {Config.MODEL_PATH_ONNX} | "
                f"active providers={active}"
            )

            # Nếu CUDA session không thực sự active thì không giả vờ là GPU.
            if self.device != "cpu" and "CUDAExecutionProvider" not in active:
                logger.warning(
                    "CUDAExecutionProvider không active trong session -> "
                    "chuyển sang CPU."
                )
                self.device = "cpu"
                self.session = ort.InferenceSession(
                    Config.MODEL_PATH_ONNX,
                    providers=["CPUExecutionProvider"],
                )

            inp = self.session.get_inputs()[0]
            self.input_name = inp.name

            shape = inp.shape
            # Model của project là fixed 1280x1280; vẫn đọc shape nếu là số.
            if len(shape) == 4:
                if isinstance(shape[2], int):
                    self.input_size = int(shape[2])
                elif isinstance(shape[3], int):
                    self.input_size = int(shape[3])

            outputs = self.session.get_outputs()
            logger.info(
                "ONNX input: "
                f"name={self.input_name}, shape={shape}; "
                f"outputs={[o.shape for o in outputs]}"
            )

            # YOLOv8-seg thường có output:
            #   predictions: [1, 4+nc+32, N]
            #   prototypes : [1, 32, H/4, W/4]
            for o in outputs:
                shp = o.shape
                if len(shp) == 4 and isinstance(shp[1], int):
                    self.mask_dim = int(shp[1])
                    break

            if Config.WARMUP_ON_LOAD:
                self._warmup()

            return True

        except Exception as e:
            logger.error(f"ONNX load failed: {e}")
            return False

    @staticmethod
    def _sigmoid(x):
        x = np.clip(x, -50.0, 50.0)
        return 1.0 / (1.0 + np.exp(-x))

    def _letterbox(self, image):
        """Resize + pad ảnh BGR về input vuông của YOLO."""
        h, w = image.shape[:2]
        size = self.input_size

        scale = min(size / w, size / h)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))

        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

        pad_w = size - nw
        pad_h = size - nh
        left = pad_w // 2
        right = pad_w - left
        top = pad_h // 2
        bottom = pad_h - top

        padded = cv2.copyMakeBorder(
            resized,
            top, bottom, left, right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

        return padded, scale, left, top, nw, nh

    def _preprocess(self, image):
        padded, scale, left, top, nw, nh = self._letterbox(image)

        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = rgb.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None, ...]

        return blob, (scale, left, top, nw, nh)

    @staticmethod
    def _iou_one_to_many(box, boxes):
        """IoU giữa 1 box xyxy và mảng boxes xyxy."""
        x1 = np.maximum(box[0], boxes[:, 0])
        y1 = np.maximum(box[1], boxes[:, 1])
        x2 = np.minimum(box[2], boxes[:, 2])
        y2 = np.minimum(box[3], boxes[:, 3])

        inter = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        a = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
        b = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * \
            np.maximum(0.0, boxes[:, 3] - boxes[:, 1])

        return inter / np.maximum(a + b - inter, 1e-7)

    def _nms(self, boxes, scores, class_ids, iou_threshold):
        """Class-aware NMS, không phụ thuộc PyTorch."""
        keep = []

        for cid in np.unique(class_ids):
            inds = np.where(class_ids == cid)[0]
            order = inds[np.argsort(scores[inds])[::-1]]

            while len(order):
                i = int(order[0])
                keep.append(i)

                if len(order) == 1:
                    break

                rest = order[1:]
                ious = self._iou_one_to_many(boxes[i], boxes[rest])
                order = rest[ious <= iou_threshold]

        return keep

    def _decode_outputs(self, outputs):
        """Tách prediction tensor và mask prototype từ output YOLOv8-seg."""
        pred = None
        proto = None

        for out in outputs:
            arr = np.asarray(out)

            if arr.ndim == 4:
                # [1, mask_dim, mh, mw]
                if arr.shape[1] >= 8 and arr.shape[2] > 1:
                    proto = arr[0].astype(np.float32, copy=False)

            elif arr.ndim == 3:
                # YOLOv8 ONNX: [1, 4+nc+mask_dim, N]
                if arr.shape[1] < arr.shape[2]:
                    pred = arr[0].T.astype(np.float32, copy=False)
                else:
                    pred = arr[0].astype(np.float32, copy=False)

        if pred is None:
            raise RuntimeError("Không tìm thấy prediction output của YOLO.")
        if proto is None:
            raise RuntimeError("Không tìm thấy mask prototype output của YOLOv8-seg.")

        if proto.ndim != 3:
            raise RuntimeError(f"Proto mask shape không hợp lệ: {proto.shape}")

        return pred, proto

    def _mask_to_polygon(
        self,
        coeff,
        proto,
        box,
        original_shape,
        letterbox_meta,
    ):
        """Tạo polygon mask ở tọa độ ảnh gốc."""
        scale, left, top, nw, nh = letterbox_meta
        img_h, img_w = original_shape[:2]

        ph, pw = proto.shape[1], proto.shape[2]

        # coeff @ proto -> mask trên lưới prototype.
        mask_small = self._sigmoid(
            np.matmul(coeff.astype(np.float32), proto.reshape(self.mask_dim, -1))
        ).reshape(ph, pw)

        # Upscale về ảnh letterbox.
        mask = cv2.resize(
            mask_small,
            (self.input_size, self.input_size),
            interpolation=cv2.INTER_LINEAR,
        )

        # Crop theo bounding box letterbox để giảm mask leakage.
        x1, y1, x2, y2 = box
        x1 = max(0, min(self.input_size - 1, int(np.floor(x1))))
        y1 = max(0, min(self.input_size - 1, int(np.floor(y1))))
        x2 = max(0, min(self.input_size, int(np.ceil(x2))))
        y2 = max(0, min(self.input_size, int(np.ceil(y2))))

        cropped = np.zeros_like(mask, dtype=np.float32)
        if x2 > x1 and y2 > y1:
            cropped[y1:y2, x1:x2] = mask[y1:y2, x1:x2]

        binary = (cropped > 0.5).astype(np.uint8) * 255

        # Bỏ phần padding letterbox.
        binary = binary[top:top + nh, left:left + nw]

        if binary.size == 0:
            return None, 0.0

        # Trở về kích thước camera gốc.
        binary = cv2.resize(
            binary,
            (img_w, img_h),
            interpolation=cv2.INTER_NEAREST,
        )

        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return None, 0.0

        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))

        if len(contour) < 3 or area <= 0:
            return None, area

        polygon = contour.reshape(-1, 2).astype(np.float32)
        return polygon, area

    def _warmup(self):
        """Warmup trực tiếp bằng ONNX Runtime."""
        import time

        try:
            blank = np.zeros(
                (
                    Config.CAMERA_HEIGHT,
                    Config.CAMERA_WIDTH,
                    3,
                ),
                dtype=np.uint8,
            )

            t0 = time.time()
            self.classify(blank)

            logger.info(f"Warmup xong: {time.time() - t0:.2f}s")

        except Exception as e:
            logger.warning(f"Warmup lỗi (bỏ qua): {e}")

    def classify(self, image):
        if self.session is None or self.input_name is None:
            return 0, False, 0.0, None

        try:
            if image is None or image.ndim != 3:
                return 0, False, 0.0, None

            blob, meta = self._preprocess(image)

            outputs = self.session.run(
                None,
                {self.input_name: blob},
            )

            pred, proto = self._decode_outputs(outputs)

            # YOLOv8-seg:
            # [cx, cy, w, h, class_scores..., mask_coeff...]
            nc = pred.shape[1] - 4 - self.mask_dim

            if nc <= 0:
                raise RuntimeError(
                    f"Không suy ra được số class: pred={pred.shape}, "
                    f"mask_dim={self.mask_dim}"
                )

            class_scores = pred[:, 4:4 + nc]
            class_ids = np.argmax(class_scores, axis=1)
            confidences = class_scores[
                np.arange(len(class_scores)), class_ids
            ]

            conf_thr = float(Config.CONFIDENCE_THRESHOLD)
            selected = confidences >= conf_thr

            if not np.any(selected):
                logger.debug("No detection -> reject")
                return 0, False, 0.0, None

            pred = pred[selected]
            class_ids = class_ids[selected].astype(np.int32)
            confidences = confidences[selected].astype(np.float32)

            # Chỉ giữ class mà application đang định nghĩa: 0 / 1.
            valid = np.isin(class_ids, [0, 1])
            if not np.any(valid):
                return 0, False, 0.0, None

            pred = pred[valid]
            class_ids = class_ids[valid]
            confidences = confidences[valid]

            cx = pred[:, 0]
            cy = pred[:, 1]
            bw = pred[:, 2]
            bh = pred[:, 3]

            boxes = np.column_stack([
                cx - bw / 2,
                cy - bh / 2,
                cx + bw / 2,
                cy + bh / 2,
            ]).astype(np.float32)

            boxes[:, [0, 2]] = np.clip(
                boxes[:, [0, 2]], 0, self.input_size
            )
            boxes[:, [1, 3]] = np.clip(
                boxes[:, [1, 3]], 0, self.input_size
            )

            keep = self._nms(
                boxes,
                confidences,
                class_ids,
                float(Config.IOU_THRESHOLD),
            )

            if not keep:
                return 0, False, 0.0, None

            coeffs = pred[:, 4 + nc:]
            img_h, img_w = image.shape[:2]
            img_area = float(img_h * img_w)

            best = None

            for idx in keep:
                polygon, area_px = self._mask_to_polygon(
                    coeffs[idx],
                    proto,
                    boxes[idx],
                    image.shape,
                    meta,
                )

                if polygon is None or len(polygon) < 3:
                    continue

                if area_px < float(Config.MIN_MASK_AREA_PX):
                    continue

                cid = int(class_ids[idx])
                conf = float(confidences[idx])

                if best is None or conf > best["conf"]:
                    best = {
                        "cid": cid,
                        "conf": conf,
                        "polygon": polygon,
                        "area_px": area_px,
                    }

            if best is None:
                logger.debug("No valid mask -> reject")
                return 0, False, 0.0, None

            cid = best["cid"]
            conf = best["conf"]
            polygon = best["polygon"]
            area_ratio = best["area_px"] / img_area

            is_large = (
                area_ratio >= float(Config.SIZE_THRESHOLD_RATIO)
            )

            if cid == 0:
                return 0, False, conf, polygon

            size_class = 2 if is_large else 1
            return size_class, True, conf, polygon

        except Exception as e:
            logger.error(f"ONNX classify error: {e}")
            return 0, False, 0.0, None

# ======================================================================
# TEST ĐỘC LẬP: python classifier.py <ảnh>
# ======================================================================
if __name__ == "__main__":

    clf = ONNXClassifier()

    if not clf.load():
        sys.exit(1)

    if len(sys.argv) < 2:
        print(
            "Dùng: python classifier.py <đường_dẫn_ảnh>"
        )
        sys.exit(0)

    path = sys.argv[1]

    img = cv2.imread(path)

    if img is None:
        logger.error(
            f"Không đọc được ảnh: {path}"
        )
        sys.exit(1)

    scls, is_good, conf, poly = clf.classify(img)

    h, w = img.shape[:2]

    area = (
        cv2.contourArea(
            np.asarray(poly, np.float32)
        )
        if poly is not None
        else 0.0
    )

    print(f"\n  ảnh        : {w}x{h}")

    print(
        f"  device     : {clf.device}"
    )

    print(
        f"  kết quả    : "
        f"{'PASS' if is_good else 'DEFECT/REJECT'}"
    )

    size_name = {
    0: "-",
    1: "S",
    2: "L",
    }.get(scls, "?")

    print(
        f"  size_class : {scls}  "
        f"({size_name})"
    )

    print(
        f"  confidence : {conf:.3f}"
    )

    print(
        f"  mask area  : {area:.0f} px"
    )

    print(
        f"  area_ratio : {area / (w * h):.4f}"
        f"  (ngưỡng {Config.SIZE_THRESHOLD_RATIO})"
    )

    # Đo tốc độ để so CPU vs GPU
    # Bỏ lần đầu vì đã warmup ở load
    import time

    ts = []

    for _ in range(3):

        t0 = time.time()

        clf.classify(img)

        ts.append(
            time.time() - t0
        )

    print(
        f"  thời gian  : "
        f"{min(ts):.3f}s/ảnh "
        f"(nhanh nhất trong 3 lần)"
    )