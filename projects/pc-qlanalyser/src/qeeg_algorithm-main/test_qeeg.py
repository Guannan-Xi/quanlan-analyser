"""QEEG分析测试脚本"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qeeg import QEEGAnalyzer, PreprocessingParams

CHANNELS_21 = [
    'Fp1', 'Fp2', 'C3', 'C4', 'O1', 'O2', 'Cz', 'T3', 'T4',
    'F3', 'F4', 'Fz', 'F7', 'F8', 'Pz', 'P3',
    'T5', 'P4', 'T6', 'Fpz', 'Oz'
]


def main():
    test_file = "S001R01_cleaned.edf"
    
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        print("请确保EDF文件在当前目录下")
        return
    
    print("=" * 60)
    print("QEEG量化分析系统测试")
    print("=" * 60)
    print(f"\n使用文件: {test_file}")
    print(f"提取通道: {len(CHANNELS_21)} 个")
    print(f"通道列表: {CHANNELS_21}")
    
    params = PreprocessingParams()
    params.lowcut = 0.5
    params.highcut = 45.0
    params.notch_freq = 50.0
    params.artifact_rejection = True
    params.amplitude_threshold = 100.0
    params.baseline_correction = True
    
    analyzer = QEEGAnalyzer(preprocessing_params=params, verbose=True)
    
    result = analyzer.analyze(
        test_file,
        time_window=(0, 60),
        select_channels=CHANNELS_21,
    )
    
    if not result.success:
        print(f"\n分析失败: {result.error_message}")
        return
    
    print("\n" + "=" * 60)
    print("分析结果摘要")
    print("=" * 60)
    
    print("\n【1. PAF分析 (Peak Alpha Frequency)】")
    if result.paf:
        print(f"  O1通道Alpha峰值: {result.paf.o1_peak:.2f} Hz")
        print(f"  O2通道Alpha峰值: {result.paf.o2_peak:.2f} Hz")
        print(f"  平均Alpha峰值:   {result.paf.mean_peak:.2f} Hz")
        print(f"  频率分辨率:      {result.paf.frequency_resolution:.3f} Hz")
    else:
        print("  未能计算PAF (可能缺少O1/O2通道)")
    
    print("\n【2. TBR分析 (Theta/Beta Ratio)】")
    if result.tbr:
        print(f"  Fz通道θ/β比率: {result.tbr.fz_ratio:.3f}")
        print(f"  Cz通道θ/β比率: {result.tbr.cz_ratio:.3f}")
        print(f"  平均θ/β比率:   {result.tbr.mean_ratio:.3f}")
        print(f"  (Theta: 4-8Hz, Beta: 13-21Hz)")
    else:
        print("  未能计算TBR (可能缺少Fz/Cz通道)")
    
    print("\n【3. 全脑PSD分析】")
    if result.psd:
        print(f"  通道数: {len(result.psd.channel_names)}")
        print(f"  频率范围: {result.psd.freqs[0]:.2f} - {result.psd.freqs[-1]:.2f} Hz")
        print(f"  频点数: {len(result.psd.freqs)}")
        
        print("\n  各频段功率 (前5通道, 单位: μV²):")
        print(f"  {'通道':<8} {'δ(0.5-4)':<12} {'θ(4-8)':<12} {'α(8-13)':<12} {'β(13-30)':<12}")
        print("  " + "-" * 56)
        for ch in result.psd.channel_names[:5]:
            d = result.psd.delta_power.get(ch, 0)
            t = result.psd.theta_power.get(ch, 0)
            a = result.psd.alpha_power.get(ch, 0)
            b = result.psd.beta_power.get(ch, 0)
            print(f"  {ch:<8} {d:<12.2f} {t:<12.2f} {a:<12.2f} {b:<12.2f}")
    
    print("\n【4. 全频段地形图矩阵 (16窄带)】")
    if result.band_mapping:
        bm = result.band_mapping
        print(f"  窄带数量: {len(bm.band_edges)}")
        print(f"  通道数: {len(bm.channel_names)}")
        print(f"  绝对功率矩阵: {bm.absolute_power.shape}")
        print(f"  相对功率矩阵: {bm.relative_power.shape}")
        print("\n  窄带频率范围:")
        for i, (low, high) in enumerate(bm.band_edges[:8]):
            print(f"    Band {i+1}: {low:.0f}-{high:.0f} Hz")
        print("    ...")
    
    print("\n【5. 功率比率地形图 (12种比率)】")
    if result.ratio_mapping:
        rm = result.ratio_mapping
        print("  12种比率组合的部分通道值:")
        
        ratios = [
            ("θ/α", rm.theta_alpha),
            ("θ/β", rm.theta_beta),
            ("α/β", rm.alpha_beta),
            ("δ/θ", rm.delta_theta),
        ]
        
        for name, ratio_dict in ratios:
            if ratio_dict:
                vals = list(ratio_dict.items())[:3]
                val_str = ", ".join([f"{k}:{v:.3f}" for k, v in vals])
                print(f"    {name}: {val_str}...")
    
    output_dir = "qeeg_output"
    analyzer.save_results(result, output_dir, split_files=True)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
