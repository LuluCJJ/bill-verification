from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[3]
DECK_DIR = ROOT / "docs" / "business-overview-deck"
OUT = DECK_DIR / "output"
PREVIEWS = DECK_DIR / "previews"
OUT.mkdir(parents=True, exist_ok=True)
PREVIEWS.mkdir(parents=True, exist_ok=True)

W, H = 1600, 900
BG = "#FFFFFF"
INK = "#17212F"
TEXT = "#2E3B4B"
MUTED = "#5D6978"
LIGHT = "#F5F7FA"
LIGHT_BLUE = "#EEF5FC"
LINE = "#CDD6E0"
BLUE = "#1D5FA7"
BLUE_DARK = "#174C86"
ORANGE = "#C57918"
GREEN = "#227C55"
RED = "#B83A3A"

FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def text_lines(draw, text, f, max_width):
    lines = []
    for para in text.split("\n"):
        if para == "":
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            if draw.textlength(trial, font=f) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def draw_text(draw, xy, text, size=28, fill=TEXT, bold=False, max_width=None, line_gap=8):
    x, y = xy
    f = font(size, bold)
    if max_width is None:
        draw.text((x, y), text, font=f, fill=fill)
        return draw.textbbox((x, y), text, font=f)[3]
    for line in text_lines(draw, text, f, max_width):
        draw.text((x, y), line, font=f, fill=fill)
        y += size + line_gap
    return y


def rect(draw, box, fill=BG, outline=LINE, width=2):
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def line(draw, xy, fill=LINE, width=2):
    draw.line(xy, fill=fill, width=width)


def arrow(draw, x1, y1, x2, y2, color=BLUE):
    draw.line((x1, y1, x2, y2), fill=color, width=4)
    draw.polygon([(x2, y2), (x2 - 15, y2 - 8), (x2 - 15, y2 + 8)], fill=color)


def canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 10), fill=BLUE_DARK)
    return img


def header(draw, title, judgement):
    draw_text(draw, (70, 42), title, 42, INK, True, 1450)
    draw.rectangle((70, 110, 146, 116), fill=BLUE)
    draw_text(draw, (70, 132), f"核心判断：{judgement}", 24, TEXT, False, 1430, 6)
    line(draw, (70, 178, 1530, 178), LINE, 2)


def conclusion(draw, text):
    y = 812
    draw.rectangle((70, y - 8, 78, y + 52), fill=ORANGE)
    draw_text(draw, (96, y), "关键结论：", 25, ORANGE, True)
    draw_text(draw, (225, y), text, 25, TEXT, True, 1260, 6)


def footer(draw, idx):
    draw_text(draw, (70, 862), f"Bill Verification AI Pre-audit | {idx}/8", 17, "#8A96A3")


def save_slide(img, idx):
    path = PREVIEWS / f"slide_{idx:02d}.png"
    img.save(path)
    return path


def table(draw, x, y, col_widths, row_heights, rows, header_fill=LIGHT_BLUE):
    cur_y = y
    for r, row_h in enumerate(row_heights):
        cur_x = x
        for c, col_w in enumerate(col_widths):
            fill = header_fill if r == 0 else (LIGHT if r % 2 == 0 else BG)
            rect(draw, (cur_x, cur_y, cur_x + col_w, cur_y + row_h), fill=fill, outline=LINE, width=2)
            item = rows[r][c]
            color = BLUE if r == 0 else TEXT
            bold = r == 0 or (c == 0 and r > 0)
            draw_text(draw, (cur_x + 18, cur_y + 16), item, 22 if r == 0 else 21, color, bold, col_w - 36, 6)
            cur_x += col_w
        cur_y += row_h


def s1():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "构建权签票据一致性 AI 预审能力", "将票面信息抽取、字段映射、风险核验和人工反馈拉通为端到端闭环，辅助权签人聚焦高风险差异。")

    y = 245
    labels = [
        ("票面文档输入", "支票 / 转账信 / 汇款申请书"),
        ("AI 原文抽取", "输出 document_items，保留票面 Key/Value 原文"),
        ("规则字段映射", "模板别名 + 字段规则 + AI 候选映射"),
        ("一致性核验", "系统指令 vs 票面字段，输出风险等级"),
        ("权签人确认", "人工聚焦风险并提交优化反馈"),
    ]
    x = 75
    w = 250
    for i, (title, body) in enumerate(labels):
        rect(d, (x, y, x + w, y + 165), fill=LIGHT_BLUE if i in (1, 2) else BG)
        draw_text(d, (x + 18, y + 25), f"{i + 1}. {title}", 25, BLUE, True, w - 36)
        draw_text(d, (x + 18, y + 78), body, 20, TEXT, False, w - 36, 5)
        if i < len(labels) - 1:
            arrow(d, x + w + 8, y + 83, x + w + 55, y + 83, BLUE)
        x += w + 62

    rows = [
        ["建设对象", "核心能力", "管理价值"],
        ["权签预审场景", "票面原文抽取、字段映射、风险规则、反馈沉淀", "降低人工逐项肉眼核对压力，提升问题聚焦效率"],
        ["模板运营机制", "模板别名、位置提示、规则边界、样本反馈", "让能力不依赖频繁发版，支持持续迭代"],
    ]
    table(d, 130, 500, [270, 520, 520], [54, 92, 92], rows)
    conclusion(d, "本项目定位为权签前风险初筛能力，不替代权签人最终判断，而是构建可运营、可解释、可迭代的预审底座。")
    footer(d, 1)
    return img


def s2():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "从人工逐项核对升级为 AI 辅助风险初筛", "现有权签核对面对模板多、字段多、语言多和人员分散的复合压力，需要用智能化能力先完成一轮风险聚焦。")

    rows = [
        ["压力来源", "现状表现", "对权签人的影响", "AI 预审切入点"],
        ["票据模板多", "全球 200+ 银行模板，版式、语言和字段叫法差异明显", "难以依赖统一肉眼经验快速判断", "按模板沉淀别名、位置和抽取提示"],
        ["系统字段多", "MAP/AP 指令有几十个结构化字段，票面只出现子集", "需要判断哪些字段应参与本次核验", "先抽取票面原文，再映射到系统字段"],
        ["兼职权签多", "600+ 权签人中大量兼职权签，职位层级较高", "使用体验对准确性和解释性要求高", "突出风险项，通过项收起，保留证据链"],
        ["迭代周期长", "办公系统版本周期约两个月，频繁发版成本高", "模板问题难以及时修正", "通过配置和反馈样本形成运营闭环"],
    ]
    table(d, 70, 220, [210, 430, 380, 390], [58, 95, 95, 95, 95], rows)

    d.rectangle((105, 716, 1495, 760), fill=LIGHT_BLUE, outline=LINE)
    draw_text(d, (130, 726), "评估口径建议：准确率、召回率、风险采纳率、反馈闭环率、权签人使用满意度。", 24, BLUE_DARK, True, 1320)
    conclusion(d, "第一阶段应以“高风险不漏报、误报可解释”为目标，避免把 Demo 做成只看模型炫技的识别工具。")
    footer(d, 2)
    return img


def s3():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "将模型能力拆分为原文抽取与字段映射两层", "模型负责看懂票面并输出证据，系统负责可解释映射和一致性判断，避免模型直接替代业务规则。")

    rows = [
        ["层级", "输入", "输出", "控制方式", "关键风险"],
        ["1. 票面原文抽取", "票面图片 / 截图 / 扫描件", "原始 Key、Value、位置证据", "提示词约束保留原文，不翻译、不补全", "模型改写票面文字或幻觉补字段"],
        ["2. 字段映射", "票面原文 + 模板规则 + 系统字段字典", "标准字段、原始标签、原始取值、映射来源", "别名规则优先，AI 候选辅助", "别名泛化过度导致误映射"],
        ["3. 规则核验", "系统支付指令 + 标准字段", "风险等级、差异说明、通过项", "金额、账号、币种、日期等规则化比对", "通过项过多干扰权签人阅读"],
        ["4. 反馈沉淀", "人工确认、纠错、忽略、提交优化", "模板别名、样本记录、调优建议", "按模板和字段范围生效", "跨模板配置污染"],
    ]
    table(d, 60, 220, [190, 310, 350, 350, 250], [58, 105, 105, 105, 105], rows)
    conclusion(d, "当前设计的关键不是让模型“猜最终字段”，而是让系统能够解释“票面写了什么、映射成什么、为什么提示风险”。")
    footer(d, 3)
    return img


def s4():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "在付款核验主流程中完成反馈闭环", "反馈不应脱离业务旅程单独存在，而应从一次真实预审风险出发，沉淀为当前模板下的可复用规则。")

    y = 260
    x = 90
    steps = [
        ("选择付款任务", "系统指令 + 票面文件\n模板由系统带出或人工修正"),
        ("启动 AI 预审", "真实调用多模态模型\n抽取票面原文"),
        ("展示风险结果", "风险项展开\n通过项默认收起"),
        ("提交优化反馈", "例如新增别名\n入账行 -> beneficiary_bank"),
        ("重新预审验证", "重新真实提取与核验\n确认配置生效"),
    ]
    for i, (title, body) in enumerate(steps):
        rect(d, (x, y, x + 245, y + 170), fill=LIGHT if i % 2 == 0 else BG)
        draw_text(d, (x + 20, y + 24), f"{i + 1}", 31, ORANGE if i == 3 else BLUE, True)
        draw_text(d, (x + 64, y + 30), title, 24, INK, True, 160)
        draw_text(d, (x + 20, y + 82), body, 19, TEXT, False, 205, 4)
        if i < len(steps) - 1:
            arrow(d, x + 255, y + 86, x + 305, y + 86, BLUE)
        x += 292

    rows = [
        ["演示用例", "初始问题", "人工动作", "验证结果"],
        ["入账行别名漏识别", "模型识别出“入账行”，但未正确映射到收款方银行字段", "在当前模板下新增别名映射并保存", "再次预审后风险消失或降级"],
    ]
    table(d, 140, 540, [270, 520, 340, 300], [54, 96], rows)
    conclusion(d, "业务用户看到的是一次完整核验旅程，产品侧沉淀的是可复用模板资产和高频问题样本。")
    footer(d, 4)
    return img


def s5():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "以规则扩张为主、Prompt 辅助为辅控制映射边界", "别名配置不能简单堆进提示词，应通过规则明确生效范围，再让 Prompt 只补充当前模板必要上下文。")

    rows = [
        ["策略维度", "不建议方式", "推荐方式", "原因"],
        ["字段别名", "把所有别名全部塞进 Prompt，让模型自由联想", "后端维护别名表，支持精确、包含、模糊等受控匹配", "减少“出款方账户/账号/出款账号”之间的无边界泛化"],
        ["模板提示", "让 Prompt 承担全部模板规则", "只写当前位置、票面习惯、特殊注意事项", "让模型更好看图，但不替代系统规则"],
        ["映射判断", "直接信任模型输出的 normalized_field", "模型给候选，系统结合规则和置信度最终落字段", "保证可解释、可回溯、可运营"],
        ["反馈生效", "全局立即生效", "按国家、银行、票据类型、模板版本限定范围", "避免不同模板间互相污染"],
    ]
    table(d, 60, 220, [190, 420, 430, 410], [58, 95, 95, 95, 95], rows)
    conclusion(d, "配置体系的目标不是训练一个更会猜的模型，而是沉淀边界清晰、可解释、可回滚的规则资产。")
    footer(d, 5)
    return img


def s6():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "将高频动作拆分为四类页面，降低业务理解成本", "模型配置、付款核验、模板调优和反馈样本应分工明确，避免把一次性设置和日常核验混在同一工作台。")

    rows = [
        ["页面", "主要用户", "核心动作", "展示重点", "当前 Demo 状态"],
        ["付款核验", "权签人", "选择任务、上传票面、启动 AI 预审、查看风险、提交优化", "系统指令与票面并列，风险项显性化", "主流程已打通"],
        ["模板调优", "业务配置人员", "维护字段别名、位置提示、特殊条款、规则范围", "少技术术语，按模板和字段组织", "已具备雏形"],
        ["反馈样本", "运营 / AI 产品", "查看纠错、忽略、确认不一致、提交优化记录", "高频问题聚合，转规则或转样本", "已展示记录"],
        ["系统设置", "管理员", "配置模型 URL、模型名、API Key、文本/图片诊断", "一次性配置，不干扰日常核验", "已可配置和测试"],
    ]
    table(d, 55, 218, [190, 180, 430, 390, 260], [58, 100, 100, 100, 100], rows)
    conclusion(d, "面向演示时应突出付款核验主流程，模板调优和系统设置作为支撑能力放在后面说明。")
    footer(d, 6)
    return img


def s7():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "沉淀可修改测试资产，支撑业务持续验证配置能力", "真实票据敏感不可外传，因此需要用可编辑 Word 和合成截图构建可复用、可扩展的测试样本体系。")

    rows = [
        ["资产类型", "文件 / 样例", "覆盖重点", "使用方式"],
        ["中文支票 Word", "cn_check_alias_feedback_case", "付款人、收款人、入账行、金额、币种、不可转让", "业务修改字段名和值后截图上传"],
        ["英文电汇 Word", "en_tt_payment_application_case", "Ordering Customer、Account With Institution、SWIFT、Charges", "验证英文和跨境字段映射"],
        ["预置样例 JSON", "中文通过、金额差异、账号差异、别名漏识别", "覆盖风险核验和反馈闭环", "用于 Demo 快速切换与调试"],
        ["模型诊断脚本", "test_model_api.py / image variants", "文本链路、图片链路、base64 image_url 兼容性", "定位公司网关和模型调用差异"],
    ]
    table(d, 70, 220, [230, 390, 460, 350], [58, 100, 100, 100, 100], rows)
    d.rectangle((120, 700, 1480, 748), fill=LIGHT_BLUE, outline=LINE)
    draw_text(d, (145, 711), "建议指标位：样例覆盖数、字段覆盖率、模板覆盖率、反馈闭环率、模型结构化成功率。", 24, BLUE_DARK, True, 1300)
    conclusion(d, "测试资产需要像规则一样持续沉淀，后续才能支撑不同银行模板和不同语言场景的能力评估。")
    footer(d, 7)
    return img


def s8():
    img = canvas()
    d = ImageDraw.Draw(img)
    header(d, "以 MVP 验证带动模板运营和规模化推广", "当前 Demo 已验证关键链路，下一步应从可演示闭环走向可评估、可运营、可接入 MAP 的产品化路径。")

    rows = [
        ["阶段", "建设目标", "关键动作", "衡量指标"],
        ["阶段一：Demo 验证", "打通真实模型、字段抽取、规则核验、反馈闭环", "完善样例、修正页面旅程、沉淀文档和汇报材料", "结构化成功率、演示通过率"],
        ["阶段二：试点模板", "选取高频国家/银行模板进行小范围试点", "建立模板识别、别名范围、特殊条款配置和反馈运营机制", "风险召回率、误报率、反馈闭环率"],
        ["阶段三：MAP 接入", "由 MAP 管理系统字段、模板选择和转换规则", "打通任务输入、票面上传、结果回写和权限边界", "流程耗时、采纳率、问题定位效率"],
        ["阶段四：规模运营", "形成全球模板资产与规则运营体系", "建立样本池、规则版本、回滚机制和效果报表", "模板覆盖率、规则沉淀量、用户满意度"],
    ]
    table(d, 65, 220, [230, 390, 540, 290], [58, 102, 102, 102, 102], rows)
    conclusion(d, "后续重点不是单次模型效果展示，而是形成“模板资产 + 规则资产 + 反馈样本 + 效果指标”的持续运营机制。")
    footer(d, 8)
    return img


slides = [s1(), s2(), s3(), s4(), s5(), s6(), s7(), s8()]
preview_paths = [save_slide(img, i + 1) for i, img in enumerate(slides)]


def add_textbox(slide, x, y, w, h, text_value, size=8, color="#7A8795"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text_value
    p.font.name = "Microsoft YaHei"
    p.font.size = Pt(size)
    p.font.color.rgb = RGBColor.from_string(color.strip("#"))
    return box


prs = Presentation()
prs.slide_width = Inches(16)
prs.slide_height = Inches(9)
blank = prs.slide_layouts[6]
for idx, png in enumerate(preview_paths, start=1):
    slide = prs.slides.add_slide(blank)
    slide.shapes.add_picture(str(png), 0, 0, width=Inches(16), height=Inches(9))
    add_textbox(slide, 0.15, 8.55, 6, 0.3, f"权签票据一致性 AI 预审 - 第 {idx} 页")

pptx_path = OUT / "bill_verification_business_overview.pptx"
prs.save(pptx_path)

montage = Image.new("RGB", (W * 2, H * 4), "#FFFFFF")
for i, img in enumerate(slides):
    montage.paste(img.resize((W, H)), ((i % 2) * W, (i // 2) * H))
montage_path = PREVIEWS / "montage.png"
montage.save(montage_path)

print(pptx_path)
for p in preview_paths:
    print(p)
print(montage_path)
