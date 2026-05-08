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
BG = "#F6F8FB"
INK = "#162333"
MUTED = "#5B6878"
BLUE = "#1F66B3"
GREEN = "#227C55"
RED = "#B93A3A"
AMBER = "#B87514"
LINE = "#D7E0EA"

FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def draw_text(draw, xy, text, size=32, fill=INK, bold=False, max_width=None, line_gap=8):
    x, y = xy
    f = font(size, bold)
    if "\n" in text:
        for line in text.split("\n"):
            y = draw_text(draw, (x, y), line, size, fill, bold, max_width, line_gap)
        return y
    if not max_width:
        draw.text((x, y), text, font=f, fill=fill)
        box = draw.textbbox((x, y), text, font=f)
        return box[3]
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=f) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill)
        y += size + line_gap
    return y


def rounded(draw, box, fill, outline=None, width=2, r=20):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def pill(draw, x, y, text, color=BLUE):
    f = font(22, True)
    w = draw.textlength(text, font=f) + 38
    rounded(draw, (x, y, x + w, y + 44), fill="#EAF3FF", outline="#BFD7F0", r=22)
    draw.text((x + 19, y + 10), text, font=f, fill=color)
    return x + w


def arrow(draw, x1, y1, x2, y2, color=BLUE):
    draw.line((x1, y1, x2, y2), fill=color, width=5)
    draw.polygon([(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)], fill=color)


def canvas():
    return Image.new("RGB", (W, H), BG)


def footer(draw, idx):
    draw.text((80, 842), f"Bill Verification AI Pre-audit · {idx}/8", font=font(18), fill="#7A8795")


def save_slide(img, idx):
    path = PREVIEWS / f"slide_{idx:02d}.png"
    img.save(path)
    return path


def slide_title(draw, title, subtitle=None):
    draw_text(draw, (80, 58), title, 46, INK, True, 1380)
    if subtitle:
        draw_text(draw, (82, 118), subtitle, 24, MUTED, False, 1320)


def s1():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, H), fill="#EDF4F8")
    d.polygon([(980, 0), (1600, 0), (1600, 900), (1220, 900)], fill="#D8EAF5")
    d.polygon([(1120, 0), (1600, 0), (1600, 900), (1370, 900)], fill="#C9E1EC")
    draw_text(d, (90, 110), "权签票据一致性\nAI 预审方案", 72, INK, True, 760, 16)
    draw_text(d, (94, 322), "最新框架：AI 抽取票面原文，系统规则映射字段，权签人聚焦风险", 34, MUTED, False, 820)
    x = 94
    for label in ["支票", "转账信", "汇款申请书", "MAP/AP 指令"]:
        x = pill(d, x, 446, label) + 14
    rounded(d, (1040, 190, 1450, 620), "#FFFFFF", "#BFD0DD", 3, 28)
    draw_text(d, (1090, 245), "票面原文", 28, BLUE, True)
    draw_text(d, (1090, 300), "Key: 入账行\nValue: 中国工商银行上海分行", 25, INK, False, 310, 14)
    arrow(d, 1130, 445, 1340, 445)
    draw_text(d, (1090, 490), "映射字段", 28, GREEN, True)
    draw_text(d, (1090, 540), "beneficiary_bank", 26, INK, True)
    footer(d, 1)
    return img


def s2():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "为什么要做：权签核对正在变成高成本风险点")
    cards = [
        ("票面形态多", "全球 200+ 银行模板，字段叫法、语言、版式差异大。", BLUE),
        ("系统字段多", "MAP/AP 有几十个结构化字段，票面往往只出现子集。", AMBER),
        ("人工压力大", "600+ 权签人，兼职权签多，靠肉眼逐项核对体验差。", RED),
    ]
    x = 80
    for title, body, color in cards:
        rounded(d, (x, 190, x + 440, 510), "#FFFFFF", LINE, 2, 22)
        d.ellipse((x + 28, 220, x + 88, 280), fill=color)
        draw_text(d, (x + 110, 222), title, 34, INK, True)
        draw_text(d, (x + 36, 320), body, 28, MUTED, False, 360, 12)
        x += 500
    draw_text(d, (100, 650), "目标不是替代权签人，而是在权签前做一轮风险初筛，让人聚焦真正需要判断的问题。", 38, GREEN, True, 1320)
    footer(d, 2)
    return img


def s3():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "最新核心链路：原文抽取与字段映射分层")
    cols = [
        ("1. 票面原文抽取", "document_items\nraw_key / raw_value\n逐字保留票面文字", BLUE),
        ("2. 字段映射", "extracted_fields\nnormalized_field\n别名 + 模板 + AI 候选", GREEN),
        ("3. 规则核验", "system_value\nvs document_value\n金额/账号/币种/日期\n输出风险等级", AMBER),
    ]
    x = 80
    for title, body, color in cols:
        rounded(d, (x, 200, x + 440, 650), "#FFFFFF", LINE, 2, 24)
        draw_text(d, (x + 35, 245), title, 34, color, True, 360)
        draw_text(d, (x + 35, 330), body, 30, INK, False, 360, 18)
        if x < 1080:
            arrow(d, x + 460, 420, x + 555, 420, "#8BA8C5")
        x += 520
    draw_text(d, (110, 720), "设计原则：模型不要替业务做最终判断；系统必须能解释“文档写了什么、映射成什么、为什么提示风险”。", 32, INK, True, 1320)
    footer(d, 3)
    return img


def s4():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "付款核验用户旅程：在主流程里完成反馈闭环")
    steps = [
        ("选择任务", "系统指令 + 票面文件"),
        ("真实提取", "调用多模态模型"),
        ("发现风险", "如“入账行”未映射"),
        ("提交优化", "加入当前模板别名"),
        ("再次预审", "重新真实提取并核验"),
    ]
    x = 100
    for i, (title, body) in enumerate(steps):
        rounded(d, (x, 250, x + 230, 520), "#FFFFFF", LINE, 2, 22)
        d.ellipse((x + 76, 280, x + 154, 358), fill="#EAF3FF", outline="#BFD7F0", width=3)
        draw_text(d, (x + 103, 298), str(i + 1), 34, BLUE, True)
        draw_text(d, (x + 36, 385), title, 28, INK, True, 170)
        draw_text(d, (x + 30, 440), body, 22, MUTED, False, 175)
        if i < len(steps) - 1:
            arrow(d, x + 245, 385, x + 310, 385, "#8BA8C5")
        x += 290
    rounded(d, (160, 650, 1440, 755), "#FFFFFF", "#CFE0D6", 2, 24)
    draw_text(d, (210, 680), "Demo 中新增“反馈闭环：入账行别名漏识别”付款任务，整个过程都在付款核验页完成。", 32, GREEN, True, 1140)
    footer(d, 4)
    return img


def s5():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "配置策略：规则扩张为主，Prompt 辅助为辅")
    rounded(d, (90, 180, 720, 690), "#FFFFFF", LINE, 2, 24)
    rounded(d, (880, 180, 1510, 690), "#FFFFFF", LINE, 2, 24)
    draw_text(d, (130, 225), "不建议", 36, RED, True)
    bad = ["把所有别名全部堆进 prompt", "让模型自由联想更多叫法", "把模型输出直接当最终映射", "无法解释配置为何生效"]
    y = 305
    for item in bad:
        draw_text(d, (135, y), "X", 30, RED, True)
        draw_text(d, (180, y), item, 28, INK, False, 460)
        y += 72
    draw_text(d, (920, 225), "建议", 36, GREEN, True)
    good = ["模型先抽取原始 Key/Value", "别名表明确匹配边界", "模板规则控制生效范围", "Prompt 只放当前模板必要提示"]
    y = 305
    for item in good:
        draw_text(d, (925, y), "OK", 25, GREEN, True)
        draw_text(d, (970, y), item, 28, INK, False, 460)
        y += 72
    footer(d, 5)
    return img


def s6():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "产品页面：四类动作分开，但反馈闭环回到主旅程")
    items = [
        ("付款核验", "权签人", "系统指令、票面文件、真实模型提取、风险结果、提交优化", BLUE),
        ("模板调优", "配置人员", "字段别名、位置提示、AI 识别要求、比对口径", GREEN),
        ("反馈样本", "运营/AI 产品", "查看反馈记录，后续聚合高频错误并转规则", AMBER),
        ("系统设置", "管理员", "模型 URL、模型名、API Key、文本/图片诊断", "#64748B"),
    ]
    y = 160
    for title, role, body, color in items:
        rounded(d, (110, y, 1490, y + 120), "#FFFFFF", LINE, 2, 20)
        d.rectangle((110, y, 128, y + 120), fill=color)
        draw_text(d, (160, y + 25), title, 34, INK, True)
        pill(d, 405, y + 30, role, color)
        draw_text(d, (650, y + 32), body, 27, MUTED, False, 760)
        y += 145
    footer(d, 6)
    return img


def s7():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "测试资产：让业务自己改 Word、截图造样例")
    rounded(d, (120, 190, 740, 650), "#FFFFFF", LINE, 2, 24)
    rounded(d, (860, 190, 1480, 650), "#FFFFFF", LINE, 2, 24)
    draw_text(d, (165, 245), "中文支票 Word", 34, BLUE, True)
    draw_text(d, (165, 320), "cn_check_alias_feedback_case.docx\n\n包含：付款人、收款人、入账行、金额、币种、不可转让。", 28, INK, False, 500, 16)
    draw_text(d, (905, 245), "英文电汇 Word", 34, GREEN, True)
    draw_text(d, (905, 320), "en_tt_payment_application_case.docx\n\n包含：Ordering Customer、Account With Institution、SWIFT、Charges。", 28, INK, False, 500, 16)
    draw_text(d, (155, 720), "业务可直接改字段名、字段值和版式，再截图上传 Demo，验证别名与模板配置是否生效。", 34, INK, True, 1240)
    footer(d, 7)
    return img


def s8():
    img = canvas()
    d = ImageDraw.Draw(img)
    slide_title(d, "当前状态与下一步")
    rounded(d, (90, 170, 730, 690), "#FFFFFF", "#CFE0D6", 2, 22)
    rounded(d, (870, 170, 1510, 690), "#FFFFFF", "#F0D7A8", 2, 22)
    draw_text(d, (130, 220), "已完成", 36, GREEN, True)
    done = ["公司内模型文本/图片链路可访问", "真实模型提取进入付款核验主流程", "document_items 与 extracted_fields 分层", "反馈别名用例可重新真实提取", "中英文 Word 测试用例"]
    y = 290
    for item in done:
        draw_text(d, (135, y), "OK", 25, GREEN, True)
        draw_text(d, (180, y), item, 27, INK, False, 480)
        y += 66
    draw_text(d, (910, 220), "下一步建议", 36, AMBER, True)
    todo = ["增加别名匹配方式：精确/包含/模糊", "反馈样本池聚合高频问题并转规则", "模板识别：系统带出 + AI 建议 + 人工修正", "PDF 转图片进入模型识别", "扩大 Word/截图样例覆盖范围"]
    y = 290
    for item in todo:
        draw_text(d, (915, y), ">", 30, AMBER, True)
        draw_text(d, (960, y), item, 27, INK, False, 480)
        y += 66
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
