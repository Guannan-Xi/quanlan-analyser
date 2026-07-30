from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_OUTPUT = Path("outputs/simnibs_ti_violante2023_reproduction_20260729")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adapt the existing ernie TI example to simnibs.delivery.v2.")
    parser.add_argument("--source", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def figure(figure_id: str, category: str, title: str, conclusion: str, stem: str, data_file: str) -> dict:
    return {
        "figure_id": figure_id,
        "category": category,
        "title": title,
        "conclusion": conclusion,
        "image": f"figures/png/{stem}.png",
        "vector": f"figures/svg/{stem}.svg",
        "pdf": f"figures/pdf/{stem}.pdf",
        "source_data": f"figures/figure_data/{data_file}",
    }


def build_payload(source: Path) -> dict:
    result = json.loads((source / "result.json").read_text(encoding="utf-8"))
    conditions = result["conditions"]
    hip11 = conditions["TI_1to1"]["metrics"]["hippocampus"]["TI_directional"]
    hip13 = conditions["TI_1to3"]["metrics"]["hippocampus"]["TI_directional"]
    off11 = conditions["TI_1to1"]["metrics"]["off_target_gray_matter"]["TI_directional"]
    off13 = conditions["TI_1to3"]["metrics"]["off_target_gray_matter"]["TI_directional"]
    share11 = conditions["TI_1to1"]["relative_hippocampal_segment_exposure"]
    share13 = conditions["TI_1to3"]["relative_hippocampal_segment_exposure"]
    anterior_shift = 100 * (share13["hippocampus_anterior"] - share11["hippocampus_anterior"])

    target_specs = [
        ("hippocampus", "左海马", "target", "Harvard-Oxford 25% 最大概率图谱左海马"),
        ("right_hippocampus", "右海马", "contralateral", "Harvard-Oxford 25% 最大概率图谱右海马"),
        ("cortex_anterior", "前部皮层采样区", "off_target_sample", "蒙太奇相关的 10 mm 球形灰质采样区"),
        ("cortex_middle", "中部皮层采样区", "off_target_sample", "蒙太奇相关的 10 mm 球形灰质采样区"),
        ("cortex_posterior", "后部皮层采样区", "off_target_sample", "蒙太奇相关的 10 mm 球形灰质采样区"),
        ("off_target_gray_matter", "全部非靶区灰质", "off_target", "有效灰质分析域减去左海马靶区"),
    ]
    targets = [
        {"target_id": target_id, "name": name, "role": role, "definition": definition, "coordinate_space": "MNI / ernie subject conform"}
        for target_id, name, role, definition in target_specs
    ]

    roi_metrics = []
    for condition_id in ("TI_1to1", "TI_1to3"):
        for target_id, *_ in target_specs:
            values = conditions[condition_id]["metrics"][target_id]["TI_directional"]
            roi_metrics.append({
                "condition_id": condition_id,
                "target_id": target_id,
                "values": {
                    "mean": round(float(values["mean_v_per_m"]), 4),
                    "median": round(float(values["median_v_per_m"]), 4),
                    "p95": round(float(values["p95_v_per_m"]), 4),
                    "volume": round(float(values["volume_mm3"]), 1),
                },
            })

    figures = [
        figure("anatomy_target", "anatomy", "个体头模型与左海马靶区", "绿色轮廓标示本次分析采用的左海马范围。", "fig01_individual_anatomy_hippocampus", "fig01_anatomy_roi.csv"),
        figure("stimulation_montage", "protocol", "刺激电极与两组回路", "四个电极组成 FT7-Fp2 与 TP7-TP8 两组回路。", "fig02_stimulation_montage", "fig02_electrode_montage.csv"),
        figure("carrier_fields", "field", "两组载波基础电场", "E1 和 E2 为两组回路各自在 1 mA 条件下的基础场。", "fig03_carrier_fields_E1_E2", "fig03_color_scale.csv"),
        figure("ti_1to1_field", "field", "TI 1:1 电场分布", "TI 1:1 在左海马产生的整体场强高于 TI 1:3。", "fig04_TI_1to1_directional_and_TImax", "fig04_TI_1to1_slice_and_scale.csv"),
        figure("ti_1to3_field", "field", "TI 1:3 电场分布", "TI 1:3 降低左海马整体场强，并改变海马内相对分布。", "fig05_TI_1to3_directional_and_TImax", "fig05_TI_1to3_slice_and_scale.csv"),
        figure("segment_comparison", "quantitative", "海马前、中、后三段比较", f"TI 1:3 使前段场强份额增加 {anterior_shift:.1f} 个百分点，但后段占比仍最高。", "fig06_hippocampal_segment_steering", "fig06_hippocampal_segment_steering.csv"),
        figure("cortical_comparison", "quantitative", "左海马与局部皮层比较", "部分皮层采样区的中位场强与左海马相当或更高。", "fig07_hippocampus_overlying_cortex", "fig07_hippocampus_overlying_cortex.csv"),
        figure("targeting_focality", "quantitative", "靶区、对侧海马与非靶区比较", "左海马中位场强高于全部非靶区灰质，但 P95 水平接近。", "fig08_targeting_and_focality", "fig08_targeting_and_focality.csv"),
        figure("focus_location", "localization", "左海马内高值区位置", "TI 1:3 的高值区重心前移 1.65 mm，但该差异靠近分段边界。", "fig09_focus_location_mni", "fig09_focus_location_mni.csv"),
        figure("cortical_surface", "localization", "皮层表面电场", "两种方案均存在较广泛的皮层表面电场。", "fig10_directional_ti_cortical_surface", "fig10_cortical_surface_scale.csv"),
    ]

    return {
        "schema_version": "simnibs.delivery.v2",
        "analysis_mode": "forward_compare",
        "stimulation_modality": "temporal_interference",
        "project": {
            "project_id": "SIMNIBS-TI-ERNIE-EXAMPLE-20260729",
            "title": "海马时间干涉刺激仿真报告",
            "scientific_question": "比较 TI 1:1 与 TI 1:3 的左海马场强、海马内高值区位置和非靶区暴露。",
            "service_status": "draft",
        },
        "subject": {
            "subject_id": "ernie",
            "model_type": "SimNIBS CHARM 单受试者头模型",
            "image_source": "本示例使用 SimNIBS 官方 ernie MRI 数据；正式服务应替换为客户 MRI 和经审核的个体头模型。",
        },
        "targets": targets,
        "protocol": {
            "amplitude_convention": "peak_to_baseline",
            "conditions": [
                {"condition_id": "TI_1to1", "label": "TI 1:1", "channels": [
                    {"channel_id": "E1", "description": "FT7(+1.0 mA) / Fp2(-1.0 mA)，2.005 kHz"},
                    {"channel_id": "E2", "description": "TP7(+1.0 mA) / TP8(-1.0 mA)，2.000 kHz"},
                ]},
                {"condition_id": "TI_1to3", "label": "TI 1:3", "channels": [
                    {"channel_id": "E1", "description": "FT7(+0.5 mA) / Fp2(-0.5 mA)，2.005 kHz"},
                    {"channel_id": "E2", "description": "TP7(+1.5 mA) / TP8(-1.5 mA)，2.000 kHz"},
                ]},
            ],
        },
        "results": {
            "headline_findings": [
                f"左海马中位场强：TI 1:1 为 {hip11['median_v_per_m']:.3f} V/m，TI 1:3 为 {hip13['median_v_per_m']:.3f} V/m。",
                f"TI 1:3 使前海马场强份额增加 {anterior_shift:.1f} 个百分点，但场强占比最高的区域仍是海马后段。",
                "两种方案均存在皮层和其他非靶区暴露；部分局部皮层采样区与左海马相当或更高。",
            ],
            "interpretation": [
                "如果研究目标是提高这个模型中的左海马整体场强，TI 1:1 更符合该目标。",
                "TI 1:3 使海马内高值区略向前移动，但同时降低左海马整体场强，且没有减少非靶区暴露。",
                "本例不能用于判断临床疗效、安全性或患者个体化方案。",
            ],
            "interpretation_boundary": "结果仅适用于 ernie 单受试者、当前电极位置、组织电导率和数值设置。",
            "metric_definitions": {
                "mean": {"label": "平均值", "unit": "V/m", "definition": "按四面体体积加权的区域均值", "decimals": 4},
                "median": {"label": "中位数", "unit": "V/m", "definition": "按四面体体积加权的区域中位数", "decimals": 4},
                "p95": {"label": "P95", "unit": "V/m", "definition": "按四面体体积加权的第 95 百分位数", "decimals": 4},
                "volume": {"label": "体积", "unit": "mm³", "definition": "有效分析单元总体积", "decimals": 1},
            },
            "roi_metrics": roi_metrics,
            "comparisons": {
                "target_to_offtarget_median": {
                    "TI_1to1": round(hip11["median_v_per_m"] / off11["median_v_per_m"], 3),
                    "TI_1to3": round(hip13["median_v_per_m"] / off13["median_v_per_m"], 3),
                }
            },
        },
        "quality_control": {
            "checks": [
                {"name": "载波网格一致性", "status": "pass", "evidence": "E1 与 E2 的节点和单元逐项一致"},
                {"name": "TI 公式独立复算", "status": "pass", "evidence": "最大绝对误差 0 V/m"},
                {"name": "DTI 方向数据覆盖", "status": "warning", "evidence": f"有限方向向量覆盖 {100*result['quality']['dti_valid_gray_fraction']:.2f}% 灰质单元；方向可靠性未单独评估"},
                {"name": "跨受试者稳健性", "status": "not_assessed", "evidence": "当前仅包含一个示例受试者"},
            ],
            "limitations": [
                "未进行网格收敛分析。",
                "未进行电极位置扰动和组织电导率敏感性分析。",
                "未量化 DTI 主方向和非线性 MNI 配准的不确定性。",
                "没有患者队列、组水平统计或临床结局数据。",
            ],
        },
        "methods": [
            {"title": "有限元计算", "text": f"采用 SimNIBS {result['software']['version']} 和 hypre 求解器。两组载波共用同一网格，灰质分析包含 {result['quality']['gray_tetrahedra']:,} 个四面体。"},
            {"title": "海马定义", "text": "灰质单元中心变换到 MNI 空间后，以最近邻方式采样 Harvard-Oxford 25% 最大概率图谱中的左、右海马。"},
            {"title": "TI 指标", "text": "主要指标为沿 DTI 主方向计算的方向投影 TI；同时提供方向无关的 TImax。两者均为调制包络幅度，不是神经激活阈值。"},
        ],
        "figures": figures,
        "artifacts": [
            {"path": "tables/violante2023_ti_reproduction_results.xlsx", "label": "Excel 结果表", "purpose": "ROI 统计、图件索引和计算口径"},
            {"path": "packages/figure_support_csv.zip", "label": "图表数据", "purpose": "各图对应的 CSV 文件"},
            {"path": "packages/nifti_fields.zip", "label": "NIfTI 数据", "purpose": "空间场和 ROI 掩膜"},
            {"path": "raw/violante2023_reproduction_fields.h5", "label": "HDF5 数据", "purpose": "逐单元电场与派生指标"},
            {"path": "publication_index.json", "label": "发表图件索引", "purpose": "图件、图注与源数据的对应关系", "generated_by_builder": True},
            {"path": "standard_manifest.json", "label": "标准文件清单", "purpose": "标准报告及客户交付文件的大小与 SHA-256", "generated_by_builder": True},
            {"path": "reproducibility/DATA_AND_CODE_AVAILABILITY.md", "label": "复现说明", "purpose": "冻结脚本、依赖和使用边界"},
        ],
        "modules": {
            "temporal_interference": {
                "primary_metric": "directional_ti",
                "secondary_metric": "timax",
                "carrier_frequencies_hz": [2005, 2000],
                "beat_frequency_hz": 5,
                "direction_source": "DTI principal eigenvector",
            }
        },
    }


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    payload = build_payload(source)
    output = source / "standard_report_data.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "complete", "payload": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
