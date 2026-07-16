#!/usr/bin/env python3
"""
AutoDL YOLOv11 训练脚本 — NutriMind-Agent

针对 RTX 3080 Ti (12GB VRAM) / 90GB RAM / 12 核 CPU 深度优化。

核心优化:
  - batch=32 启动，OOM 时自动降级到 16/12/8/4
  - cache='ram' 利用 90GB 大内存缓存全部图片（极限 I/O 加速）
  - workers=8 充分利用 12 核 CPU
  - amp=True 自动混合精度（节省显存 + 加速）
  - patience=10 早停（10 轮无提升自动结束，省算力费）
  - yolo11s.pt 预训练权重

用法:
  # 基本训练
  python train_yolo.py --data /root/autodl-tmp/UECFOOD256/data.yaml

  # 后台运行（防止 SSH 断开）
  nohup python train_yolo.py --data /root/autodl-tmp/UECFOOD256/data.yaml > /tmp/train.log 2>&1 &

  # 仅检查环境
  python train_yolo.py --check-env

环境依赖:
  pip install ultralytics>=8.3.0
"""

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Optional


# ==================================================================
# 默认配置（针对 RTX 3080 Ti + 90GB RAM 优化）
# ==================================================================

class Config:
    """训练超参数默认值。"""
    MODEL_NAME = "yolo11s"              # YOLOv11 Small
    EPOCHS = 100                        # 训练轮数
    IMG_SIZE = 640                      # 输入图像尺寸
    BATCH = 32                          # 初始 batch size（OOM 时自动降级）
    WORKERS = 8                         # 数据加载线程数（12 核 CPU 的 2/3）
    PATIENCE = 15                       # 早停轮数（256 类数据集更大，放宽一些）
    CACHE = "ram"                       # 缓存策略（90GB 内存充足）
    AMP = True                          # 自动混合精度
    DEVICE = 0                          # GPU 设备编号
    OUTPUT_NAME = "yolo11_food_best.pt" # 最终输出模型名
    MODEL_OUTPUT_DIR = None             # 模型输出目录（运行时计算）


# 备用 batch size 列表（从大到小尝试）
BATCH_SIZE_FALLBACKS = [32, 24, 16, 12, 8, 4, 2]


# ==================================================================
# 环境检查
# ==================================================================

def check_environment() -> dict:
    """检查训练环境是否就绪。"""
    info = {
        "ultralytics_available": False,
        "cuda_available": False,
        "gpu_name": "N/A",
        "vram_gb": 0,
        "ram_gb": 0,
    }

    print("=" * 60)
    print("[ENV] 环境检查")
    print("=" * 60)

    # 1. ultralytics
    try:
        import ultralytics
        info["ultralytics_available"] = True
        print(f"  OK  ultralytics {ultralytics.__version__}")
    except ImportError:
        print("  FAIL  ultralytics 未安装: pip install ultralytics>=8.3.0")
        return info

    # 2. CUDA
    try:
        import torch
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  OK  CUDA: {info['gpu_name']}  ({info['vram_gb']:.1f} GB VRAM)")
        else:
            print("  WARN  CUDA 不可用，将使用 CPU（极慢）")
    except ImportError:
        print("  WARN  torch 未安装")

    # 3. 系统内存
    try:
        import psutil
        info["ram_gb"] = psutil.virtual_memory().total / (1024**3)
        print(f"  OK  内存: {info['ram_gb']:.1f} GB")
    except ImportError:
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        info["ram_gb"] = int(line.split()[1]) / (1024**2)
                        print(f"  OK  内存: {info['ram_gb']:.1f} GB")
                        break
        except Exception:
            print("  WARN  无法检测内存")

    # 4. 数据盘
    autodl_tmp = Path("/root/autodl-tmp")
    if autodl_tmp.exists():
        try:
            usage = shutil.disk_usage(autodl_tmp)
            print(f"  OK  数据盘: {usage.free / (1024**3):.1f} GB 可用")
        except Exception:
            pass

    print("=" * 60)
    return info


# ==================================================================
# 训练主逻辑
# ==================================================================

def run_training(
    data_yaml: str,
    model_name: str = Config.MODEL_NAME,
    epochs: int = Config.EPOCHS,
    img_size: int = Config.IMG_SIZE,
    batch: int = Config.BATCH,
    workers: int = Config.WORKERS,
    patience: int = Config.PATIENCE,
    cache: str = Config.CACHE,
    amp: bool = Config.AMP,
    device: int = Config.DEVICE,
    model_output_dir: Optional[Path] = None,
) -> dict:
    """执行 YOLOv11 训练。

    包含自动 batch size 降级机制：CUDA OOM 时依次尝试更小的 batch size。
    """
    from ultralytics import YOLO

    data_path = Path(data_yaml)
    if not data_path.exists():
        print(f"FAIL: data.yaml 不存在: {data_yaml}")
        sys.exit(1)

    # 模型输出目录
    if model_output_dir is None:
        model_output_dir = Path(__file__).resolve().parent / "data" / "models"
    model_output_dir.mkdir(parents=True, exist_ok=True)

    pretrained = f"{model_name}.pt"
    print(f"\n[MODEL] 预训练权重: {pretrained}")

    # 打印配置
    print()
    print("=" * 60)
    print("[CONFIG] 训练配置")
    print("=" * 60)
    print(f"  模型:          {model_name}")
    print(f"  数据配置:      {data_yaml}")
    print(f"  Epochs:        {epochs}")
    print(f"  Image Size:    {img_size}")
    print(f"  Batch Size:    {batch} (初始，OOM 自动降级)")
    print(f"  Workers:       {workers}")
    print(f"  Cache:         {cache}")
    print(f"  AMP:           {amp}")
    print(f"  Patience:      {patience}")
    print(f"  模型输出:      {model_output_dir / Config.OUTPUT_NAME}")
    print("=" * 60)

    # 自动 batch size 降级
    batch_sizes_to_try = [batch] + [b for b in BATCH_SIZE_FALLBACKS if b < batch]

    for attempt, bs in enumerate(batch_sizes_to_try):
        try:
            print(f"\n{'='*60}")
            if attempt > 0:
                print(f"[RETRY] batch={bs} (前次 OOM: {batch_sizes_to_try[attempt-1]})")
            print(f"[TRAIN] 开始训练 (batch={bs})")
            print(f"{'='*60}")
            start_time = time.time()

            model = YOLO(pretrained)
            results = model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=img_size,
                batch=bs,
                workers=workers,
                patience=patience,
                cache=cache,
                amp=amp,
                device=device,
                exist_ok=True,
                pretrained=True,
                verbose=True,
                # 数据增强
                hsv_h=0.015,
                hsv_s=0.7,
                hsv_v=0.4,
                degrees=5.0,
                translate=0.1,
                scale=0.3,
                shear=2.0,
                perspective=0.0,
                flipud=0.0,
                fliplr=0.5,
                mosaic=0.5,
                mixup=0.1,
            )

            elapsed = time.time() - start_time
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)

            print(f"\n{'='*60}")
            print(f"[DONE] 训练完成!")
            print(f"{'='*60}")
            print(f"  总耗时: {int(h)}h {int(m)}m {int(s)}s")
            print(f"  Batch:  {bs}")

            metrics = extract_metrics(results)
            print_metrics(metrics)

            # 复制最佳权重
            best_source = _find_best_pt(results)
            best_dest = model_output_dir / Config.OUTPUT_NAME
            if best_source and best_source.exists():
                shutil.copy2(best_source, best_dest)
                print(f"\n[MODEL] best.pt -> {best_dest}")
                print(f"        大小: {best_dest.stat().st_size / (1024**2):.1f} MB")

            metrics["output_model"] = str(best_dest)
            metrics["batch_used"] = bs
            metrics["training_time_seconds"] = round(elapsed, 1)
            return metrics

        except RuntimeError as e:
            error_msg = str(e)
            if "out of memory" in error_msg.lower() or "OOM" in error_msg:
                print(f"\n[OOM] CUDA OOM (batch={bs})")
                if attempt < len(batch_sizes_to_try) - 1:
                    print(f"      -> 降级 batch={batch_sizes_to_try[attempt+1]}, 重试...")
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                    time.sleep(3)
                    continue
            print(f"\n[FAIL] 训练失败: {error_msg}")
            raise

    print(f"\n[FAIL] 所有 batch size 均 OOM: {batch_sizes_to_try}")
    print("  建议: 减小 img_size 或 使用更小的模型 (yolo11n)")
    sys.exit(1)


# ==================================================================
# 指标提取与展示
# ==================================================================

def extract_metrics(results) -> dict:
    """从 ultralytics 训练结果中提取关键指标。"""
    metrics = {}
    try:
        if hasattr(results, "results_dict"):
            rd = results.results_dict
            metrics["mAP50"] = float(rd.get("metrics/mAP50(B)", 0))
            metrics["mAP50-95"] = float(rd.get("metrics/mAP50-95(B)", 0))
            metrics["precision"] = float(rd.get("metrics/precision(B)", 0))
            metrics["recall"] = float(rd.get("metrics/recall(B)", 0))
    except Exception:
        pass

    if hasattr(results, "save_dir"):
        csv_path = Path(results.save_dir) / "results.csv"
        if csv_path.exists():
            metrics["results_csv"] = str(csv_path)
        metrics["save_dir"] = str(results.save_dir)

    return metrics


def _find_best_pt(results) -> Optional[Path]:
    """查找训练产出的 best.pt 文件。"""
    if hasattr(results, "save_dir"):
        best_path = Path(results.save_dir) / "weights" / "best.pt"
        if best_path.exists():
            return best_path

    runs_dir = Path.cwd() / "runs" / "detect"
    if runs_dir.exists():
        train_dirs = sorted(
            runs_dir.glob("train*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for d in train_dirs:
            best_path = d / "weights" / "best.pt"
            if best_path.exists():
                return best_path
    return None


def print_metrics(metrics: dict) -> None:
    """格式化打印训练指标。"""
    print(f"\n{'='*60}")
    print("[METRICS] 最终训练指标")
    print("=" * 60)
    for key, label in [("mAP50", "mAP@50"), ("mAP50-95", "mAP@50-95"),
                        ("precision", "Precision"), ("recall", "Recall")]:
        if key in metrics and metrics[key] is not None:
            print(f"  {label:12s}: {metrics[key]:.4f}")

    if "training_time_seconds" in metrics:
        t = metrics["training_time_seconds"]
        h, m = divmod(t, 3600)
        m, s = divmod(m, 60)
        print(f"  训练耗时      : {int(h)}h {int(m)}m {int(s)}s")

    if "batch_used" in metrics:
        print(f"  Batch Size    : {metrics['batch_used']}")

    if "save_dir" in metrics:
        print(f"  输出目录      : {metrics['save_dir']}")
    print("=" * 60)


# ==================================================================
# CLI
# ==================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NutriMind-Agent YOLOv11 训练脚本 (AutoDL 优化版)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--data", type=str, help="data.yaml 配置文件路径")
    parser.add_argument("--model", type=str, default=Config.MODEL_NAME,
                        help=f"预训练模型 (默认: {Config.MODEL_NAME})")
    parser.add_argument("--epochs", type=int, default=Config.EPOCHS)
    parser.add_argument("--img-size", type=int, default=Config.IMG_SIZE)
    parser.add_argument("--batch", type=int, default=Config.BATCH)
    parser.add_argument("--workers", type=int, default=Config.WORKERS)
    parser.add_argument("--patience", type=int, default=Config.PATIENCE)
    parser.add_argument("--no-cache", action="store_true", help="禁用 RAM 缓存")
    parser.add_argument("--no-amp", action="store_true", help="禁用 AMP")
    parser.add_argument("--device", type=int, default=Config.DEVICE)
    parser.add_argument("--output-dir", type=Path, default=None, help="模型输出目录")
    parser.add_argument("--check-env", action="store_true", help="仅检查环境")

    args = parser.parse_args()

    if args.check_env:
        check_environment()
        return

    if args.data is None:
        parser.print_help()
        print("\n请指定 --data 参数")
        sys.exit(1)

    env_info = check_environment()
    if not env_info["ultralytics_available"]:
        sys.exit(1)

    metrics = run_training(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        img_size=args.img_size,
        batch=args.batch,
        workers=args.workers,
        patience=args.patience,
        cache=False if args.no_cache else Config.CACHE,
        amp=False if args.no_amp else Config.AMP,
        device=args.device,
        model_output_dir=args.output_dir,
    )

    print(f"\n[DONE] 训练完成!")
    print(f"  模型: {metrics.get('output_model', 'N/A')}")


if __name__ == "__main__":
    main()
