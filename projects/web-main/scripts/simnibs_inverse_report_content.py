"""Render the customer-facing inverse TI report from verified package data."""

from __future__ import annotations

import html


REFERENCES = [
    {
        "id": "saturnino2019simnibs",
        "title": "SimNIBS 2.1: A Comprehensive Pipeline for Individualized Electric Field Modelling for Transcranial Brain Stimulation",
        "authors": "Saturnino GB, Puonti O, Nielsen JD, et al.",
        "year": 2019,
        "doi": "10.1007/978-3-030-21293-3_1",
        "pmid": "31725247",
        "used_for": "SimNIBS individualized electric-field modeling workflow",
    },
    {
        "id": "grossman2017ti",
        "title": "Noninvasive Deep Brain Stimulation via Temporally Interfering Electric Fields",
        "authors": "Grossman N, Bono D, Dedic N, et al.",
        "year": 2017,
        "doi": "10.1016/j.cell.2017.05.024",
        "pmid": "28575667",
        "used_for": "temporal-interference stimulation concept",
    },
]


def _figure(name: str, alt: str, caption: str) -> str:
    return (
        f'<figure><img src="figures/{name}.png" alt="{html.escape(alt)}">'
        f'<figcaption>{caption}</figcaption></figure>'
    )


def render_customer_report(context: dict) -> str:
    result = context["result"]
    validation = context["validation"]
    winner = result["winner"]
    final = validation["independent_metrics"]
    sensitivity = validation["recompute_half_max_threshold_sensitivity"]
    threshold = validation["comparison_threshold_v_per_m"]
    recompute_threshold = sensitivity["threshold_v_per_m"]
    search_peak = context["search_peak"]
    final_peak = context["final_peak"]
    shared_color_max = context["shared_color_max"]
    artifacts = context["artifacts"]
    cluster = context["cluster"]
    cluster_sensitivity = context["cluster_sensitivity"]
    readiness = context["figure_readiness"]
    search_roi_mean = validation["search_stage_roi_mean_v_per_m"]
    final_roi_mean = validation["independent_rerun_roi_mean_v_per_m"]
    search_off_target_mean = result["metrics"]["off_target"]["mean"]
    final_off_target_mean = final["off_target"]["mean"]
    search_mean_ratio = winner["target_to_off_target_mean_ratio"]
    final_mean_ratio = validation["independent_target_to_off_target_mean_ratio"]
    off_target_delta_pct = 100.0 * (final_off_target_mean - search_off_target_mean) / search_off_target_mean
    mean_ratio_delta_pct = 100.0 * (final_mean_ratio - search_mean_ratio) / search_mean_ratio

    candidate_rows = "".join(
        f"<tr><td>{row['rank']}</td><td>{html.escape(row['candidate_id'])}</td>"
        f"<td>{row['target_mean_v_per_m']:.4f}</td><td>{row['off_target_mean_v_per_m']:.4f}</td>"
        f"<td>{row['target_to_off_target_mean_ratio']:.3f}</td></tr>"
        for row in result["all_candidates"]
    )
    roi_rows = "".join(
        f"<tr><td>{label}</td><td>{values['mean']:.4f}</td><td>{values['median']:.4f}</td>"
        f"<td>{values['p95']:.4f}</td><td>{values['max']:.4f}</td>"
        f"<td>{values['threshold_coverage_pct']:.2f}</td><td>{values['suprathreshold_volume_mm3']:.1f}</td></tr>"
        for label, values in (("目标 ROI", final["target"]), ("靶外灰质", final["off_target"]))
    )
    readiness_rows = "".join(
        f"<tr><td>{html.escape(row['figure_id'])}</td><td>{html.escape(row['scientific_question'])}</td>"
        f"<td><code>{html.escape(row['machine_data'])}</code></td><td>{html.escape(row['status'])}</td>"
        f"<td>{html.escape(row['blocking_reason'])}</td></tr>"
        for row in readiness
    )
    artifact_rows = "".join(
        f"<tr><td><code>{html.escape(item['path'])}</code></td><td>{html.escape(item['type'])}</td>"
        f"<td>{html.escape(item['purpose'])}</td></tr>"
        for item in artifacts
    )
    reference_rows = "".join(
        f"<li>{html.escape(ref['authors'])} ({ref['year']}). {html.escape(ref['title'])}. "
        f"DOI: <code>{ref['doi']}</code>; PMID: <code>{ref['pmid']}</code>.</li>"
        for ref in REFERENCES
    )

    primary_figures = "".join([
        _figure("fig00_model_target_registration", "ernie 个体 T1、组织边界与球形灰质 ROI 的三正交定位",
            "图 1｜头模型与目标区定位。三正交 T1 上叠加组织边界和半径 20 mm 的球形灰质 ROI。坐标为 ernie 个体 conform 物理空间，不是经验证的 MNI 靶点；正式客户研究应替换为客户 MRI、分割结果和经确认的靶点。"),
        _figure("fig00_inverse_electrode_montage", "F5-P5 和 FC3-CP3 四电极方案及电流方向",
            "图 2｜最终四电极方案。F5 +1 mA → P5 -1 mA，FC3 +1 mA → CP3 -1 mA；电流为峰值口径。绿色圆环仅表示 ROI 中心投影。当前 40 mm 电极的 F5-FC3 存在两节点点接触，两个载波回路的电气独立性未建立；局部分流可能影响 E1、E2、TImax 及其派生统计。本图和相关数值仅用于流程演示，须在验证正间隙并重新网格、求解后替换。"),
        _figure("fig00_four_electrode_e1_e2_timax", "最终四电极 E1、E2 与 TImax 的灰质轴向场分布",
            "图 3｜载波场与最大调制幅值。显示 ROI 高度附近 ±1 mm 的灰质四面体轴向 slab；三面板共用由全灰质 |E1|、|E2|、TImax 正值合并计算的 P99 显示上限。单位为 V/m，绿色轮廓为 ROI。精确逐单元值以 NPZ 为准。"),
        _figure("fig00_four_electrode_timax_surface", "最终四电极 TImax 的灰质表面分布",
            "图 4｜灰质表面 TImax。场值由四面体结果插值到 SimNIBS 灰质表面，色标上限为表面正值 P99，超过上限的颜色被截断但数据未截断。该图用于观察空间分布，不替代四面体级定量。"),
        _figure("fig07_four_electrode_timax_slices", "最终四电极 TImax 的 ROI 三正交切面与靶外极值切面",
            f"图 5｜最终四电极复算场。前三个面板经过 ROI 中心，第四个面板标出靶外灰质单四面体极值 {final['off_target']['max']:.4f} V/m；其个体坐标为 ({', '.join(f'{v:.2f}' for v in final_peak['off_target_peak_conform_mm'])}) mm，距 ROI 中心 {final_peak['distance_from_roi_center_mm']:.2f} mm。色标为 0–{shared_color_max:.4f} V/m。单元极值尚未通过网格和位置稳健性分析，不能解释为稳定解剖热点。"),
        _figure("fig08_four_electrode_quantitative", "目标 ROI 与靶外灰质的最终场强、覆盖率与超阈体积比较",
            f"图 6｜最终定量结果。主分析使用固定绝对阈值 {threshold:.4f} V/m，该数值由搜索场全灰质单四面体极值的 50% 事后导出；敏感性分析另使用复算场自身 50% 极值 {recompute_threshold:.4f} V/m。两者均为探索性阈值，不构成临床剂量门限。"),
    ])

    optimization_figures = "".join([
        _figure("fig02_candidate_objective", "有限候选库中三个组合的目标区 TImax 均值",
            "图 7｜候选目标函数。三个可行组合全部完成计算，柱高为搜索阶段 ROI 体积加权均值。该图用于解释候选排序，不是最终四电极场图。"),
        _figure("fig04_candidate_ranking", "有限候选库目标函数完整排序",
            "图 8｜有限集合排序。第 2、3 名只相差约 0.5%，且没有对这两项进行四活动电极复算，因此名义次序不能解释为稳健优劣。本任务为有限穷举，迭代收敛曲线不适用。"),
        _figure("fig05_current_constraints", "两个载波回路的固定电流约束",
            "图 9｜电流约束。每个回路固定为 +1/-1 mA peak，回路净电流为 0；本次没有优化幅度比，也没有指定载波频率或差频。"),
        _figure("fig06_independent_fem", "搜索场与四活动电极复算场的描述性比较",
            f"图 10｜跨阶段场解对照。ROI 均值由 {search_roi_mean:.4f} 变为 {final_roi_mean:.4f} V/m（+{validation['relative_difference_pct']:.2f}%）；靶外均值由 {search_off_target_mean:.4f} 变为 {final_off_target_mean:.4f} V/m（{off_target_delta_pct:+.2f}%）；目标/靶外均值比由 {search_mean_ratio:.3f} 变为 {final_mean_ratio:.3f}（{mean_ratio_delta_pct:+.2f}%）。复算日志的估计电流校准误差为 0.3%–6.9%，搜索阶段缺少同口径汇总，因此这些差异不能与运行间校准偏差分离，也不能归因于电极构型；本图不是网格收敛或稳健性证据。"),
    ])

    css = """
*{box-sizing:border-box}body{margin:0;background:#eef1ef;color:#19231f;font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;line-height:1.72;letter-spacing:0}main{max-width:1180px;margin:auto;background:#fff;padding:54px 68px}header{border-bottom:3px solid #185f49;padding-bottom:28px}h1{font-size:36px;line-height:1.25;margin:8px 0 12px}h2{font-size:24px;margin:48px 0 18px;padding-top:24px;border-top:1px solid #d8dfdb}h3{font-size:18px;margin:28px 0 10px}p{margin:10px 0}.meta{color:#58675f}.metric{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:22px 0}.metric div{border:1px solid #d4ddd8;padding:16px;min-width:0}.metric span{display:block;color:#58675f;font-size:13px}.metric b{display:block;color:#145f48;font-size:22px;line-height:1.35;margin-top:5px}.scope{border-left:5px solid #9b671b;background:#fff8e9;padding:18px 20px;margin:24px 0}.scope ul{margin:8px 0;padding-left:22px}.result-note{background:#eff7f3;padding:18px 20px;margin:20px 0}figure{margin:30px 0 38px}img{display:block;width:100%;height:auto}figcaption{font-size:14px;color:#485850;margin-top:10px}.scroll{overflow:auto;max-width:100%}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border:1px solid #d5dcd8;padding:8px 9px;text-align:left;vertical-align:top}th{background:#f1f5f3}code{font-size:11px;overflow-wrap:anywhere}.status{font-weight:700;color:#9b671b}.small{font-size:13px;color:#58675f}@media(max-width:760px){main{padding:26px 18px}h1{font-size:29px}.metric{grid-template-columns:1fr 1fr}.metric b{font-size:19px}}@media(max-width:440px){.metric{grid-template-columns:1fr}}@media print{body{background:white}main{max-width:none;padding:15mm}figure,table{break-inside:avoid}h2{break-after:avoid}}
@media(max-width:760px){.scroll table{min-width:720px}}
"""

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>个体化逆向 TI 仿真报告</title><style>{css}</style></head><body><main>
<header><p class="meta">QuanLan BrainScience · SimNIBS 科研演示交付</p><h1>个体化逆向 TI 仿真报告</h1><p>有限候选库离散优化｜SimNIBS ernie 示例受试者｜报告编号 QLA-SIMNIBS-INVERSE-TI-ERNIE-20260729-01</p></header>
<h2>结果摘要</h2><div class="metric"><div><span>候选库内最优方案</span><b>{winner['carrier_1']}<br>+ {winner['carrier_2']}</b></div><div><span>目标 ROI 平均 TImax</span><b>{final['target']['mean']:.4f} V/m</b></div><div><span>目标/靶外均值比</span><b>{validation['independent_target_to_off_target_mean_ratio']:.3f}</b></div><div><span>ROI 覆盖率（固定阈值 / 复算场半峰阈值）</span><b>{final['target']['threshold_coverage_pct']:.2f}% / {sensitivity['target']['threshold_coverage_pct']:.2f}%</b></div></div>
<div class="result-note"><b>结果解释。</b>在本次声明的三个可行双载波组合中，{winner['carrier_1']} + {winner['carrier_2']} 的搜索阶段 ROI 体积加权平均 TImax 最高。对入选方案进行四活动电极构型复算后，目标 ROI 平均 TImax 为 {final['target']['mean']:.4f} V/m，靶外灰质为 {final['off_target']['mean']:.4f} V/m。均值比为 {validation['independent_target_to_off_target_mean_ratio']:.3f}，说明目标区平均场强高于靶外平均水平；但靶外单元极值 {final['off_target']['max']:.4f} V/m 高于目标区极值 {final['target']['max']:.4f} V/m，因此不能表述为高场已限制在 ROI 内，也不能单凭均值比宣称聚焦。</div>
<div class="scope"><b>结果适用范围</b><ul><li>本包证明的是 ernie 示例头模型、固定 1:1 载波幅度和有限候选库内的模型场分布与排序。</li><li>F5-FC3 两节点点接触使两个载波回路的电气独立性未建立。局部分流可能影响 E1、E2、TImax 绝对值及区域统计；在验证正间隙并重新网格、求解前，0.2614 V/m、2.350 和覆盖率等数值只能用于流程演示，不得作为正式研究结果引用。</li><li>未完成客户 MRI 配准、真实 64 通道帽触点映射、非灰质组织暴露、网格收敛、电导率和电极位置敏感性分析。</li><li>结果不验证神经激活、临床安全性、治疗效果或个体处方。<span class="status">当前状态：演示交付包完整，正式研究前提未满足。</span></li></ul></div>
<h2>头模型、刺激方案与最终电场</h2>{primary_figures}
<h2>目标区与靶外定量</h2><div class="scroll"><table><thead><tr><th>区域</th><th>Mean (V/m)</th><th>Median (V/m)</th><th>P95 (V/m)</th><th>单四面体极值 (V/m)</th><th>覆盖率 (%)</th><th>超阈体积 (mm³)</th></tr></thead><tbody>{roi_rows}</tbody></table></div>
<p>主分析阈值为 {threshold:.6f} V/m，由搜索场全灰质单四面体极值的 50% 事后导出。采用复算场自身 50% 极值 {recompute_threshold:.6f} V/m 时，目标 ROI 覆盖率由 {final['target']['threshold_coverage_pct']:.2f}% 变为 {sensitivity['target']['threshold_coverage_pct']:.2f}%，靶外覆盖率由 {final['off_target']['threshold_coverage_pct']:.2f}% 变为 {sensitivity['off_target']['threshold_coverage_pct']:.2f}%。这些阈值用于探索性比较，不是临床阈值。</p>
<h2>逆向优化证据</h2><p>本任务最初尝试调用 SimNIBS 原生 <code>TesFlexOptimization</code>，但在头模型准备阶段终止，未进入优化，也未产生候选解、目标函数或收敛结果。随后采用人工预先声明的三个双极电极对（F5-P5、F6-P6、FC3-CP3）建立离散候选库；这些基对并非由 10-10 全部位置或 64 通道全部组合穷举得到。因此，“最优”仅指该人工候选库内的确定性排序，不代表原生 TesFlex、连续头皮位置或全通道搜索的全局最优。</p><p>目标函数为个体空间半径 20 mm 球形灰质 ROI 内 TImax 的四面体体积加权均值。由上述三个基对组成的三个互不共享电极双载波组合已全部计算；每回路固定 +1/-1 mA peak，未优化幅度分配。搜索网格用于候选排序，入选方案的最终数值来自四活动电极构型复算。</p>{optimization_figures}<div class="scroll"><table><thead><tr><th>排名</th><th>组合</th><th>搜索阶段 ROI mean</th><th>搜索阶段靶外 mean</th><th>搜索阶段目标/靶外均值比</th></tr></thead><tbody>{candidate_rows}</tbody></table></div>
<h2>靶外空间分布与敏感性</h2><p>主阈值下，靶外灰质包含 {cluster['cluster_count']:,} 个按共享三角面定义的超阈连通域；最大连通域体积为 {cluster['clusters'][0]['volume_mm3']:.1f} mm³。改用复算场自身 50% 极值阈值后，连通域数量为 {cluster_sensitivity['cluster_count']:,}，最大连通域体积为 {cluster_sensitivity['clusters'][0]['volume_mm3']:.1f} mm³。聚类数和空间边界随阈值改变，不能解释为阈值稳健的解剖外溢边界。完整结果见带 <code>four_electrode_half_max_sensitivity</code> 后缀的 CSV/JSON。</p>
<h2>设备可执行性</h2><p>本次电极为直径 40 mm、厚 2 mm 的单层 Electrode_rubber 模型，不是 64 通道脑电帽的小触点。即使帽上使用同名 10-10 位置，也必须用真实触点中心、朝向、尺寸、接触层和材料重新建模。当前方案只给出候选库中的电流极性与固定幅度，不构成客户设备的可执行程序。</p>
<h2>数值质量与正式研究前提</h2><p>F5-FC3 两节点点接触使两个载波回路的电气独立性未建立，局部分流可能影响 E1、E2、TImax 绝对值以及由它们计算的区域统计和阈值覆盖率。因此，0.2614 V/m、2.350 和覆盖率等数值仅用于演示计算链；正式引用前必须调整电极几何、验证正的最小间隙，重新网格并完成两个载波场求解，再替换全部场值、统计量和结果图。四活动电极求解日志记录的估计电流校准误差范围为 0.3%–6.9%，原始场值未作事后缩放。与搜索场相比，四活动电极复算场的 ROI 均值增加 {validation['relative_difference_pct']:.2f}%，靶外均值增加 {off_target_delta_pct:.2f}%，目标/靶外均值比下降 {abs(mean_ratio_delta_pct):.2f}%。搜索阶段缺少同口径校准误差汇总，因此三项变化只能作为跨阶段描述性差异，不能与运行间校准偏差分离，也不能归因于电极构型；它们不适用事前接受阈值，也不能代替网格收敛或稳健性分析。正式研究还需完成客户 MRI/帽配准、非灰质组织暴露、网格收敛、组织电导率和电极位置敏感性，以及设备电流与波形约束。</p>
<h2>论文制图与二次分析</h2><div class="scroll"><table><thead><tr><th>图/模块</th><th>科学问题</th><th>机器数据</th><th>状态</th><th>阻断原因</th></tr></thead><tbody>{readiness_rows}</tbody></table></div><p class="small">PNG 用于预览，SVG 用于矢量编辑；最终场的逐单元数据位于 <code>independent_fem/independent_timax_recompute.npz</code>，区域标量位于 <code>report_data.json / results.roi_metrics</code> 和 Excel 的 <code>Final four-electrode metrics</code>，阈值敏感性位于 <code>results.recompute_half_max_threshold_sensitivity</code>。</p>
<h2>交付文件索引</h2><div class="scroll"><table><thead><tr><th>路径</th><th>格式</th><th>用途</th></tr></thead><tbody>{artifact_rows}</tbody></table></div><p>全包文件大小和 SHA-256 见 <code>manifest.json</code>；<code>delivery_root_sha256.txt</code> 保存 manifest 根摘要。历史路径中的 <code>independent_*</code> 只表示入选方案的四活动电极构型复算，不表示独立求解器、网格独立性或科学验证。</p>
<h2>方法与引用</h2><p>TImax 使用 SimNIBS 4.6.0 <code>simnibs.utils.TI_utils.get_maxTI(E1, E2)</code>，结果表示最大调制幅值，包含公式中的因子 2；E1、E2 以每回路 1 mA peak 标定。区域 mean、median、P05 和 P95 按四面体体积加权；分位数按升序累计体积并取首次达到目标概率的单元值，不插值。完整方法、边界和数据字典见 <code>methods/</code>。</p><ol>{reference_rows}</ol><p class="small">引用元数据于 2026-07-29 通过 PubMed E-utilities 核验；SimNIBS 官方网页本次连接超时，因此未把未取回的网页内容写成已核验事实。</p>
</main></body></html>"""
