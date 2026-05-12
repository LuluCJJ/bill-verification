from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "architecture-options" / "output"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1600, 900
BG = "#FFFFFF"
INK = "#17212F"
TEXT = "#2E3B4B"
MUTED = "#5D6978"
LINE = "#CDD6E0"
LIGHT = "#F5F7FA"
BLUE = "#1D5FA7"
BLUE_DARK = "#174C86"
LIGHT_BLUE = "#EEF5FC"
ORANGE = "#C57918"
GREEN = "#227C55"
RED = "#B83A3A"

FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def text_lines(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            trial = cur + ch
            if draw.textlength(trial, font=fnt) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def draw_text(draw, xy, text, size=24, fill=TEXT, bold=False, max_width=None, line_gap=6):
    x, y = xy
    fnt = font(size, bold)
    if max_width is None:
        draw.text((x, y), text, font=fnt, fill=fill)
        return y + size
    for line in text_lines(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + line_gap
    return y


def rect(draw, box, fill=BG, outline=LINE, width=2):
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def pill(draw, x, y, text, fill, color=BG):
    w = int(draw.textlength(text, font=font(20, True))) + 34
    draw.rounded_rectangle((x, y, x + w, y + 38), radius=5, fill=fill)
    draw_text(draw, (x + 17, y + 7), text, 20, color, True)
    return x + w


def step_box(draw, x, y, title, body, w=160, h=92, fill=BG):
    rect(draw, (x, y, x + w, y + h), fill=fill, outline=LINE, width=2)
    title_size = 19
    draw_text(draw, (x + 12, y + 11), title, title_size, BLUE, True, w - 24, 4)
    draw_text(draw, (x + 12, y + 52), body, 15, TEXT, False, w - 24, 4)


def arrow(draw, x1, y1, x2, y2, color=BLUE):
    draw.line((x1, y1, x2, y2), fill=color, width=3)
    draw.polygon([(x2, y2), (x2 - 13, y2 - 7), (x2 - 13, y2 + 7)], fill=color)


def capability_row(draw, y, label, a_text, b_text):
    rect(draw, (70, y, 255, y + 58), fill=LIGHT_BLUE, outline=LINE, width=2)
    rect(draw, (255, y, 805, y + 58), fill=BG, outline=LINE, width=2)
    rect(draw, (805, y, 1530, y + 58), fill=BG, outline=LINE, width=2)
    draw_text(draw, (88, y + 16), label, 20, BLUE, True, 145, 4)
    draw_text(draw, (275, y + 13), a_text, 19, TEXT, False, 500, 4)
    draw_text(draw, (825, y + 13), b_text, 19, TEXT, False, 660, 4)


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 10), fill=BLUE_DARK)

    draw_text(draw, (70, 38), "MAP 与 AI 产品边界：两种配置方案对比", 42, INK, True, 1420)
    draw.rectangle((70, 108, 146, 114), fill=BLUE)
    draw_text(
        draw,
        (70, 130),
        "核心问题：MAP 已天然管理模板和电子流字段；AI 至少需要字段清单。当前需要对齐 AI 识别配置和测试入口放在哪个产品边界。",
        23,
        TEXT,
        False,
        1450,
        6,
    )
    draw.line((70, 176, 1530, 176), fill=LINE, width=2)

    x = 80
    x = pill(draw, x, 202, "共识前提", BLUE)
    draw_text(
        draw,
        (x + 18, 206),
        "先确认模板 -> 配置待检查系统字段 -> 判断是否启用 AI；无字段约束的全量提取在 POC 中幻觉明显。",
        21,
        TEXT,
        False,
        1210,
        5,
    )

    # Option A
    rect(draw, (70, 262, 770, 586), fill="#FBFCFE", outline=LINE, width=2)
    draw_text(draw, (94, 286), "方案 A：MAP 集成 AI 识别配置与测试", 28, BLUE, True, 640)
    draw_text(draw, (94, 326), "一个入口完成模板、字段、AI 说明、测试、发布和启用。", 20, MUTED, False, 630)
    steps_a = [
        ("1 模板", "MAP 确认/选择"),
        ("2 字段", "系统电子流映射"),
        ("3 AI说明", "别名 + 识别说明"),
        ("4 测试", "直接调 AI 验证"),
        ("5 启用", "发布后正式核验"),
    ]
    sx = 96
    for idx, (title, body) in enumerate(steps_a):
        step_box(draw, sx, 382, title, body, 112, 88, LIGHT_BLUE if idx == 2 else BG)
        if idx < len(steps_a) - 1:
            arrow(draw, sx + 112, 426, sx + 145, 426, BLUE)
        sx += 145
    draw_text(draw, (96, 496), "MAP 能力：模板字段配置、AI 识别说明、测试入口、发布/回滚、正式调用。", 19, TEXT, True, 620, 5)
    draw_text(draw, (96, 536), "AI 能力：多模态提取接口、Prompt 组装、前后处理、稳定结构化输出。", 19, TEXT, False, 620, 5)

    # Option B
    rect(draw, (830, 262, 1530, 586), fill="#FBFCFE", outline=LINE, width=2)
    draw_text(draw, (854, 286), "方案 B：MAP 配字段，AI 产品独立配置", 28, BLUE, True, 640)
    draw_text(draw, (854, 326), "MAP 与 AI 两边配置联动，AI 侧新增配置台和测试沙箱。", 20, MUTED, False, 630)
    steps_b = [
        ("1 字段", "保存\n字段清单"),
        ("2 同步", "传给 AI 产品"),
        ("3 AI配置", "别名 + 说明"),
        ("4 测试", "AI 沙箱验证"),
        ("5 回传", "再回 MAP 启用"),
    ]
    sx = 856
    for idx, (title, body) in enumerate(steps_b):
        step_box(draw, sx, 382, title, body, 112, 88, LIGHT if idx == 2 else BG)
        if idx < len(steps_b) - 1:
            arrow(draw, sx + 112, 426, sx + 145, 426, BLUE)
        sx += 145
    draw_text(draw, (856, 496), "MAP 能力：字段清单、同步接口、状态展示、跳转入口、正式调用。", 19, TEXT, True, 620, 5)
    draw_text(draw, (856, 536), "AI 能力：配置前端、版本权限、测试沙箱、状态回传、提取接口。", 19, TEXT, False, 620, 5)

    # Comparison table
    draw_text(draw, (70, 610), "能力与成本对比", 26, INK, True)
    rect(draw, (70, 648, 255, 700), fill=LIGHT_BLUE, outline=LINE, width=2)
    rect(draw, (255, 648, 805, 700), fill=LIGHT_BLUE, outline=LINE, width=2)
    rect(draw, (805, 648, 1530, 700), fill=LIGHT_BLUE, outline=LINE, width=2)
    draw_text(draw, (88, 664), "维度", 21, BLUE, True)
    draw_text(draw, (275, 664), "方案 A：配置集中在 MAP", 21, BLUE, True)
    draw_text(draw, (825, 664), "方案 B：AI 独立配置台", 21, BLUE, True)
    capability_row(draw, 700, "用户旅程", "单页完成配置、测试和发布", "MAP -> AI -> MAP，多页面跳转")
    capability_row(draw, 758, "研发边界", "MAP 加字段说明和测试入口；AI 做能力接口", "MAP 做同步；AI 额外做前端、权限、版本、沙箱")

    draw.rectangle((70, 836, 78, 881), fill=ORANGE)
    draw_text(draw, (96, 828), "待确认：", 24, ORANGE, True)
    draw_text(
        draw,
        (205, 828),
        "一个模板多场景是否拆分/选择；AI 启用标准；测试通过责任人。",
        24,
        TEXT,
        True,
        1230,
        5,
    )
    out = OUT / "map_ai_boundary_options_v3.png"
    img.save(out)
    img.save(OUT / "map_ai_boundary_options.png")
    print(out)


if __name__ == "__main__":
    build()
