"""Build a compact, secret-free final review artifact for the inverse TI package."""

from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729"
GATE = ROOT / "outputs" / "simnibs_inverse_ti_discrete_ernie_20260729_review_gate"
ACCEPTANCE = ROOT / "outputs" / "simnibs_dual_delivery_acceptance_20260729.json"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"style", "script"}:
            self.suppressed += 1
        if tag in {"p", "li", "h1", "h2", "h3", "tr", "figure", "figcaption"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"}:
            self.suppressed = max(0, self.suppressed - 1)
        if tag in {"p", "li", "h1", "h2", "h3", "tr", "figure", "figcaption"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            text = " ".join(data.split())
            if text:
                self.parts.append(text + " ")

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    GATE.mkdir(parents=True, exist_ok=True)
    report_html = PACKAGE / "report.html"
    extractor = TextExtractor()
    extractor.feed(report_html.read_text(encoding="utf-8"))
    report_data = json.loads((PACKAGE / "report_data.json").read_text(encoding="utf-8"))
    visual = json.loads((PACKAGE / "visual_acceptance.json").read_text(encoding="utf-8"))
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    hashes = {
        name: sha256(PACKAGE / name)
        for name in ("report.html", "report.pdf", "report_data.json", "manifest.json")
    }
    artifact = "\n\n".join([
        "# FINAL FROZEN ARTIFACT IDENTITY\n" + json.dumps(hashes, ensure_ascii=False, indent=2),
        "# CUSTOMER REPORT TEXT\n" + extractor.text(),
        "# STRUCTURED REPORT DATA\n" + json.dumps(report_data, ensure_ascii=False, indent=2),
        "# AUTOMATED VISUAL ACCEPTANCE\n" + json.dumps(visual, ensure_ascii=False, indent=2),
        "# DUAL-PACKAGE ACCEPTANCE SUMMARY\n" + json.dumps({
            "status": acceptance["status"],
            "failure_count": acceptance["failure_count"],
            "check_count": len(acceptance["checks"]),
            "failures": acceptance["failures"],
        }, ensure_ascii=False, indent=2),
    ])
    brief = """目标：判断这份基于真实 SimNIBS ernie 数据的逆向 TI 客户交付包，是否已经达到科研演示模板的交付标准，并准确声明正式论文使用前的阻断项。
目标用户：神经科学家、临床研究者，以及需要直接取图和二次统计的研究人员。
产物：客户 HTML/PDF、结构化 JSON、Excel/CSV/NPZ/NIfTI/Msh、出版图和复算脚本。
当前阶段：科研演示模板，不是客户个体正式研究结果。

必须完整攻击以下方面：
1. 科学和数值正确性：TImax、电流幅度、单位、ROI/靶外定义、阈值来源、E1/E2 与最终场口径。
2. 逆向优化边界：有限候选库内最优、搜索场与四活动电极场解复算、未优化幅度和频率；跨阶段差异能否与运行间校准偏差分离，是否存在未经证据支持的构型效应归因。
3. 客户可用性：主结果是否前置，图、标量和机器数据能否追溯，是否把内部流程文字写给客户。
4. 发表与二次分析：图的科学问题、单位、色标、坐标系、ROI、可编辑格式、机器数据和阻断状态是否清楚。
5. 风险边界：F5-FC3 点接触是否被准确解释为两个载波回路的电气独立性未建立，是否明确禁止在重网格并重算两个载波场前引用 E1、E2、TImax、区域统计和覆盖率；示例 MRI、未做客户帽映射、非灰质暴露和稳健性分析是否有任何过度声明。
6. 验收可信度：自动 schema、视觉、manifest 和数值证据是否支持当前结论，不能把自动通过误写成科学验证。

目标用户追问攻击：报告本身必须能够回答以下问题，不能依赖评审者补充解释：
1. 搜索场与四活动电极场解复算中，哪一套数值是最终结果，另一套承担什么作用？
2. “最优”是否只限于三个离散候选，是否等同于连续空间或全 64 通道全局最优？
3. 16.71% 与 9.22% 两个覆盖率为何不同，各自使用什么阈值，能否解释为疗效阈值？
4. 当前图表和数据能否直接作为客户个体论文结果，正式发表前必须替换或补做哪些内容？
5. F5-FC3 点接触会怎样限制两个载波回路的电气独立性和场解解释；0.2614 V/m、2.350 与覆盖率能否正式引用；自动验收通过是否代表网格、求解器或科学验证通过？
6. 6.25% 跨阶段 ROI 均值差异能否归因于电极构型；搜索阶段缺少同口径校准误差汇总时，报告是否明确禁止这种归因？

规则：
- 只根据所给冻结材料判断，不假设未提供的实验、注册、客户 MRI 或设备证据。
- 此前所有轮次的 PASS/FAIL 均已失效；只审本材料列出的新哈希。
- 重点寻找 P0/P1。若存在问题，issues 只返回单个最高影响的新问题并给出可复核证据。
- 若没有 P0/P1，decision 必须为 PASS 且 issues 必须为空。
- unknowns 只能列材料本身无法回答、但不影响当前“演示模板”结论的问题；若 unknown 会影响该结论，应形成 issue。
"""
    (GATE / "final_review_artifact.txt").write_text(artifact, encoding="utf-8")
    (GATE / "final_review_brief.txt").write_text(brief, encoding="utf-8")
    (GATE / "final_frozen_hashes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"artifact_chars": len(artifact), "brief_chars": len(brief), "hashes": hashes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
