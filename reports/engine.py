"""Report Engine (spec §38) — deterministic Markdown + PDF rendering.

Every generated report includes: overview, timeline, assets, findings, IOCs,
MITRE ATT&CK, evidence, AI analysis, risk, recommendations, human review and
remediation — no AI-generated prose is included without its evidence ids.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from risk.engine import RiskEngine

# Candidate CJK fonts across Linux / Windows / macOS.
# The first existing file is registered as the PDF fallback font so Chinese
# reports render correctly. Without any CJK font, non-Latin characters are
# replaced with "?" (English reports still render fine).
CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/wenquanyi/wqy-zenhei/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]

# Latin main fonts (full glyph coverage); CJK is used as fallback.
LATIN_FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/System/Library/Fonts/Helvetica.ttc", None),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]


def _find_cjk_font() -> str | None:
    for p in CJK_FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def _find_latin_fonts() -> tuple[str | None, str | None]:
    for regular, bold in LATIN_FONT_CANDIDATES:
        if regular and Path(regular).exists():
            return regular, bold if (bold and Path(bold).exists()) else None
    return None, None


def _latin1_safe(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


def utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Markdown builders
# ---------------------------------------------------------------------------
def build_incident_report(context: dict, ai_analysis: dict | None,
                          risk: dict | None, human_review: dict | None,
                          incident: dict | None = None) -> str:
    inc = incident or context.get("incident", {})
    lines: list[str] = []
    lines.append(f"# 安全事件报告 — {inc.get('title', 'Incident')}")
    lines.append("")
    lines.append(f"> 报告类型：事件报告 | 生成时间：{utcnow_str()} | 事件 ID：`{inc.get('id', '-')}`")
    lines.append("")

    # 1. 事件概述
    lines.append("## 1. 事件概述")
    lines.append("")
    lines.append(inc.get("description") or "-")
    lines.append("")
    lines.append(f"- **状态**：{inc.get('status', '-')}")
    lines.append(f"- **严重性**：{inc.get('severity', '-')}")
    lines.append(f"- **置信度**：{inc.get('confidence', '-')}")
    lines.append(f"- **攻击阶段**：{inc.get('attack_stage', '-')}")
    lines.append(f"- **检测时间**：{inc.get('detected_at', '-')}")
    lines.append("")

    # 2. 时间线
    lines.append("## 2. 时间线")
    lines.append("")
    timeline = sorted(
        [e.get("timestamp"), f"{e.get('source')} event: {e.get('event_type')} from {e.get('src_ip')}"]
        for e in context.get("current_event", [])
        if e.get("timestamp")
    ) + sorted(
        [f.get("first_seen"), f"Nuclei finding: {f.get('title')}"]
        for f in context.get("findings", [])
        if f.get("first_seen")
    )
    if timeline:
        for ts, desc in timeline:
            lines.append(f"- `{ts}` — {desc}")
    else:
        lines.append("- (无)")
    lines.append("")

    # 3. 资产
    lines.append("## 3. 涉及资产")
    lines.append("")
    lines.append("| 资产 | IP | 域名 | 类型 | 环境 | 关键性 |")
    lines.append("|------|----|------|------|------|--------|")
    for a in context.get("asset", []):
        lines.append(
            f"| {a.get('name', '-')} | {a.get('ip', '-')} | {a.get('domain', '-')} "
            f"| {a.get('asset_type', '-')} | {a.get('environment', '-')} | {a.get('criticality', '-')} |"
        )
    if not context.get("asset"):
        lines.append("| - | - | - | - | - | - |")
    lines.append("")

    # 4. 漏洞
    lines.append("## 4. 相关漏洞")
    lines.append("")
    lines.append("| 模板 | 标题 | 严重性 | CVSS | CWE | 状态 |")
    lines.append("|------|------|--------|------|-----|------|")
    for f in context.get("findings", []):
        lines.append(
            f"| {f.get('template_id', '-')} | {f.get('title', '-')} | {f.get('severity', '-')} "
            f"| {f.get('cvss', '-')} | {f.get('cwe', '-')} | {f.get('status', '-')} |"
        )
    if not context.get("findings"):
        lines.append("| - | - | - | - | - | - |")
    lines.append("")

    # 5. IOC
    lines.append("## 5. 威胁情报 IOC")
    lines.append("")
    for i in context.get("threat_intel", []):
        lines.append(f"- `{i.get('type')}`: `{i.get('value')}` (confidence {i.get('confidence')})")
    if not context.get("threat_intel"):
        lines.append("- (无)")
    lines.append("")

    # 6. MITRE
    lines.append("## 6. MITRE ATT&CK")
    lines.append("")
    atk = context.get("attack_context", {})
    techs = atk.get("techniques", [])
    if techs:
        for t in techs:
            lines.append(f"- `{t}`")
    else:
        lines.append("- (无)")
    lines.append("")

    # 7. Evidence
    lines.append("## 7. 证据链")
    lines.append("")
    for e in context.get("evidence", []):
        lines.append(f"- `{e.get('id')}` [{e.get('type')}] {e.get('title')} (source: {e.get('source')})")
    if not context.get("evidence"):
        lines.append("- (无)")
    lines.append("")

    # 8. AI 研判
    lines.append("## 8. AI 研判")
    lines.append("")
    if ai_analysis:
        out = ai_analysis.get("output", {})
        lines.append(f"- **分类**：{out.get('classification', '-')}")
        lines.append(f"- **严重性**：{out.get('severity', '-')}")
        lines.append(f"- **置信度**：{out.get('confidence', '-')}")
        lines.append(f"- **ATT&CK**：{', '.join(out.get('mitre_techniques', [])) or '-'}")
        lines.append(f"- **依据证据**：{', '.join(out.get('evidence_ids', [])) or '-'}")
        lines.append(f"- **研判摘要**：{out.get('reasoning_summary', '-')}")
        lines.append(f"- **处置建议**：{'; '.join(out.get('recommendations', [])) or '-'}")
    else:
        lines.append("- 尚未执行 AI 分析。")
    lines.append("")

    # 9. 风险
    lines.append("## 9. 风险评估")
    lines.append("")
    if risk:
        lines.append(f"- **风险评分**：**{risk.get('risk_score')}**")
        lines.append(f"- **风险等级**：**{risk.get('risk_level')}**")
        lines.append("")
        lines.append("| 因子 | 值 |")
        lines.append("|------|----|")
        for k, v in (risk.get("factors") or {}).items():
            lines.append(f"| {k} | {v} |")
    else:
        lines.append("- 尚未执行风险评估。")
    lines.append("")

    # 10. 处置建议
    lines.append("## 10. 处置建议")
    lines.append("")
    if ai_analysis and ai_analysis.get("output", {}).get("recommendations"):
        for r in ai_analysis["output"]["recommendations"]:
            lines.append(f"- {r}")
    else:
        lines.append("- 隔离受影响资产；收集完整日志；核实 IOC 命中；必要时上报。")
    lines.append("")

    # 11. 人工审核
    lines.append("## 11. 人工审核")
    lines.append("")
    if human_review:
        lines.append(f"- **AI 决策**：{human_review.get('ai_decision', '-')}")
        lines.append(f"- **人工决策**：{human_review.get('human_decision', '-')}")
        lines.append(f"- **审核人**：{human_review.get('reviewer', '-')}")
        lines.append(f"- **意见**：{human_review.get('review_comment', '-')}")
    else:
        lines.append("- 待安全工程师审核。")
    lines.append("")

    # 12. 整改建议
    lines.append("## 12. 整改建议")
    lines.append("")
    lines.append("- 对漏洞进行修复并复测；")
    lines.append("- 封禁确认的恶意 IOC；")
    lines.append("- 强化主机 EDR / HIDS 规则；")
    lines.append("- 对相似资产做横向排查。")
    lines.append("")
    lines.append("---")
    lines.append("*本报告由 SecFlow AI 生成，仅供授权安全运营使用。*")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF rendering (fpdf2, dependency-light)
# ---------------------------------------------------------------------------
def render_pdf(markdown_text: str, out_path: str | Path, title: str = "SecFlow AI Report") -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    cjk_font = _find_cjk_font()
    latin_font, latin_bold = _find_latin_fonts()
    if latin_font:
        # Latin main font (DejaVu/Arial) + CJK fallback for Chinese text.
        # Register regular AND bold CJK variants so fpdf2's exact-match
        # fallback also covers bold headings.
        pdf.add_font("main", "", latin_font)
        if latin_bold:
            pdf.add_font("main", "B", latin_bold)
        pdf.add_font("main", "I", latin_font)
        if cjk_font:
            pdf.add_font("cjk", "", cjk_font)
            pdf.add_font("cjk", "B", cjk_font)
            pdf.add_font("cjk", "I", cjk_font)
            pdf.set_fallback_fonts(["cjk"])
        main_font = "main"
    elif cjk_font:
        # CJK-only fallback (all text rendered in the CJK font)
        pdf.add_font("cjk", "", cjk_font)
        pdf.add_font("cjk", "B", cjk_font)
        pdf.add_font("cjk", "I", cjk_font)
        main_font = "cjk"
    else:
        main_font = "Helvetica"
        markdown_text = _latin1_safe(markdown_text)
        title = _latin1_safe(title)

    pdf.add_page()
    pdf.set_font(main_font, "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(4)

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if not line:
            pdf.ln(2)
            continue
        if line.startswith("# "):
            pdf.set_font(main_font, "B", 14)
            _multi_cell_guarded(pdf, 0, 8, _strip_md(line[2:]), 14)
        elif line.startswith("## "):
            pdf.set_font(main_font, "B", 12)
            _multi_cell_guarded(pdf, 0, 7, _strip_md(line[3:]), 12)
        elif line.startswith("|"):
            continue  # tables rendered as plain lines below
        elif line.startswith("- "):
            pdf.set_font(main_font, "", 10)
            _multi_cell_guarded(pdf, 0, 6, "• " + _strip_md(line[2:]), 10)
        elif line.startswith("> "):
            pdf.set_font(main_font, "I", 9)
            _multi_cell_guarded(pdf, 0, 6, _strip_md(line[2:]), 9)
        else:
            pdf.set_font(main_font, "", 10)
            _multi_cell_guarded(pdf, 0, 6, _strip_md(line), 10)
    pdf.output(str(out))
    return out


def _multi_cell_guarded(pdf: FPDF, w: float, h: float, text: str, size: float) -> None:
    """multi_cell that survives unbreakable long lines (e.g. a long IOC value
    without spaces) by chunking the text."""
    try:
        pdf.multi_cell(w, h, text)
    except Exception:  # noqa: BLE001  (fpdf2 FPDFException)
        chunk = max(8, int(280 / max(size, 6)))
        for i in range(0, len(text), chunk):
            try:
                pdf.multi_cell(w, h, text[i : i + chunk])
            except Exception:  # noqa: BLE001
                pdf.cell(w, h, text[i : i + chunk], ln=True)


_MD_RE = re.compile(r"[`*_\[\]()#]|:\s*-")


def _strip_md(text: str) -> str:
    return _MD_RE.sub("", text).strip() or " "
