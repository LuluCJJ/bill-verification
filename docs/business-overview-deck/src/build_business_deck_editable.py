from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[3]
DECK_DIR = ROOT / "docs" / "business-overview-deck"
OUT = DECK_DIR / "output"
OUT.mkdir(parents=True, exist_ok=True)

PPTX_PATH = OUT / "bill_verification_business_overview_editable.pptx"
SUMMARY_PATH = OUT / "bill_verification_business_overview_editable_summary.json"

W, H = 16, 9
BG = "FFFFFF"
INK = "17212F"
TEXT = "2E3B4B"
MUTED = "5D6978"
LIGHT = "F5F7FA"
LIGHT_BLUE = "EEF5FC"
LINE = "CDD6E0"
BLUE = "1D5FA7"
BLUE_DARK = "174C86"
ORANGE = "C57918"


def rgb(hex_color: str) -> RGBColor:
    value = hex_color.strip().lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def set_typeface(run, name: str = "Microsoft YaHei") -> None:
    run.font.name = name
    r_pr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        node = r_pr.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            r_pr.append(node)
        node.set("typeface", name)


def add_text(
    slide,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: float = 14,
    color: str = TEXT,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.text_frame.word_wrap = True
    box.text_frame.margin_left = Inches(0.03)
    box.text_frame.margin_right = Inches(0.03)
    box.text_frame.margin_top = Inches(0.02)
    box.text_frame.margin_bottom = Inches(0.02)
    box.text_frame.vertical_anchor = valign
    p = box.text_frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)
    set_typeface(run)
    return box


def add_rect(slide, x: float, y: float, w: float, h: float, fill: str = "FFFFFF", line: str = LINE, width: float = 1):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.line.color.rgb = rgb(line)
    shape.line.width = Pt(width)
    return shape


def add_line(slide, x1: float, y1: float, x2: float, y2: float, color: str = LINE, width: float = 1.2):
    shape = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1),
        Inches(y1),
        Inches(x2),
        Inches(y2),
    )
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(width)
    return shape


def add_arrow(slide, x1: float, y1: float, x2: float, y2: float, color: str = BLUE):
    shape = add_line(slide, x1, y1, x2, y2, color, 2)
    shape.line.end_arrowhead = True
    return shape


def add_header(slide, title: str, judgement: str):
    add_rect(slide, 0, 0, W, 0.1, BLUE_DARK, BLUE_DARK, 0)
    add_text(slide, title, 0.55, 0.42, 14.5, 0.48, 22, INK, True)
    add_rect(slide, 0.55, 1.07, 0.58, 0.05, BLUE, BLUE, 0)
    add_text(slide, f"核心判断：{judgement}", 0.55, 1.34, 14.7, 0.34, 12.2, TEXT)
    add_line(slide, 0.55, 1.76, 15.45, 1.76, LINE, 1)


def add_conclusion(slide, text: str):
    add_rect(slide, 0.55, 8.15, 0.07, 0.55, ORANGE, ORANGE, 0)
    add_text(slide, "关键结论：", 0.72, 8.2, 1.15, 0.35, 12.5, ORANGE, True)
    add_text(slide, text, 1.75, 8.2, 13.4, 0.42, 12.5, INK, True)


def add_footer(slide, index: int):
    add_text(slide, f"Bill Verification AI Pre-audit | {index}/8", 0.55, 8.72, 4.3, 0.22, 8.5, "8A96A3")


def add_table(
    slide,
    rows: list[list[str]],
    x: float,
    y: float,
    widths: list[float],
    row_h: float,
    font_size: float = 10.5,
    header_size: float = 11.3,
):
    for r, row in enumerate(rows):
        cursor = x
        fill = LIGHT_BLUE if r == 0 else (LIGHT if r % 2 == 0 else BG)
        for c, text in enumerate(row):
            add_rect(slide, cursor, y + r * row_h, widths[c], row_h, fill, LINE, 1)
            add_text(
                slide,
                text,
                cursor + 0.1,
                y + r * row_h + 0.1,
                widths[c] - 0.18,
                row_h - 0.12,
                header_size if r == 0 else font_size,
                BLUE if r == 0 else INK,
                r == 0 or c == 0,
            )
            cursor += widths[c]


def add_flow(slide, labels: list[tuple[str, str]], x: float, y: float, w: float, h: float, gap: float):
    for i, (title, body) in enumerate(labels):
        add_rect(slide, x, y, w, h, LIGHT_BLUE if i in (1, 2) else BG, LINE, 1)
        add_text(slide, f"{i + 1}. {title}", x + 0.12, y + 0.25, w - 0.24, 0.28, 12.3, BLUE, True)
        add_text(slide, body, x + 0.12, y + 0.75, w - 0.24, h - 0.82, 9.5, TEXT)
        if i < len(labels) - 1:
            add_arrow(slide, x + w + 0.08, y + h / 2, x + w + gap - 0.08, y + h / 2)
        x += w + gap


def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def s1(prs):
    slide = blank_slide(prs)
    add_header(slide, "构建权签票据一致性 AI 预审能力", "将票面信息抽取、字段映射、风险核验和人工反馈拉通为端到端闭环，辅助权签人聚焦高风险差异。")
    add_flow(
        slide,
        [
            ("票面文档输入", "支票 / 转账信 / 汇款申请书"),
            ("AI 原文抽取", "输出 document_items，保留票面 Key/Value 原文"),
            ("规则字段映射", "模板别名 + 字段规则 + AI 候选映射"),
            ("一致性核验", "系统指令 vs 票面字段，输出风险等级"),
            ("权签人确认", "人工聚焦风险并提交优化反馈"),
        ],
        0.6,
        2.45,
        1.55,
        1.55,
        0.4,
    )
    add_table(
        slide,
        [
            ["建设对象", "核心能力", "管理价值"],
            ["权签预审场景", "票面原文抽取、字段映射、风险规则、反馈沉淀", "降低人工逐项肉眼核对压力，提升问题聚焦效率"],
            ["模板运营机制", "模板别名、位置提示、规则边界、样本反馈", "让能力不依赖频繁发版，支持持续迭代"],
        ],
        1.1,
        5.0,
        [2.6, 5.0, 5.0],
        0.62,
        10.4,
    )
    add_conclusion(slide, "本项目定位为权签前风险初筛能力，不替代权签人最终判断，而是构建可运营、可解释、可迭代的预审底座。")
    add_footer(slide, 1)


def s2(prs):
    slide = blank_slide(prs)
    add_header(slide, "从人工逐项核对升级为 AI 辅助风险初筛", "现有权签核对面对模板多、字段多、语言多和人员分散的复合压力，需要用智能化能力先完成一轮风险聚焦。")
    add_table(
        slide,
        [
            ["压力来源", "现状表现", "对权签人的影响", "AI 预审切入点"],
            ["票据模板多", "全球 200+ 银行模板，版式、语言和字段叫法差异明显", "难以依赖统一肉眼经验快速判断", "按模板沉淀别名、位置和抽取提示"],
            ["系统字段多", "MAP/AP 指令有几十个结构化字段，票面只出现子集", "需要判断哪些字段应参与本次核验", "先抽取票面原文，再映射到系统字段"],
            ["兼职权签多", "600+ 权签人中大量兼职权签，职位层级较高", "使用体验对准确性和解释性要求高", "突出风险项，通过项收起，保留证据链"],
            ["迭代周期长", "办公系统版本周期约两个月，频繁发版成本高", "模板问题难以及时修正", "通过配置和反馈样本形成运营闭环"],
        ],
        0.55,
        2.15,
        [1.7, 4.1, 3.6, 3.6],
        0.88,
        9.5,
    )
    add_rect(slide, 0.85, 7.18, 14.1, 0.36, LIGHT_BLUE, LINE, 1)
    add_text(slide, "评估口径建议：准确率、召回率、风险采纳率、反馈闭环率、权签人使用满意度。", 1.0, 7.25, 13.5, 0.24, 11.8, BLUE_DARK, True)
    add_conclusion(slide, "第一阶段应以“高风险不漏报、误报可解释”为目标，避免把 Demo 做成只看模型炫技的识别工具。")
    add_footer(slide, 2)


def s3(prs):
    slide = blank_slide(prs)
    add_header(slide, "将模型能力拆分为原文抽取与字段映射两层", "模型负责看懂票面并输出证据，系统负责可解释映射和一致性判断，避免模型直接替代业务规则。")
    add_table(
        slide,
        [
            ["层级", "输入", "输出", "控制方式", "关键风险"],
            ["1. 票面原文抽取", "票面图片 / 截图 / 扫描件", "原始 Key、Value、位置证据", "提示词约束保留原文，不翻译、不补全", "模型改写票面文字或幻觉补字段"],
            ["2. 字段映射", "票面原文 + 模板规则 + 系统字段字典", "标准字段、原始标签、原始取值、映射来源", "别名规则优先，AI 候选辅助", "别名泛化过度导致误映射"],
            ["3. 规则核验", "系统支付指令 + 标准字段", "风险等级、差异说明、通过项", "金额、账号、币种、日期等规则化比对", "通过项过多干扰权签人阅读"],
            ["4. 反馈沉淀", "人工确认、纠错、忽略、提交优化", "模板别名、样本记录、调优建议", "按模板和字段范围生效", "跨模板配置污染"],
        ],
        0.45,
        2.15,
        [1.55, 3.0, 3.35, 3.35, 2.35],
        0.9,
        9.2,
    )
    add_conclusion(slide, "当前设计的关键不是让模型“猜最终字段”，而是让系统能够解释“票面写了什么、映射成什么、为什么提示风险”。")
    add_footer(slide, 3)


def s4(prs):
    slide = blank_slide(prs)
    add_header(slide, "在付款核验主流程中完成反馈闭环", "反馈不应脱离业务流程单独存在，而应从一次真实预审风险出发，沉淀为当前模板下的可复用规则。")
    add_flow(
        slide,
        [
            ("选择付款任务", "系统指令 + 票面文件\n模板由系统带出或人工修正"),
            ("启动 AI 预审", "真实调用多模态模型\n抽取票面原文"),
            ("展示风险结果", "风险项展开\n通过项默认收起"),
            ("提交优化反馈", "例如新增别名\n入账行 -> beneficiary_bank"),
            ("重新预审验证", "重新真实提取与核验\n确认配置生效"),
        ],
        0.65,
        2.65,
        1.45,
        1.55,
        0.42,
    )
    add_table(
        slide,
        [
            ["演示用例", "初始问题", "人工动作", "验证结果"],
            ["入账行别名漏识别", "模型识别出“入账行”，但未正确映射到收款方银行字段", "在当前模板下新增别名映射并保存", "再次预审后风险消失或降级"],
        ],
        1.0,
        5.75,
        [2.3, 5.0, 3.2, 3.1],
        0.62,
        10.0,
    )
    add_conclusion(slide, "业务用户看到的是一次完整核验旅程，产品侧沉淀的是可复用模板资产和高频问题样本。")
    add_footer(slide, 4)


def s5(prs):
    slide = blank_slide(prs)
    add_header(slide, "以规则扩张为主、Prompt 辅助为辅控制映射边界", "别名配置不能简单堆进提示词，应通过规则明确生效范围，再让 Prompt 只补充当前模板必要上下文。")
    add_table(
        slide,
        [
            ["策略维度", "不建议方式", "推荐方式", "原因"],
            ["字段别名", "把所有别名全部塞进 Prompt，让模型自由联想", "后端维护别名表，支持精确、包含、模糊等受控匹配", "减少“出款方账户/账号/出款账号”之间的无边界泛化"],
            ["模板提示", "让 Prompt 承担全部模板规则", "只写当前位置、票面习惯、特殊注意事项", "让模型更好看图，但不替代系统规则"],
            ["映射判断", "直接信任模型输出的 normalized_field", "模型给候选，系统结合规则和置信度最终落字段", "保证可解释、可回溯、可运营"],
            ["反馈生效", "全局立即生效", "按国家、银行、票据类型、模板版本限定范围", "避免不同模板间互相污染"],
        ],
        0.55,
        2.25,
        [1.75, 4.1, 4.2, 3.55],
        0.92,
        9.4,
    )
    add_conclusion(slide, "配置体系的目标不是训练一个更会猜的模型，而是沉淀边界清晰、可解释、可回滚的规则资产。")
    add_footer(slide, 5)


def s6(prs):
    slide = blank_slide(prs)
    add_header(slide, "将高频动作拆分为四类页面，降低业务理解成本", "模型配置、付款核验、模板调优和反馈样本应分工明确，避免把一次性设置和日常核验混在同一工作台。")
    add_table(
        slide,
        [
            ["页面", "主要用户", "核心动作", "展示重点", "当前 Demo 状态"],
            ["付款核验", "权签人", "选择任务、上传票面、启动 AI 预审、查看风险、提交优化", "系统指令与票面并列，风险项显性化", "主流程已打通"],
            ["模板调优", "业务配置人员", "维护字段别名、位置提示、特殊条款、规则范围", "少技术术语，按模板和字段组织", "已具备雏形"],
            ["反馈样本", "运营 / AI 产品", "查看纠错、忽略、确认不一致、提交优化记录", "高频问题聚合，转规则或转样本", "已展示记录"],
            ["系统设置", "管理员", "配置模型 URL、模型名、API Key、文本/图片诊断", "一次性配置，不干扰日常核验", "已可配置和测试"],
        ],
        0.45,
        2.25,
        [1.65, 1.65, 4.15, 3.75, 2.15],
        0.9,
        9.0,
    )
    add_conclusion(slide, "面向演示时应突出付款核验主流程，模板调优和系统设置作为支撑能力放在后面说明。")
    add_footer(slide, 6)


def s7(prs):
    slide = blank_slide(prs)
    add_header(slide, "沉淀可修改测试资产，支撑业务持续验证配置能力", "真实票据敏感不可外传，因此需要用可编辑 Word 和合成截图构建可复用、可扩展的测试样本体系。")
    add_table(
        slide,
        [
            ["资产类型", "文件 / 样例", "覆盖重点", "使用方式"],
            ["中文支票 Word", "cn_check_alias_feedback_case", "付款人、收款人、入账行、金额、币种、不可转让", "业务修改字段名和值后截图上传"],
            ["英文电汇 Word", "en_tt_payment_application_case", "Ordering Customer、Account With Institution、SWIFT、Charges", "验证英文和跨境字段映射"],
            ["预置样例 JSON", "中文通过、金额差异、账号差异、别名漏识别", "覆盖风险核验和反馈闭环", "用于 Demo 快速切换与调试"],
            ["模型诊断脚本", "test_model_api.py / image variants", "文本链路、图片链路、base64 image_url 兼容性", "定位公司网关和模型调用差异"],
        ],
        0.55,
        2.25,
        [2.1, 3.7, 4.3, 3.4],
        0.9,
        9.4,
    )
    add_rect(slide, 0.95, 7.18, 13.8, 0.36, LIGHT_BLUE, LINE, 1)
    add_text(slide, "建议指标位：样例覆盖数、字段覆盖率、模板覆盖率、反馈闭环率、模型结构化成功率。", 1.1, 7.25, 13.1, 0.24, 11.5, BLUE_DARK, True)
    add_conclusion(slide, "测试资产需要像规则一样持续沉淀，后续才能支撑不同银行模板和不同语言场景的能力评估。")
    add_footer(slide, 7)


def s8(prs):
    slide = blank_slide(prs)
    add_header(slide, "以 MVP 验证带动模板运营和规模化推广", "当前 Demo 已验证关键链路，下一步应从可演示闭环走向可评估、可运营、可接入 MAP 的产品化路径。")
    add_table(
        slide,
        [
            ["阶段", "建设目标", "关键动作", "衡量指标"],
            ["阶段一：Demo 验证", "打通真实模型、字段抽取、规则核验、反馈闭环", "完善样例、修正页面旅程、沉淀文档和汇报材料", "结构化成功率、演示通过率"],
            ["阶段二：试点模板", "选取高频国家/银行模板进行小范围试点", "建立模板识别、别名范围、特殊条款配置和反馈运营机制", "风险召回率、误报率、反馈闭环率"],
            ["阶段三：MAP 接入", "由 MAP 管理系统字段、模板选择和转换规则", "打通任务输入、票面上传、结果回写和权限边界", "流程耗时、采纳率、问题定位效率"],
            ["阶段四：规模运营", "形成全球模板资产与规则运营体系", "建立样本池、规则版本、回滚机制和效果报表", "模板覆盖率、规则沉淀量、用户满意度"],
        ],
        0.55,
        2.25,
        [2.05, 3.6, 5.0, 2.75],
        0.9,
        9.4,
    )
    add_conclusion(slide, "后续重点不是单次模型效果展示，而是形成“模板资产 + 规则资产 + 反馈样本 + 效果指标”的持续运营机制。")
    add_footer(slide, 8)


def count_shapes(prs: Presentation) -> dict[str, int]:
    counts = {"slides": len(prs.slides), "text_boxes": 0, "shapes": 0, "tables": 0, "pictures": 0}
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_table:
                counts["tables"] += 1
            elif getattr(shape, "shape_type", None) == 13:
                counts["pictures"] += 1
            elif shape.has_text_frame:
                counts["text_boxes"] += 1
            else:
                counts["shapes"] += 1
    return counts


def main():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    for builder in (s1, s2, s3, s4, s5, s6, s7, s8):
        builder(prs)

    prs.save(PPTX_PATH)

    reopened = Presentation(PPTX_PATH)
    summary = {
        "pptx": str(PPTX_PATH),
        "editable": True,
        "fallback_images": 0,
        "note": "All visible slide content is built from native PowerPoint text boxes, shapes, lines, and editable table-like cell groups. No full-slide image fallback is used.",
        "counts": count_shapes(reopened),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(PPTX_PATH)
    print(SUMMARY_PATH)
    print(json.dumps(summary["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
