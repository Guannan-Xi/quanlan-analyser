"""QEEG主分析器"""

import json
from pathlib import Path

from .models import (
    PreprocessingParams,
    TimeWindow,
    QEEGAnalysisResult,
)
from .edf_reader import read_edf, find_available_channels
from .preprocessing import preprocess
from .analyzers import (
    analyze_paf,
    analyze_tbr,
    analyze_psd,
    analyze_band_mapping,
    analyze_ratio_mapping,
    analyze_faa,
    analyze_alpha_ratio,
)


class QEEGAnalyzer:
    """QEEG量化分析器"""
    
    def __init__(self, preprocessing_params=None, verbose=False):
        self.preprocessing_params = preprocessing_params or PreprocessingParams()
        self.verbose = verbose
        self._edf_data = None
        self._preprocessed = None
    
    def analyze(self, file_path, time_window=None, preprocessing_params=None,
                analyses=None, select_channels=None):
        """执行完整的QEEG分析"""
        params = preprocessing_params or self.preprocessing_params
        
        if analyses is None:
            analyses = ['paf', 'tbr', 'psd', 'band_mapping', 'ratio_mapping', 'faa', 'alpha_ratio']
        
        try:
            if self.verbose:
                print(f"\n{'='*50}")
                print(f"QEEG分析开始: {file_path}")
                print(f"{'='*50}")
            
            edf_data = read_edf(file_path, verbose=self.verbose, select_channels=select_channels)
            self._edf_data = edf_data
            
            if self.verbose:
                available = find_available_channels(edf_data)
                print(f"\n找到 {len(available)}/21 个标准通道")
            
            if time_window is not None:
                start, end = time_window
                start = max(0, start)
                end = min(edf_data.duration, end)
                edf_data = edf_data.get_time_segment(start, end)
                tw = TimeWindow(start=start, end=end)
            else:
                tw = TimeWindow(start=0, end=edf_data.duration)
            
            if self.verbose:
                print(f"\n分析时间窗口: {tw.start:.2f}s - {tw.end:.2f}s (时长: {tw.duration:.2f}s)")
            
            if self.verbose:
                print(f"\n--- 预处理 ---")
            
            preprocessed = preprocess(edf_data, params, verbose=self.verbose)
            self._preprocessed = preprocessed
            
            paf_result = None
            tbr_result = None
            psd_result = None
            band_mapping_result = None
            ratio_mapping_result = None
            faa_result = None
            alpha_ratio_result = None

            data = preprocessed.data
            ch_names = preprocessed.channel_names
            sfreq = preprocessed.sampling_frequency
            
            if 'paf' in analyses:
                if self.verbose:
                    print(f"\n--- PAF分析 ---")
                paf_result = analyze_paf(data, ch_names, sfreq)
                if self.verbose and paf_result:
                    print(f"  O1峰值: {paf_result.o1_peak:.2f} Hz")
                    print(f"  O2峰值: {paf_result.o2_peak:.2f} Hz")
                    print(f"  平均峰值: {paf_result.mean_peak:.2f} Hz")
            
            if 'tbr' in analyses:
                if self.verbose:
                    print(f"\n--- TBR分析 ---")
                tbr_result = analyze_tbr(data, ch_names, sfreq)
                if self.verbose and tbr_result:
                    print(f"  Fz比率: {tbr_result.fz_ratio:.3f}")
                    print(f"  Cz比率: {tbr_result.cz_ratio:.3f}")
                    print(f"  平均比率: {tbr_result.mean_ratio:.3f}")
            
            if 'psd' in analyses:
                if self.verbose:
                    print(f"\n--- PSD分析 ---")
                psd_result = analyze_psd(data, ch_names, sfreq)
                if self.verbose:
                    print(f"  频谱数据形状: {psd_result.psd_array.shape}")
                    print(f"  频率范围: {psd_result.freqs[0]:.2f} - {psd_result.freqs[-1]:.2f} Hz")
            
            if 'band_mapping' in analyses:
                if self.verbose:
                    print(f"\n--- 全频段地形图矩阵 ---")
                band_mapping_result = analyze_band_mapping(data, ch_names, sfreq)
                if self.verbose:
                    print(f"  窄带数量: {len(band_mapping_result.band_edges)}")
                    print(f"  绝对功率矩阵形状: {band_mapping_result.absolute_power.shape}")
            
            if 'ratio_mapping' in analyses:
                if self.verbose:
                    print(f"\n--- 功率比率地形图 ---")
                ratio_mapping_result = analyze_ratio_mapping(data, ch_names, sfreq)
                if self.verbose:
                    print(f"  计算了12种比率组合")
            
            if 'faa' in analyses:
                if self.verbose:
                    print(f"\n--- FAA分析 (前额Alpha非对称性) ---")
                faa_result = analyze_faa(data, ch_names, sfreq)
                if self.verbose and faa_result:
                    print(f"  FAA百分比: {faa_result.faa_percentage:.2f}%")
                    print(f"  F3 Alpha功率: {faa_result.alpha_f3:.4f} μV²")
                    print(f"  F4 Alpha功率: {faa_result.alpha_f4:.4f} μV²")

            if 'alpha_ratio' in analyses:
                if self.verbose:
                    print(f"\n--- Alpha Ratio 分析 (闭眼/睁眼 Alpha 比例) ---")
                # 暂无独立闭眼/睁眼数据时，闭眼与睁眼均使用同一段数据
                alpha_ratio_result = analyze_alpha_ratio(data, data, ch_names, sfreq)
                if self.verbose and alpha_ratio_result:
                    print(f"  Alpha 比例 (抑制指数): {alpha_ratio_result.ratio:.4f}")
                    print(f"  闭眼枕区 Alpha 功率 (O1,O2 均值): {alpha_ratio_result.alpha_power_closed:.4f} μV²")
                    print(f"  睁眼枕区 Alpha 功率 (O1,O2 均值): {alpha_ratio_result.alpha_power_open:.4f} μV²")

            if self.verbose:
                print(f"\n{'='*50}")
                print("QEEG分析完成")
                print(f"{'='*50}\n")
            
            return QEEGAnalysisResult(
                file_path=file_path,
                analysis_time_window=tw,
                preprocessing_params=params,
                sampling_frequency=sfreq,
                n_channels=len(ch_names),
                channel_names=ch_names,
                paf=paf_result,
                tbr=tbr_result,
                psd=psd_result,
                band_mapping=band_mapping_result,
                ratio_mapping=ratio_mapping_result,
                faa=faa_result,
                alpha_ratio=alpha_ratio_result,
                success=True,
                error_message=None,
            )
            
        except Exception as e:
            if self.verbose:
                print(f"\n分析失败: {str(e)}")
            
            return QEEGAnalysisResult(
                file_path=file_path,
                analysis_time_window=TimeWindow(start=0, end=0),
                preprocessing_params=params,
                sampling_frequency=0,
                n_channels=0,
                channel_names=[],
                success=False,
                error_message=str(e),
            )
    
    def analyze_paf_only(self, file_path, time_window=None):
        """只执行PAF分析"""
        result = self.analyze(file_path, time_window, analyses=['paf'])
        return result.paf
    
    def analyze_tbr_only(self, file_path, time_window=None):
        """只执行TBR分析"""
        result = self.analyze(file_path, time_window, analyses=['tbr'])
        return result.tbr
    
    def analyze_psd_only(self, file_path, time_window=None):
        """只执行PSD分析"""
        result = self.analyze(file_path, time_window, analyses=['psd'])
        return result.psd
    
    def analyze_faa_only(self, file_path, time_window=None):
        """只执行FAA分析"""
        result = self.analyze(file_path, time_window, analyses=['faa'])
        return result.faa

    def analyze_alpha_ratio_only(self, file_path, time_window=None):
        """只执行闭眼/睁眼 Alpha 比例分析。暂无独立闭眼/睁眼数据时，闭眼与睁眼均使用同一段数据"""
        result = self.analyze(file_path, time_window, analyses=['alpha_ratio'])
        return result.alpha_ratio

    def to_json(self, result, indent=2):
        """将分析结果转换为JSON字符串"""
        return json.dumps(result.to_dict(), indent=indent, ensure_ascii=False)
    
    def save_results(self, result, output_dir, split_files=True):
        """保存分析结果到JSON文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not split_files:
            file_path = output_path / "qeeg_result.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            if self.verbose:
                print(f"结果已保存到: {file_path}")
            return
        
        saved_files = []
        
        metadata = {
            "file_path": result.file_path,
            "time_window": {
                "start_s": result.analysis_time_window.start,
                "end_s": result.analysis_time_window.end,
                "duration_s": result.analysis_time_window.duration,
            },
            "sampling_frequency_hz": result.sampling_frequency,
            "n_channels": result.n_channels,
            "channel_names": result.channel_names,
            "preprocessing": {
                "lowcut_hz": result.preprocessing_params.lowcut,
                "highcut_hz": result.preprocessing_params.highcut,
                "notch_freq_hz": result.preprocessing_params.notch_freq,
                "artifact_rejection": result.preprocessing_params.artifact_rejection,
                "amplitude_threshold_uv": result.preprocessing_params.amplitude_threshold,
                "baseline_correction": result.preprocessing_params.baseline_correction,
            },
            "status": {
                "success": result.success,
                "error_message": result.error_message,
            }
        }
        self._save_json(output_path / "1_metadata.json", metadata)
        saved_files.append("1_metadata.json")
        
        if result.paf:
            self._save_json(output_path / "2_paf_result.json", result.paf.to_dict())
            saved_files.append("2_paf_result.json")
        
        if result.tbr:
            self._save_json(output_path / "3_tbr_result.json", result.tbr.to_dict())
            saved_files.append("3_tbr_result.json")
        
        if result.psd:
            psd_dict = result.psd.to_dict()
            psd_summary = {
                "channel_names": psd_dict["channel_names"],
                "frequency_range_hz": [float(result.psd.freqs[0]), float(result.psd.freqs[-1])],
                "n_frequencies": len(result.psd.freqs),
                "band_powers_absolute": psd_dict["band_powers_absolute"],
                "band_powers_relative": psd_dict["band_powers_relative"],
            }
            self._save_json(output_path / "4_psd_result.json", psd_summary)
            saved_files.append("4_psd_result.json")
            
            psd_raw = {
                "frequencies": result.psd.freqs.tolist(),
                "psd_absolute": result.psd.psd_array.tolist(),
                "psd_relative": result.psd.psd_relative_array.tolist(),
                "channel_names": result.psd.channel_names,
            }
            self._save_json(output_path / "4_psd_raw_data.json", psd_raw)
            saved_files.append("4_psd_raw_data.json")
        
        if result.band_mapping:
            band_mapping_dict = {
                "band_edges_hz": result.band_mapping.band_edges,
                "channel_names": result.band_mapping.channel_names,
                "absolute_power": result.band_mapping.absolute_power.tolist(),
                "relative_power": result.band_mapping.relative_power.tolist(),
            }
            self._save_json(output_path / "5_band_mapping_result.json", band_mapping_dict)
            saved_files.append("5_band_mapping_result.json")
        
        if result.ratio_mapping:
            self._save_json(output_path / "6_ratio_mapping_result.json", result.ratio_mapping.to_dict())
            saved_files.append("6_ratio_mapping_result.json")
        
        if result.faa:
            self._save_json(output_path / "8_faa_result.json", result.faa.to_dict())
            saved_files.append("8_faa_result.json")

        if result.alpha_ratio:
            self._save_json(output_path / "9_alpha_ratio_result.json", result.alpha_ratio.to_dict())
            saved_files.append("9_alpha_ratio_result.json")

        if hasattr(result, 'zscore') and result.zscore is not None:
            self._save_json(output_path / "7_zscore_result.json", result.zscore.to_dict())
            saved_files.append("7_zscore_result.json")
        
        if self.verbose:
            print(f"\n结果已保存到目录: {output_path}")
            print(f"生成的文件:")
            for f in saved_files:
                print(f"  - {f}")
    
    def _save_json(self, file_path, data):
        """保存单个JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def quick_analyze(file_path, time_window=None, select_channels=None, verbose=True):
    """快速执行完整QEEG分析"""
    analyzer = QEEGAnalyzer(verbose=verbose)
    return analyzer.analyze(file_path, time_window, select_channels=select_channels)
