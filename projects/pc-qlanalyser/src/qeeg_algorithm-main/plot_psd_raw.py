"""
绘制 4_psd_raw_data.json 中各通道的 PSD 图
"""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_psd_raw(json_path):
    """加载 PSD 原始数据 JSON。"""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["frequencies"], data["psd_data"], data["channel_names"]


def plot_psd_matrix(
    json_path,
    freq_lim=(0, 45),
    log_y=True,
    figsize=None,
    dpi=100,
    out_path=None,
):
    
    frequencies, psd_data, channel_names = load_psd_raw(json_path)
    frequencies = np.array(frequencies)
    psd_data = np.array(psd_data)

    n_channels = len(channel_names)
    n_freqs = len(frequencies)

    # 子图网格：尽量接近正方形
    n_cols = math.ceil(math.sqrt(n_channels))
    n_rows = math.ceil(n_channels / n_cols)

    if figsize is None:
        figsize = (4 * n_cols, 2.5 * n_rows)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, sharex=True, sharey=True)
    if n_channels == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    axes_flat = axes.ravel()

    # 频率范围掩码
    mask = (frequencies >= freq_lim[0]) & (frequencies <= freq_lim[1])
    freqs_plot = frequencies[mask]

    for i in range(n_channels):
        ax = axes_flat[i]
        psd_row = np.array(psd_data[i])
        psd_plot = psd_row[mask]
        # 避免 log(0)
        psd_plot = np.maximum(psd_plot, 1e-20)

        if log_y:
            ax.semilogy(freqs_plot, psd_plot, color="steelblue", linewidth=0.8)
        else:
            ax.plot(freqs_plot, psd_plot, color="steelblue", linewidth=0.8)

        ax.set_title(channel_names[i], fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(freq_lim)

    # 隐藏多余子图
    for j in range(n_channels, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("PSD by channel (Power Spectral Density)", fontsize=12, y=1.02)
    fig.supxlabel("Frequency (Hz)", fontsize=10)
    fig.supylabel("Power (μV²/Hz)" + (" [log]" if log_y else ""), fontsize=10)
    plt.tight_layout()

    if out_path is not None:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=dpi, bbox_inches="tight")
        print(f"已保存: {out_path}")

    plt.show()
    return fig, axes


def main():
    json_path = Path(__file__).parent / "qeeg_output" / "4_psd_raw_data.json"
    out_path = Path(__file__).parent / "qeeg_output" / "psd_matrix_plot.png"

    plot_psd_matrix(
        json_path,
        freq_lim=(0, 45),
        log_y=True,
        out_path=out_path,
        dpi=120,
    )


if __name__ == "__main__":
    main()
