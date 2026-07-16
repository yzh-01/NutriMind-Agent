# -*- coding: utf-8 -*-
"""验证训练好的 YOLO11 模型能否正常加载和推理。

用法:
  python test_model.py                             # 仅验证模型加载
  python test_model.py --image path/to/food.jpg    # 对指定图片推理
"""

import argparse
import sys
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "data" / "models" / "yolo11_food_best.pt"


def test_load():
    print("[1/2] 模型路径: %s" % MODEL_PATH)
    if not MODEL_PATH.exists():
        print("FAIL: 模型文件不存在!")
        return None

    size_mb = MODEL_PATH.stat().st_size / (1024 ** 2)
    print("      模型大小: %.1f MB" % size_mb)

    try:
        from ultralytics import YOLO
        model = YOLO(str(MODEL_PATH))
        print("      模型加载成功")
        print("      共 %d 个食物类别" % len(model.names))
        return model
    except Exception as e:
        print("FAIL: 模型加载失败: %s" % e)
        return None


def test_inference(model, image_path: str):
    if not Path(image_path).exists():
        print("FAIL: 图片不存在: %s" % image_path)
        return

    print("\n[2/2] 推理: %s" % image_path)
    results = model.predict(source=image_path, conf=0.25, verbose=False)
    result = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        print("      未检测到任何食物")
        return

    print("      检测到 %d 个目标:" % len(result.boxes))
    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = result.names[cls_id]
        conf = float(box.conf[0])
        print("        %-25s  %.2f%%" % (cls_name, conf * 100))

    print("      推理正常完成")


def main():
    parser = argparse.ArgumentParser(description="NutriMind-Agent YOLOv11 模型验证")
    parser.add_argument("--image", type=str, help="测试图片路径(可选)")
    args = parser.parse_args()

    print("=" * 50)
    print("NutriMind-Agent YOLOv11 模型验证")
    print("=" * 50)

    model = test_load()
    if model is None:
        sys.exit(1)

    if args.image:
        test_inference(model, args.image)
    else:
        print("\n提示: 传入 --image 参数可对图片推理")
        print("   python test_model.py --image 你的图片.jpg")

    print("\n验证结束!")


if __name__ == "__main__":
    main()
