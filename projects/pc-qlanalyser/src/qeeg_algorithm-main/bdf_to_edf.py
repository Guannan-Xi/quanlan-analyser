"""
将 BDF 文件转换为 EDF 文件的测试脚本。
依赖: mne (read_raw_bdf, export.export_raw)
"""

import argparse
from pathlib import Path

import mne


def bdf_to_edf(
    bdf_path,
    edf_path=None,
    preload=True,
    overwrite=True,
    verbose=True,
):
    """
    将 BDF 转为 EDF。

    Parameters
    ----------
    bdf_path : str | Path
        输入的 BDF 文件路径
    edf_path : str | Path | None
        输出的 EDF 文件路径；None 时与 BDF 同目录、同名改为 .edf
    preload : bool
        是否预加载数据到内存，默认 True
    overwrite : bool
        是否覆盖已存在的 EDF 文件，默认 True
    verbose : bool
        是否打印信息

    Returns
    -------
    Path
        输出 EDF 的路径
    """
    bdf_path = Path(bdf_path)
    if not bdf_path.exists():
        raise FileNotFoundError(f"BDF 文件不存在: {bdf_path}")

    if bdf_path.suffix.lower() != ".bdf":
        raise ValueError(f"期望 .bdf 文件，当前: {bdf_path.suffix}")

    if edf_path is None:
        edf_path = bdf_path.with_suffix(".edf")
    else:
        edf_path = Path(edf_path)

    if edf_path.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在且未设置 overwrite: {edf_path}")

    if verbose:
        print(f"读取 BDF: {bdf_path}")

    raw = mne.io.read_raw_bdf(bdf_path, preload=preload, verbose="WARNING")

    if verbose:
        print(f"  通道数: {len(raw.ch_names)}")
        print(f"  采样率: {raw.info['sfreq']} Hz")
        print(f"  时长: {raw.times[-1]:.2f} s")
        print(f"写出 EDF: {edf_path}")

    mne.export.export_raw(
        str(edf_path),
        raw,
        fmt="edf",
        overwrite=overwrite,
        physical_range="channelwise",
    )

    if verbose:
        print("  完成。")

    return edf_path


def main():
    parser = argparse.ArgumentParser(description="BDF 转 EDF")
    parser.add_argument(
        "bdf_file",
        nargs="?",
        default="20260204173709_1_20Hz.bdf",
        help="BDF 文件路径（默认: 20260204173030_1_12Hz.bdf）",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出 EDF 路径（默认: 与 BDF 同目录、同名 .edf）",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="不覆盖已存在的 EDF",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="少输出信息",
    )
    args = parser.parse_args()

    root = Path(__file__).parent
    bdf_path = Path(args.bdf_file)
    if not bdf_path.is_absolute():
        bdf_path = root / bdf_path

    bdf_to_edf(
        bdf_path,
        edf_path=Path(args.output) if args.output else None,
        overwrite=not args.no_overwrite,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
