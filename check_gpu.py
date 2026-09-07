import json
import time
from pathlib import Path
import numpy as np
import onnxruntime as ort

MODEL = Path(__file__).resolve().parent / "best.onnx"
DEVICE_ID = 0
RUNS = 10

def main():
    print("=" * 60)
    print("ONNX Runtime GPU verification")
    print("=" * 60)
    if not MODEL.exists():
        print(f"ERROR: Không tìm thấy model: {MODEL}")
        return
    ort.preload_dlls()
    print(f"ORT version : {ort.__version__}")
    print(f"Available EP: {ort.get_available_providers()}")
    print(f"ORT device  : {ort.get_device()}")
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        print("\nFAIL: CUDAExecutionProvider không khả dụng.")
        return
    so = ort.SessionOptions()
    so.enable_profiling = True
    so.profile_file_prefix = str(Path(__file__).resolve().parent / "ort_gpu_profile")
    session = ort.InferenceSession(str(MODEL), sess_options=so, providers=[("CUDAExecutionProvider", {"device_id": DEVICE_ID}), "CPUExecutionProvider"])
    print("Session providers:", session.get_providers())
    print("Provider options :", session.get_provider_options())
    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    x = np.random.rand(1, 3, 1280, 1280).astype(np.float32)
    print(f"\nRunning {RUNS} inferences...")
    for _ in range(3): session.run(None, {input_name: x})
    t0 = time.perf_counter()
    for _ in range(RUNS): session.run(None, {input_name: x})
    elapsed = time.perf_counter() - t0
    print(f"Average inference: {elapsed / RUNS * 1000:.2f} ms")
    print(f"Throughput        : {RUNS / elapsed:.2f} FPS")
    profile_path = Path(session.end_profiling())
    print(f"\nProfile file: {profile_path}")
    try:
        events = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as e:
        print("Không đọc được profile:", e)
        return
    providers_seen = {}
    cuda_events = []
    for event in events:
        provider = event.get("args", {}).get("provider")
        if provider:
            providers_seen[provider] = providers_seen.get(provider, 0) + 1
        if provider == "CUDAExecutionProvider":
            cuda_events.append(event)
    print("\nProviders recorded in ORT profiling:")
    for provider, count in sorted(providers_seen.items()): print(f"  {provider}: {count} events")
    print(f"\nCUDAExecutionProvider events: {len(cuda_events)}")
    if cuda_events:
        print("\n" + "=" * 60)
        print("GPU INFERENCE: CONFIRMED")
        print("=" * 60)
        print("ONNX Runtime recorded graph execution on CUDAExecutionProvider (GPU device 0).")
    else:
        print("\n" + "=" * 60)
        print("GPU INFERENCE: NOT CONFIRMED")
        print("=" * 60)

if __name__ == "__main__": main()
