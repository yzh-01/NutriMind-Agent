"""
数据集准备与预处理工具模块 — Phase 1.1 数据集准备。

职责：
- 下载公开食物数据集（UECFOOD-100 / COCO Food 子集）
- 验证 YOLO TXT 格式标注文件的正确性
- 将标注转换为 YOLO 格式（归一化坐标）
- 自动生成 data.yaml 配置文件
- 按比例划分训练/验证/测试集
- 下载 ultralytics 预训练权重（yolo11n.pt 等）

使用方式：
    # CLI 子命令
    uv run python -m app.services.data_utils download    # 下载数据集
    uv run python -m app.services.data_utils validate    # 验证标注文件
    uv run python -m app.services.data_utils split       # 划分数据集
    uv run python -m app.services.data_utils weights     # 下载预训练权重

    # Python API
    from app.services.data_utils import download_pretrained_weights
    path = download_pretrained_weights("yolo11n")
"""

import argparse
import random
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from app.config.settings import settings

# ==================================================================
# 数据集下载
# ==================================================================

# 常用食物数据集 URL 映射
DATASET_URLS: dict[str, str] = {
    "UECFOOD-100": "http://foodcam.mobi/dataset/100/UECFOOD100.zip",
    "UECFOOD-256": "http://foodcam.mobi/dataset/256/UECFOOD256.zip",
    # COCO 完整数据集太大（~25GB），建议在 AutoDL 云端下载
    "COCO2017": "http://images.cocodataset.org/zips/train2017.zip",
}


def get_default_data_dir() -> Path:
    """获取默认数据目录路径。"""
    return settings.BASE_DIR / "data" / "datasets"


def download_food_dataset(
    dataset_name: str = "UECFOOD-100",
    output_dir: Optional[str] = None,
) -> Path:
    """下载食物数据集并解压。

    Args:
        dataset_name: 数据集名称，支持 "UECFOOD-100"、"UECFOOD-256"
        output_dir: 输出目录（可选，默认为 data/datasets/）

    Returns:
        解压后的数据集目录路径

    Raises:
        ValueError: 不支持的数据集名称
        RuntimeError: 下载失败
    """
    if dataset_name not in DATASET_URLS:
        raise ValueError(
            f"不支持的数据集: {dataset_name}。支持: {list(DATASET_URLS.keys())}"
        )

    import urllib.request

    target_dir = Path(output_dir) if output_dir else get_default_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    url = DATASET_URLS[dataset_name]
    zip_path = target_dir / f"{dataset_name}.zip"

    print(f"[下载] 正在从 {url} 下载 {dataset_name} ...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print(f"[下载] 完成: {zip_path}")
    except Exception as e:
        raise RuntimeError(f"数据集下载失败: {e}") from e

    # 解压
    extract_dir = target_dir / dataset_name
    print(f"[解压] 正在解压到 {extract_dir} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    print(f"[解压] 完成: {extract_dir}")

    # 删除 zip 文件
    zip_path.unlink()

    return extract_dir


# ==================================================================
# 标注验证
# ==================================================================

def validate_dataset_structure(dataset_path: Path) -> dict:
    """验证数据集目录结构和 YOLO 标注文件格式。

    期望的目录结构：
        dataset/
        ├── images/
        │   ├── train/
        │   ├── val/
        │   └── test/
        └── labels/
            ├── train/
            ├── val/
            └── test/

    YOLO TXT 格式（归一化坐标）：
        class_id x_center y_center width height

    Args:
        dataset_path: 数据集根目录

    Returns:
        验证结果摘要 dict: {
            "valid": bool,
            "train_images": int, "train_labels": int,
            "val_images": int, "val_labels": int,
            "test_images": int, "test_labels": int,
            "errors": list[str],
            "warnings": list[str],
        }
    """
    result = {
        "valid": True,
        "train_images": 0,
        "train_labels": 0,
        "val_images": 0,
        "val_labels": 0,
        "test_images": 0,
        "test_labels": 0,
        "errors": [],
        "warnings": [],
    }

    for split in ["train", "val", "test"]:
        img_dir = dataset_path / "images" / split
        lbl_dir = dataset_path / "labels" / split

        if not img_dir.exists():
            result["errors"].append(f"缺少图片目录: {img_dir}")
            result["valid"] = False
            continue

        result[f"{split}_images"] = len(list(img_dir.glob("*")))

        if not lbl_dir.exists():
            result["warnings"].append(f"缺少标注目录: {lbl_dir}（如果正在进行格式转换这是正常的）")
            result[f"{split}_labels"] = 0
            continue

        # 验证标注文件
        label_files = list(lbl_dir.glob("*.txt"))
        result[f"{split}_labels"] = len(label_files)

        for lbl_file in label_files:
            file_errors = _validate_single_label(lbl_file)
            if file_errors:
                result["errors"].extend(
                    [f"{lbl_file.name}: {e}" for e in file_errors]
                )
                result["valid"] = False

    return result


def _validate_single_label(label_path: Path) -> list[str]:
    """验证单个 YOLO 标注文件的内容合法性。

    每行格式：class_id x_center y_center width height
    - class_id: 非负整数
    - bbox 4 个值: 均应在 [0, 1] 范围内（归一化坐标）

    Args:
        label_path: 标注文件路径

    Returns:
        错误信息列表（空列表表示无错误）
    """
    errors = []
    try:
        with open(label_path, "r") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 5:
                    errors.append(f"第 {line_no} 行格式错误，需要 5 个值，实际 {len(parts)} 个")
                    continue

                try:
                    class_id = int(parts[0])
                    x, y, w, h = map(float, parts[1:])
                except ValueError:
                    errors.append(f"第 {line_no} 行包含非数值内容")
                    continue

                if class_id < 0:
                    errors.append(f"第 {line_no} 行 class_id 为负数: {class_id}")

                for name, val in [("x_center", x), ("y_center", y), ("width", w), ("height", h)]:
                    if not (0.0 <= val <= 1.0):
                        errors.append(
                            f"第 {line_no} 行 {name}={val} 超出 [0,1] 范围"
                        )
    except Exception as e:
        errors.append(f"读取文件失败: {e}")

    return errors


def verify_yolo_labels(label_dir: Path, num_classes: int) -> tuple[int, list[str]]:
    """批量验证目录下所有标注文件，检查 class_id 是否在合法范围内。

    Args:
        label_dir: 标注文件目录
        num_classes: 预期的类别总数

    Returns:
        (有效文件数, 错误列表)
    """
    valid_count = 0
    all_errors = []

    for lbl_file in label_dir.glob("*.txt"):
        errors = _validate_single_label(lbl_file)
        if not errors:
            # 额外检查 class_id 范围
            with open(lbl_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 1:
                        try:
                            cid = int(parts[0])
                            if cid >= num_classes:
                                all_errors.append(
                                    f"{lbl_file.name}: class_id={cid} 超出范围 (0-{num_classes - 1})"
                                )
                        except ValueError:
                            pass
            valid_count += 1
        else:
            all_errors.extend([f"{lbl_file.name}: {e}" for e in errors])

    return valid_count, all_errors


# ==================================================================
# 格式转换
# ==================================================================

def convert_to_yolo_format(
    annotation_path: Path,
    output_path: Path,
    class_mapping: dict[str, int],
    img_width: int = 640,
    img_height: int = 640,
) -> int:
    """将非 YOLO 格式的标注转换为 YOLO TXT 格式。

    支持输入格式：每行包含 class_name x1 y1 x2 y2（像素坐标）

    Args:
        annotation_path: 原始标注文件路径
        output_path: 输出的 YOLO 标注目录
        class_mapping: 类别名到 class_id 的映射
        img_width: 原始图片宽度（像素）
        img_height: 原始图片高度（像素）

    Returns:
        转换成功的文件数
    """
    output_path.mkdir(parents=True, exist_ok=True)
    converted = 0

    for ann_file in annotation_path.glob("*.txt"):
        yolo_lines = []
        with open(ann_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                # 尝试解析 "class_name x1 y1 x2 y2"
                if len(parts) >= 5 and not parts[0].replace(".", "").isdigit():
                    class_name = parts[0]
                    if class_name not in class_mapping:
                        continue
                    cid = class_mapping[class_name]
                    x1, y1, x2, y2 = map(float, parts[1:5])
                elif len(parts) == 5:
                    # 已是 class_id + 像素坐标格式
                    cid = int(parts[0])
                    x1, y1, x2, y2 = map(float, parts[1:5])
                else:
                    continue

                # 像素坐标 → 归一化 YOLO 格式
                x_center = ((x1 + x2) / 2) / img_width
                y_center = ((y1 + y2) / 2) / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height

                # 截断到 [0,1]
                x_center = max(0.0, min(1.0, x_center))
                y_center = max(0.0, min(1.0, y_center))
                width = max(0.0, min(1.0, width))
                height = max(0.0, min(1.0, height))

                yolo_lines.append(
                    f"{cid} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
                )

        if yolo_lines:
            out_file = output_path / ann_file.name
            with open(out_file, "w") as f:
                f.writelines(yolo_lines)
            converted += 1

    return converted


# ==================================================================
# data.yaml 生成
# ==================================================================

def generate_data_yaml(
    dataset_path: Path,
    output_path: Path,
    class_names: list[str],
    nc: Optional[int] = None,
) -> Path:
    """生成 YOLO 训练所需的 data.yaml 配置文件。

    内容格式：
        path: /absolute/path/to/dataset
        train: images/train
        val: images/val
        test: images/test  (可选)
        nc: 类别数
        names: [class1, class2, ...]

    Args:
        dataset_path: 数据集根目录（包含 images/ 和 labels/ 子目录）
        output_path: 输出的 yaml 文件路径
        class_names: 类别名列表（英文）
        nc: 类别数（可选，默认从 class_names 中推断）

    Returns:
        生成的 data.yaml 路径
    """
    nc_value = nc if nc is not None else len(class_names)

    yaml_content = f"""# Auto-generated by NutriMind-Agent data_utils
# Dataset: {dataset_path.name}
# Generated at: {__import__('datetime').datetime.now()}

path: {dataset_path.absolute().as_posix()}
train: images/train
val: images/val
test: images/test

nc: {nc_value}
names: {class_names}
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[生成] data.yaml 已保存至: {output_path}")
    return output_path


# ==================================================================
# 数据集划分
# ==================================================================

def split_dataset(
    image_dir: Path,
    label_dir: Path,
    output_dir: Path,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> dict:
    """将图片和标注文件按比例随机划分到 train/val/test 目录。

    Args:
        image_dir: 原始图片目录
        label_dir: 原始标注目录
        output_dir: 输出根目录（将创建 images/train, labels/train 等子目录）
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        seed: 随机种子

    Returns:
        划分结果统计: {"train": N, "val": N, "test": N}
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.001, "三部分比例之和必须为 1"

    random.seed(seed)

    # 获取所有图片文件
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    image_files = [
        f for f in sorted(image_dir.glob("*"))
        if f.suffix.lower() in image_extensions
    ]
    random.shuffle(image_files)

    n_total = len(image_files)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_files = image_files[:n_train]
    val_files = image_files[n_train : n_train + n_val]
    test_files = image_files[n_train + n_val :]

    splits = {"train": train_files, "val": val_files, "test": test_files}
    counts = {}

    for split_name, files in splits.items():
        out_img_dir = output_dir / "images" / split_name
        out_lbl_dir = output_dir / "labels" / split_name
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_file in files:
            # 复制图片
            shutil.copy2(img_file, out_img_dir / img_file.name)

            # 复制对应的标注文件
            lbl_file = label_dir / f"{img_file.stem}.txt"
            if lbl_file.exists():
                shutil.copy2(lbl_file, out_lbl_dir / lbl_file.name)

        counts[split_name] = len(files)
        print(f"[划分] {split_name}: {len(files)} 张图片")

    print(f"[划分] 完成。总计 {n_total} 张图片 → train:{counts['train']} / val:{counts['val']} / test:{counts['test']}")
    return counts


# ==================================================================
# 预训练权重下载
# ==================================================================

# ultralytics 支持的 YOLOv11 预训练模型
AVAILABLE_WEIGHTS = [
    "yolo11n",   # YOLOv11 Nano
    "yolo11s",   # YOLOv11 Small
    "yolo11m",   # YOLOv11 Medium
    "yolo11l",   # YOLOv11 Large
    "yolo11x",   # YOLOv11 XLarge
]


def download_pretrained_weights(
    model_name: str = "yolo11n",
    output_dir: Optional[str] = None,
) -> Path:
    """下载 ultralytics YOLOv11 预训练权重文件。

    首次调用时从 ultralytics 官方下载，后续使用本地缓存。

    Args:
        model_name: 模型名称，如 "yolo11n", "yolo11s", "yolo11m"
        output_dir: 输出目录（可选，默认 data/models/）

    Returns:
        权重文件路径
    """
    from ultralytics import YOLO

    target_dir = Path(output_dir) if output_dir else settings.MODELS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # ultralytics 首次加载时会自动下载权重到系统缓存目录
    # 这里显式加载以触发下载，然后将文件复制到项目目录
    print(f"[下载] 正在加载预训练模型 {model_name}.pt ...")
    model = YOLO(f"{model_name}.pt")

    # 检查 ultralytics 缓存中的权重文件
    # ultralytics 将权重缓存在 ~/.config/ultralytics/ 或类似位置
    import os

    ultralytics_home = Path(
        os.environ.get("ULTRALYTICS_HOME", Path.home() / ".config" / "ultralytics")
    )
    cached_weight = ultralytics_home / f"{model_name}.pt"

    if cached_weight.exists():
        target_path = target_dir / f"{model_name}.pt"
        if not target_path.exists():
            shutil.copy2(str(cached_weight), str(target_path))
            print(f"[下载] 权重已复制到: {target_path}")
        else:
            print(f"[下载] 权重已存在: {target_path}")
        return target_path
    else:
        # 如果 ultralytics 缓存中找不到，尝试从当前目录查找
        local_path = Path(f"{model_name}.pt")
        if local_path.exists():
            target_path = target_dir / f"{model_name}.pt"
            shutil.copy2(str(local_path), str(target_path))
            return target_path

        print(f"[警告] 无法定位 {model_name}.pt 权重文件，但模型已加载。")
        print(f"[提示] ultralytics 缓存目录: {ultralytics_home}")
        return target_dir / f"{model_name}.pt"


# ==================================================================
# CLI 入口
# ==================================================================

def _build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="data_utils",
        description="NutriMind-Agent 数据集准备与预处理工具（Phase 1.1）",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # download
    p_dl = sub.add_parser("download", help="下载食物数据集")
    p_dl.add_argument("--dataset", default="UECFOOD-100", choices=list(DATASET_URLS.keys()))
    p_dl.add_argument("--output", default=None, help="输出目录")

    # validate
    p_val = sub.add_parser("validate", help="验证数据集结构和标注文件")
    p_val.add_argument("--dataset-path", required=True, help="数据集根目录路径")
    p_val.add_argument("--num-classes", type=int, default=None, help="预期类别数")

    # convert
    p_cvt = sub.add_parser("convert", help="转换标注格式为 YOLO TXT")
    p_cvt.add_argument("--input", required=True, help="原始标注目录")
    p_cvt.add_argument("--output", required=True, help="输出目录")
    p_cvt.add_argument("--class-mapping", required=True, help="类别映射 JSON 文件路径")
    p_cvt.add_argument("--img-width", type=int, default=640)
    p_cvt.add_argument("--img-height", type=int, default=640)

    # split
    p_sp = sub.add_parser("split", help="划分 train/val/test")
    p_sp.add_argument("--image-dir", required=True, help="原始图片目录")
    p_sp.add_argument("--label-dir", required=True, help="原始标注目录")
    p_sp.add_argument("--output", required=True, help="输出根目录")
    p_sp.add_argument("--train-ratio", type=float, default=0.7)
    p_sp.add_argument("--val-ratio", type=float, default=0.15)
    p_sp.add_argument("--test-ratio", type=float, default=0.15)
    p_sp.add_argument("--seed", type=int, default=42)

    # weights
    p_wt = sub.add_parser("weights", help="下载预训练权重")
    p_wt.add_argument("--model", default="yolo11n", choices=AVAILABLE_WEIGHTS)
    p_wt.add_argument("--output", default=None, help="输出目录")

    # generate-yaml
    p_yaml = sub.add_parser("generate-yaml", help="生成 data.yaml")
    p_yaml.add_argument("--dataset-path", required=True)
    p_yaml.add_argument("--output", required=True)
    p_yaml.add_argument("--class-names", required=True, help="逗号分隔的类别名列表")
    p_yaml.add_argument("--nc", type=int, default=None)

    return parser


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "download":
        download_food_dataset(dataset_name=args.dataset, output_dir=args.output)

    elif args.command == "validate":
        ds_path = Path(args.dataset_path)
        result = validate_dataset_structure(ds_path)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.num_classes:
            for split in ["train", "val", "test"]:
                lbl_dir = ds_path / "labels" / split
                if lbl_dir.exists():
                    valid, errors = verify_yolo_labels(lbl_dir, args.num_classes)
                    print(f"\n{split} 标注验证: {valid} 个有效文件, {len(errors)} 个错误")

    elif args.command == "convert":
        import json
        with open(args.class_mapping, "r") as f:
            mapping = json.load(f)
        n = convert_to_yolo_format(
            Path(args.input), Path(args.output), mapping,
            args.img_width, args.img_height
        )
        print(f"转换完成: {n} 个文件")

    elif args.command == "split":
        counts = split_dataset(
            Path(args.image_dir), Path(args.label_dir), Path(args.output),
            args.train_ratio, args.val_ratio, args.test_ratio, args.seed
        )
        print(f"划分结果: {counts}")

    elif args.command == "weights":
        path = download_pretrained_weights(model_name=args.model, output_dir=args.output)
        print(f"预训练权重位置: {path}")

    elif args.command == "generate-yaml":
        class_names_list = [n.strip() for n in args.class_names.split(",")]
        generate_data_yaml(
            Path(args.dataset_path), Path(args.output), class_names_list, args.nc
        )

    else:
        parser.print_help()
