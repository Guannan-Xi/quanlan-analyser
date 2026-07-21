"""Z-Score计算测试脚本"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qeeg import QEEGAnalyzer, PreprocessingParams, ZScoreCalculator

CHANNELS_21 = [
    'Fp1', 'Fp2', 'C3', 'C4', 'O1', 'O2', 'Cz', 'T3', 'T4',
    'F3', 'F4', 'Fz', 'F7', 'F8', 'Pz', 'P3',
    'T5', 'P4', 'T6', 'Fpz', 'Oz'
]


def main():
    test_file = "S001R01_cleaned.edf"
    norms_dir = "EEGnorms"
    
    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return
    
    if not os.path.exists(norms_dir):
        print(f"规范数据目录不存在: {norms_dir}")
        return
    
    print("=" * 60)
    print("QEEG Z-Score计算测试")
    print("=" * 60)
    
    print("\n【1. 执行基础QEEG分析】")
    
    params = PreprocessingParams()
    params.lowcut = 0.5
    params.highcut = 45.0
    params.notch_freq = 50.0
    params.artifact_rejection = True
    params.amplitude_threshold = 100.0
    params.baseline_correction = True
    
    analyzer = QEEGAnalyzer(preprocessing_params=params, verbose=False)
    
    result = analyzer.analyze(
        test_file,
        time_window=(0, 60),
        select_channels=CHANNELS_21,
    )
    
    if not result.success:
        print(f"QEEG分析失败: {result.error_message}")
        return
    
    print(f"  分析完成，通道数: {result.n_channels}")
    
    print("\n【2. 计算Z-Score】")
    
    test_age = 25
    test_state = 'eyes_closed'
    
    print(f"  年龄: {test_age}岁")
    print(f"  状态: {test_state}")
    
    try:
        zscore_calc = ZScoreCalculator(norms_dir=norms_dir)
        
        zscore_result = zscore_calc.calculate(
            psd_result=result.psd,
            age=test_age,
            state=test_state,
            calculate_broadband=True,
            calculate_narrowband=True,
        )
        
        print("\n【3. Z-Score结果摘要】")
        print(f"  显著偏离数量 (|Z|>=1.96): {zscore_result.n_significant_deviations}")
        print(f"  显著偏离通道: {zscore_result.significant_channels}")
        
        def mark(z):
            if z is None:
                return "    N/A   "
            if abs(z) >= 2.58:
                return f"{z:>7.2f}**"
            elif abs(z) >= 1.96:
                return f"{z:>7.2f}* "
            else:
                return f"{z:>7.2f}  "
        
        if zscore_result.broadband:
            print("\n【4. 宽带模型Z-Score (绝对功率) - 按电极】")
            print(f"  {'通道':<8} {'delta':<10} {'theta':<10} {'alpha':<10} {'beta':<10}")
            print("  " + "-" * 48)
            
            for ch in zscore_result.broadband.channel_names[:10]:
                z_vals = zscore_result.broadband.z_absolute_power.get(ch, {})
                d = z_vals.get('delta', 0)
                t = z_vals.get('theta', 0)
                a = z_vals.get('alpha', 0)
                b = z_vals.get('beta', 0)
                print(f"  {ch:<8} {mark(d)} {mark(t)} {mark(a)} {mark(b)}")
            
            print("\n  (* p<0.05, ** p<0.01)")
            
            print("\n【5. 脑区(Brodmann Area) Z-Score】")
            print(f"  {'脑区':<15} {'delta':<10} {'theta':<10} {'alpha':<10} {'beta':<10}")
            print("  " + "-" * 55)
            
            for ba_name, z_vals in zscore_result.broadband.z_by_brodmann_area.items():
                d = z_vals.get('delta')
                t = z_vals.get('theta')
                a = z_vals.get('alpha')
                b = z_vals.get('beta')
                print(f"  {ba_name:<15} {mark(d)} {mark(t)} {mark(a)} {mark(b)}")
            
            print("\n【6. 大脑区域汇总 Z-Score】")
            print(f"  {'区域':<12} {'delta':<10} {'theta':<10} {'alpha':<10} {'beta':<10}")
            print("  " + "-" * 52)
            
            for region, z_vals in zscore_result.broadband.z_by_region.items():
                d = z_vals.get('delta')
                t = z_vals.get('theta')
                a = z_vals.get('alpha')
                b = z_vals.get('beta')
                print(f"  {region:<12} {mark(d)} {mark(t)} {mark(a)} {mark(b)}")
        
        if zscore_result.narrowband and zscore_result.narrowband.z_matrix is not None:
            print("\n【7. 窄带模型Z-Score统计】")
            z_matrix = zscore_result.narrowband.z_matrix
            print(f"  频率范围: {zscore_result.narrowband.frequencies[0]:.2f} - {zscore_result.narrowband.frequencies[-1]:.2f} Hz")
            print(f"  频点数: {len(zscore_result.narrowband.frequencies)}")
            print(f"  匹配通道数: {len(zscore_result.narrowband.channel_names)}")
            print(f"  使用的对数偏移校正: {zscore_result.narrowband.log_offset_used:.2f}")
            
            total_values = z_matrix.size
            if total_values > 0:
                normal = np.sum(np.abs(z_matrix) < 1.96)
                mild = np.sum((np.abs(z_matrix) >= 1.96) & (np.abs(z_matrix) < 2.58))
                severe = np.sum(np.abs(z_matrix) >= 2.58)
                
                print(f"\n  Z值分布:")
                print(f"    正常 (|Z|<1.96):    {normal} ({100*normal/total_values:.1f}%)")
                print(f"    显著 (1.96<=|Z|<2.58): {mild} ({100*mild/total_values:.1f}%)")
                print(f"    高度显著 (|Z|>=2.58): {severe} ({100*severe/total_values:.1f}%)")
        
        output_dir = "qeeg_output"
        os.makedirs(output_dir, exist_ok=True)
        
        zscore_output = os.path.join(output_dir, "7_zscore_result.json")
        with open(zscore_output, 'w', encoding='utf-8') as f:
            json.dump(zscore_result.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {zscore_output}")
        
    except Exception as e:
        print(f"\nZ-Score计算失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    import numpy as np
    main()
