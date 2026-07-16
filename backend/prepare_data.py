#!/usr/bin/env python3
"""
AutoDL 数据准备脚本 — NutriMind-Agent Phase 1.1

功能：
  1. 从 HuggingFace 下载数据集（支持国内镜像）
  2. 解压位于 /root/autodl-tmp/ 下的 12GB 食物数据集压缩包
  3. 验证解压后的 YOLO 标准目录结构
  4. 自动生成/修正 data.yaml（强制使用绝对路径）

适用环境:
  - AutoDL 算力平台 (RTX 3080 Ti / 12GB VRAM / 90GB RAM)
  - 数据盘挂载路径: /root/autodl-tmp/

用法:
  # 从 HuggingFace 镜像下载
  python prepare_data.py --hf issai/Food_Portion_Benchmark

  # 从本地 zip 解压
  python prepare_data.py --zip /root/autodl-tmp/food_dataset.zip

  # 仅验证
  python prepare_data.py --validate-only --dataset /root/autodl-tmp/Food_Portion_Benchmark
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional


# ==================================================================
# 配置常量
# ==================================================================

# 默认数据盘路径（AutoDL 标准挂载点）
AUTODL_TMP = Path("/root/autodl-tmp")

# 期望的 YOLO 目录结构
REQUIRED_DIRS = [
    "images/train",
    "images/val",
    "labels/train",
    "labels/val",
]

# 常见的食物数据集类别（可按实际数据调整）
DEFAULT_FOOD_CLASSES = [
    "rice", "noodle", "bread", "egg", "chicken", "beef", "pork",
    "fish", "shrimp", "tofu", "broccoli", "carrot", "tomato",
    "potato", "apple", "banana", "orange", "grape", "watermelon",
    "milk", "coffee", "tea", "juice", "cake", "cookie", "salad",
    "pizza", "hamburger", "sushi", "dumpling",
]

# nc 将从实际标注文件中推断，或使用此默认值
DEFAULT_NC = 30


# ==================================================================
# 工具函数
# ==================================================================


def find_zip_files(search_dir: Path) -> list[Path]:
    """在指定目录下查找所有 zip 文件。

    Args:
        search_dir: 搜索目录

    Returns:
        找到的 .zip 文件列表
    """
    if not search_dir.exists():
        return []
    return sorted(search_dir.glob("*.zip"))


def download_from_huggingface(
    dataset_id: str,
    output_dir: Path,
    mirror: bool = True,
    resume: bool = True,
) -> bool:
    """使用 huggingface-cli 从 HuggingFace 下载数据集。

    自动配置国内镜像源（hf-mirror.com），避免连接超时。
    使用 --local-dir-use-symlinks False 确保下载实体文件而非符号链接。

    Args:
        dataset_id: HuggingFace 数据集 ID（如 issai/Food_Portion_Benchmark）
        output_dir: 下载目标目录
        mirror: 是否使用国内镜像（默认 True）
        resume: 是否断点续传（默认 True）

    Returns:
        是否下载成功
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 配置国内镜像
    if mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        print("🌐 已配置国内镜像: https://hf-mirror.com")
    else:
        print("🌐 使用官方源: https://huggingface.co")

    # Step 2: 检查 huggingface-cli 是否可用
    try:
        result = subprocess.run(
            ["huggingface-cli", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        print(f"✅ huggingface-cli 已安装: {result.stdout.strip()}")
    except FileNotFoundError:
        print("⚠️ huggingface-cli 未安装，正在安装...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "huggingface_hub[cli]", "-q"],
                check=True, timeout=120,
            )
            print("✅ huggingface_hub 安装成功")
        except Exception as e:
            print(f"❌ 安装失败: {e}")
            print("   请手动安装: pip install huggingface_hub[cli]")
            return False
    except Exception as e:
        print(f"⚠️ 无法检测 huggingface-cli: {e}")

    # Step 3: 构建下载命令
    cmd = [
        "huggingface-cli", "download",
        dataset_id,
        "--local-dir", str(output_dir),
        "--local-dir-use-symlinks", "False",
        "--repo-type", "dataset",
    ]
    if resume:
        cmd.append("--resume-download")

    print()
    print("=" * 60)
    print("📥 开始从 HuggingFace 下载数据集")
    print("=" * 60)
    print(f"   数据集: {dataset_id}")
    print(f"   目标路径: {output_dir}")
    print(f"   镜像源: {'hf-mirror.com' if mirror else 'huggingface.co'}")
    print(f"   断点续传: {'是' if resume else '否'}")
    print(f"   命令: {' '.join(cmd)}")
    print("=" * 60)
    print()

    # Step 4: 执行下载
    try:
        # 使用实时输出，方便监控进度
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )

        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # 过滤掉不必要的 INFO 行，保持输出简洁
                if "Fetching" in line or "Downloading" in line or "%" in line:
                    print(f"   {line}")
                elif "done" in line.lower() or "complete" in line.lower():
                    print(f"   ✅ {line}")
                elif "error" in line.lower() or "fail" in line.lower():
                    print(f"   ❌ {line}")
                else:
                    # 每 10 行非关键日志只打印一次，避免刷屏
                    pass

        return_code = process.wait()

        if return_code == 0:
            print(f"\n✅ 数据集下载完成: {output_dir}")
            return True
        else:
            print(f"\n❌ 下载失败，退出码: {return_code}")
            print(f"   请尝试:")
            print(f"   1. 检查网络连接")
            print(f"   2. 不使用镜像: python prepare_data.py --hf {dataset_id} --no-mirror")
            print(f"   3. 手动下载: 在终端运行上述命令")
            return False

    except KeyboardInterrupt:
        print("\n⚠️ 下载被中断（支持断点续传，重新运行即可继续）")
        return False
    except Exception as e:
        print(f"\n❌ 下载异常: {e}")
        return False


def download_from_huggingface_python(
    dataset_id: str,
    output_dir: Path,
    mirror: bool = True,
) -> bool:
    """使用 Python huggingface_hub 库下载数据集（备选方案）。

    当 huggingface-cli 不可用或无法正常工作时使用此方法。
    直接调用 snapshot_download API。

    Args:
        dataset_id: HuggingFace 数据集 ID
        output_dir: 下载目标目录
        mirror: 是否使用国内镜像

    Returns:
        是否下载成功
    """
    if mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    try:
        from huggingface_hub import snapshot_download

        print(f"📥 使用 Python API 下载数据集 {dataset_id} ...")
        print(f"   目标路径: {output_dir}")
        print(f"   镜像: {'hf-mirror.com' if mirror else 'huggingface.co'}")

        snapshot_download(
            repo_id=dataset_id,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            repo_type="dataset",
            resume_download=True,
        )

        print(f"✅ 数据集下载完成: {output_dir}")
        return True

    except ImportError:
        print("❌ huggingface_hub 未安装")
        print("   请运行: pip install huggingface_hub")
        return False
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False


def unzip_with_progress(
    zip_path: Path,
    extract_dir: Path,
    chunk_size: int = 128 * 1024 * 1024,  # 128MB 读块
) -> bool:
    """解压大型 zip 文件并显示进度。

    针对 12GB 级别的数据集优化：使用大缓冲区减少 I/O 次数，
    逐文件解压并实时打印进度。

    Args:
        zip_path: 压缩包路径
        extract_dir: 解压目标目录
        chunk_size: 每次读取的字节数

    Returns:
        是否成功解压
    """
    if not zip_path.exists():
        print(f"❌ 压缩包不存在: {zip_path}")
        return False

    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = zf.namelist()
            total_files = len(file_list)
            total_size = sum(info.file_size for info in zf.infolist())
            extracted_size = 0

            print(f"📦 压缩包信息:")
            print(f"   文件路径: {zip_path}")
            print(f"   文件数量: {total_files}")
            print(f"   总大小: {total_size / (1024**3):.2f} GB")
            print(f"   解压到: {extract_dir}")
            print()

            for i, member in enumerate(zf.infolist(), 1):
                zf.extract(member, extract_dir)
                extracted_size += member.file_size

                # 每 100 个文件或每 10% 进度打印一次
                if i % 100 == 0 or i == total_files:
                    pct = (extracted_size / total_size * 100) if total_size > 0 else 0
                    print(
                        f"   [{i:5d}/{total_files}] "
                        f"{extracted_size / (1024**3):.1f}/{total_size / (1024**3):.1f} GB "
                        f"({pct:.0f}%)"
                    )

        print(f"\n✅ 解压完成: {extract_dir}")
        return True

    except zipfile.BadZipFile:
        print(f"❌ 文件损坏或不是有效的 zip 文件: {zip_path}")
        return False
    except Exception as e:
        print(f"❌ 解压失败: {e}")
        return False


def detect_nested_root(extract_dir: Path) -> Path:
    """检测解压后的实际数据根目录。

    处理常见情况：zip 内部多一层目录包装，如:
      food_dataset.zip → food_dataset/images/train/...
    而不是:
      extract_dir/images/train/...

    Args:
        extract_dir: 解压目标目录

    Returns:
        实际的数据根目录
    """
    # 检查 extract_dir 下是否直接包含 images/labels
    has_images = (extract_dir / "images").exists()
    has_labels = (extract_dir / "labels").exists()

    if has_images or has_labels:
        return extract_dir

    # 查找子目录中是否包含 images/labels
    subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    for sub in subdirs:
        if (sub / "images").exists() or (sub / "labels").exists():
            print(f"🔍 检测到嵌套目录结构，实际数据根目录: {sub}")
            return sub

    # 返回原目录
    return extract_dir


def validate_directory_structure(dataset_dir: Path) -> dict:
    """验证 YOLO 数据集目录结构。

    Args:
        dataset_dir: 数据集根目录

    Returns:
        验证结果字典，包含各 split 的图片和标注文件统计
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "train": {"images": 0, "labels": 0, "label_match": 0},
        "val": {"images": 0, "labels": 0, "label_match": 0},
        "test": {"images": 0, "labels": 0, "label_match": 0},
    }

    for required in REQUIRED_DIRS:
        dir_path = dataset_dir / required
        if not dir_path.exists():
            result["errors"].append(f"缺少目录: {required}")
            result["valid"] = False

    if not result["valid"]:
        return result

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    for split in ["train", "val", "test"]:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.exists():
            continue

        # 统计图片
        images = [f for f in img_dir.iterdir() if f.suffix.lower() in image_exts]
        result[split]["images"] = len(images)

        if not lbl_dir.exists():
            result["warnings"].append(f"labels/{split} 目录不存在")
            continue

        # 统计标注文件
        label_files = list(lbl_dir.glob("*.txt"))
        result[split]["labels"] = len(label_files)

        # 检查图片-标注配对
        label_stems = {f.stem for f in label_files}
        paired = sum(1 for img in images if img.stem in label_stems)
        result[split]["label_match"] = paired

        if paired < len(images):
            result["warnings"].append(
                f"{split}: {len(images)} 张图片中仅 {paired} 张有对应标注"
            )

    # 最终有效性判断
    if result["train"]["images"] == 0:
        result["errors"].append("训练集 images/train 中没有图片！")
        result["valid"] = False
    if result["val"]["images"] == 0:
        result["warnings"].append("验证集 images/val 中没有图片（训练可行但无法验证）")

    return result


def infer_class_names(dataset_dir: Path) -> list[str]:
    """从 data.yaml 或标注文件中推断类别名列表。

    优先级:
      1. 读取已有 data.yaml 中的 names
      2. 扫描 labels/train/*.txt 提取所有出现的 class_id，使用默认名称

    Args:
        dataset_dir: 数据集根目录

    Returns:
        类别名列表
    """
    # 尝试读取已有 data.yaml
    for yaml_name in ["data.yaml", "dataset.yaml", "dataset.yml"]:
        yaml_path = dataset_dir / yaml_name
        if yaml_path.exists():
            try:
                # 简单解析 YAML 中的 names 字段
                with open(yaml_path, "r") as f:
                    content = f.read()

                # 查找 names: [...] 块
                import re
                names_match = re.search(r"names:\s*\[(.*?)\]", content, re.DOTALL)
                if names_match:
                    names_str = names_match.group(1)
                    # 提取引号内的字符串
                    names = re.findall(r"['\"]([^'\"]*)['\"]", names_str)
                    if names:
                        print(f"📋 从 {yaml_name} 中读取到 {len(names)} 个类别")
                        return names

                # 尝试 names: 下的逐行列表格式
                names_match = re.search(r"names:\s*\n(.*?)(?:\n\w|\Z)", content, re.DOTALL)
                if names_match:
                    names = re.findall(r"['\"]([^'\"]*)['\"]", names_match.group(1))
                    if names:
                        return names

            except Exception:
                pass

    # 从标注文件推断类别数
    lbl_dir = dataset_dir / "labels" / "train"
    if lbl_dir.exists():
        max_class_id = -1
        for lbl_file in list(lbl_dir.glob("*.txt"))[:500]:
            try:
                with open(lbl_file, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            cid = int(parts[0])
                            max_class_id = max(max_class_id, cid)
            except Exception:
                continue

        if max_class_id >= 0:
            nc = max_class_id + 1
            print(f"📋 从标注文件中推断出 {nc} 个类别 (max_class_id={max_class_id})")
            if nc <= len(DEFAULT_FOOD_CLASSES):
                return DEFAULT_FOOD_CLASSES[:nc]
            # 超出默认列表，生成通用名称
            return [f"class_{i}" for i in range(nc)]

    print("⚠️ 无法推断类别名，使用默认列表")
    return DEFAULT_FOOD_CLASSES


def generate_data_yaml(
    dataset_dir: Path,
    class_names: list[str],
    output_path: Optional[Path] = None,
) -> Path:
    """生成 YOLO 格式的 data.yaml 配置文件。

    path 字段强制使用绝对路径（AutoDL 数据盘要求）。

    Args:
        dataset_dir: 数据集根目录
        class_names: 类别名列表
        output_path: 输出路径（可选，默认在 dataset_dir 下）

    Returns:
        生成的 data.yaml 路径
    """
    if output_path is None:
        output_path = dataset_dir / "data.yaml"

    nc = len(class_names)

    # 检测有哪些 split 可用
    splits = {}
    for split in ["train", "val", "test"]:
        img_dir = dataset_dir / "images" / split
        if img_dir.exists() and list(img_dir.glob("*")):
            splits[split] = f"images/{split}"

    # 确保至少包含 train
    if "train" not in splits:
        print("❌ 未找到训练集图片！")
        sys.exit(1)

    lines = [
        f"# Auto-generated by NutriMind-Agent prepare_data.py",
        f"# AutoDL 训练配置",
        f"",
        f"path: {dataset_dir.absolute().as_posix()}",
        f"train: {splits.get('train', 'images/train')}",
        f"val: {splits.get('val', 'images/val')}",
    ]

    if "test" in splits:
        lines.append(f"test: {splits['test']}")

    lines.extend([
        f"",
        f"# 类别数",
        f"nc: {nc}",
        f"",
        f"# 类别名",
        f"names: {class_names}",
    ])

    content = "\n".join(lines) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ data.yaml 已生成: {output_path}")
    print(f"   绝对路径: {dataset_dir.absolute().as_posix()}")
    print(f"   类别数: {nc}")
    print(f"   splits: {list(splits.keys())}")

    return output_path


def _print_dir_tree(path: Path, prefix: str = "", max_depth: int = 3, _depth: int = 0) -> None:
    """打印目录树结构。

    Args:
        path: 起始路径
        prefix: 行前缀（内部递归用）
        max_depth: 最大递归深度
        _depth: 当前深度（内部用）
    """
    if _depth > max_depth:
        return

    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        conn = "└── " if is_last else "├── "
        print(f"{prefix}{conn}{item.name}")

        if item.is_dir() and _depth < max_depth:
            ext = "    " if is_last else "│   "
            _print_dir_tree(item, prefix + ext, max_depth, _depth + 1)
        elif item.is_dir():
            # 超过深度，只显示目录名
            print(f"{prefix}{'    ' if is_last else '│   '}...")


def print_validation_report(result: dict) -> None:
    """打印目录验证结果报告。"""
    print()
    print("=" * 60)
    print("📊 数据集目录验证报告")
    print("=" * 60)

    for split in ["train", "val", "test"]:
        info = result.get(split, {})
        if info.get("images", 0) > 0:
            label_match = info.get("label_match", 0)
            match_pct = (
                f"({label_match / info['images'] * 100:.0f}% 已标注)"
                if info["images"] > 0
                else ""
            )
            print(
                f"  {split:5s}: {info['images']:6d} 图片 | "
                f"{info.get('labels', 0):6d} 标注 {match_pct}"
            )

    if result["errors"]:
        print(f"\n❌ 错误 ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"   - {e}")

    if result["warnings"]:
        print(f"\n⚠️ 警告 ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"   - {w}")

    if result["valid"]:
        print(f"\n✅ 数据集目录结构验证通过！")
    else:
        print(f"\n❌ 数据集目录结构存在问题，请检查。")

    print("=" * 60)


# ==================================================================
# 主流程
# ==================================================================


def run_prepare(
    zip_path: Path,
    output_dir: Optional[Path] = None,
    class_names: Optional[list[str]] = None,
) -> Path:
    """完整的数据准备流程。

    步骤:
      1. 解压数据集
      2. 检测实际根目录
      3. 验证目录结构
      4. 生成/修正 data.yaml

    Args:
        zip_path: 压缩包路径
        output_dir: 解压输出目录（默认用 zip 同目录下的同名文件夹）
        class_names: 显式指定的类别名（可选，不传则自动推断）

    Returns:
        数据集根目录路径
    """
    print("=" * 60)
    print("🚀 NutriMind-Agent 数据准备脚本 (AutoDL)")
    print("=" * 60)
    print(f"   压缩包: {zip_path}")
    print(f"   数据盘: /root/autodl-tmp/")
    print()

    # Step 1: 解压
    if output_dir is None:
        output_dir = AUTODL_TMP / zip_path.stem

    print("[1/4] 解压数据集...")
    success = unzip_with_progress(zip_path, output_dir)
    if not success:
        sys.exit(1)

    # Step 2: 检测实际根目录
    print("\n[2/4] 检测数据集目录结构...")
    dataset_root = detect_nested_root(output_dir)
    print(f"   数据集根目录: {dataset_root}")

    # Step 3: 验证目录结构
    print("\n[3/4] 验证 YOLO 目录结构...")
    validation = validate_directory_structure(dataset_root)
    print_validation_report(validation)

    if not validation["valid"]:
        print("\n❌ 目录验证失败，请检查数据集结构。")
        print("   期望的 YOLO 格式：")
        print("   dataset/")
        print("   ├── images/")
        print("   │   ├── train/  (必需)")
        print("   │   ├── val/    (建议)")
        print("   │   └── test/   (可选)")
        print("   └── labels/")
        print("       ├── train/  (必需)")
        print("       └── val/    (建议)")
        sys.exit(1)

    # Step 4: 生成 data.yaml
    print("\n[4/4] 生成 data.yaml...")
    if class_names is None:
        class_names = infer_class_names(dataset_root)

    yaml_path = generate_data_yaml(dataset_root, class_names)

    print()
    print("=" * 60)
    print("✅ 数据准备完成！")
    print("=" * 60)
    print(f"   数据集路径: {dataset_root}")
    print(f"   配置文件: {yaml_path}")
    print(f"   训练集图片: {validation['train']['images']}")
    print(f"   验证集图片: {validation['val']['images']}")
    print()
    print("下一步运行训练:")
    print(f"   python train_yolo.py --data {yaml_path}")
    print("=" * 60)

    return dataset_root


def run_validate_only(dataset_dir: Path) -> None:
    """仅验证已有数据集（不解压）。"""
    print("=" * 60)
    print("🔍 数据集验证模式")
    print("=" * 60)

    dataset_root = detect_nested_root(dataset_dir)
    validation = validate_directory_structure(dataset_root)
    print_validation_report(validation)

    # 尝试读取 data.yaml
    yaml_path = dataset_root / "data.yaml"
    if yaml_path.exists():
        print(f"\n📄 已有 data.yaml: {yaml_path}")
        class_names = infer_class_names(dataset_root)
        nc = len(class_names)
        print(f"   类别数: {nc}")
        print(f"   类别: {class_names[:5]}{'...' if nc > 5 else ''}")
    else:
        print(f"\n⚠️ 未找到 data.yaml，训练前需先生成")


# ==================================================================
# CLI
# ==================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NutriMind-Agent AutoDL 数据准备工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 HuggingFace 镜像下载数据集
  python prepare_data.py --hf issai/Food_Portion_Benchmark

  # 从 HuggingFace 官方源下载
  python prepare_data.py --hf issai/Food_Portion_Benchmark --no-mirror

  # 完整流程：解压 + 验证 + 生成 data.yaml
  python prepare_data.py --zip /root/autodl-tmp/food_dataset.zip

  # 指定输出目录
  python prepare_data.py --zip /root/autodl-tmp/food_dataset.zip --output /root/autodl-tmp/my_food_data

  # 仅验证已有数据集
  python prepare_data.py --validate-only --dataset /root/autodl-tmp/Food_Portion_Benchmark

  # 自动检测 /root/autodl-tmp 下的 zip 文件
  python prepare_data.py --auto
        """,
    )

    parser.add_argument(
        "--hf", type=str, default=None,
        help="从 HuggingFace 下载数据集（提供数据集 ID，如 issai/Food_Portion_Benchmark）"
    )
    parser.add_argument(
        "--no-mirror", action="store_true",
        help="不使用国内 HuggingFace 镜像（默认使用 hf-mirror.com）"
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="解压输出目录（默认: /root/autodl-tmp/<zip_name>）"
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="仅验证已有数据集结构，不解压"
    )
    parser.add_argument(
        "--dataset", type=Path, default=None,
        help="已有数据集目录路径（与 --validate-only 配合使用）"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="自动检测 /root/autodl-tmp 下的 zip 文件并处理第一个"
    )
    parser.add_argument(
        "--class-names", type=str, default=None,
        help="逗号分隔的类别名列表（不传则自动推断）"
    )

    args = parser.parse_args()

    # 模式：从 HuggingFace 下载
    if args.hf:
        output_dir = args.output or (AUTODL_TMP / args.hf.split("/")[-1])
        use_mirror = not args.no_mirror

        print("=" * 60)
        print("🚀 NutriMind-Agent HuggingFace 数据下载")
        print("=" * 60)
        print(f"   数据集: {args.hf}")
        print(f"   输出目录: {output_dir}")
        print(f"   国内镜像: {'是 (hf-mirror.com)' if use_mirror else '否'}")
        print()

        # 优先使用 Python API（更可靠），失败则回退到 CLI
        success = download_from_huggingface_python(args.hf, output_dir, mirror=use_mirror)
        if not success:
            print("\n🔄 Python API 下载失败，尝试 huggingface-cli ...")
            success = download_from_huggingface(args.hf, output_dir, mirror=use_mirror)

        if not success:
            print("\n❌ HuggingFace 下载失败。请尝试手动命令:")
            if use_mirror:
                print("   export HF_ENDPOINT=https://hf-mirror.com")
            print(f"   huggingface-cli download {args.hf} --local-dir {output_dir} --local-dir-use-symlinks False --repo-type dataset --resume-download")
            sys.exit(1)

        # 下载完成后验证目录结构
        print("\n[验证] 检查下载的数据集...")
        dataset_root = detect_nested_root(output_dir)
        validation = validate_directory_structure(dataset_root)
        print_validation_report(validation)

        # 列出完整文件结构
        print(f"\n📂 数据集文件结构:")
        _print_dir_tree(output_dir, max_depth=3)

        return

    # 模式：仅验证
    if args.validate_only:
        dataset_dir = args.dataset or AUTODL_TMP
        run_validate_only(dataset_dir)
        return

    # 模式：自动检测 zip
    if args.auto:
        zips = find_zip_files(AUTODL_TMP)
        if not zips:
            print(f"❌ 在 {AUTODL_TMP} 下未找到 zip 文件")
            sys.exit(1)
        args.zip = zips[0]
        print(f"🔍 自动检测到压缩包: {args.zip}")

    # 模式：手动指定 zip
    if args.zip is None:
        parser.print_help()
        print("\n❌ 请指定 --zip 或使用 --auto / --validate-only")
        sys.exit(1)

    # 解析类别名
    class_names = None
    if args.class_names:
        class_names = [n.strip() for n in args.class_names.split(",")]

    # 执行完整流程
    run_prepare(args.zip, args.output, class_names)


if __name__ == "__main__":
    main()
