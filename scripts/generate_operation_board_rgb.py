from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "docs/reference/试纸色卡素材"
OUT_IMAGE = ROOT / "docs/images/炉保保操作台底板-RGB提取打样版.png"
OUT_CSV = ROOT / "docs/color-calibration/试纸宣传图RGB初始色阶.csv"

W, H = 4961, 3508  # A3 landscape at 300 dpi
BG = (244, 246, 247)
INK = (27, 33, 40)
MUTED = (91, 101, 112)
GREEN = (43, 112, 66)
GREEN_BG = (229, 241, 231)
BLUE = (29, 105, 180)
BLUE_BG = (228, 239, 250)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def median_rgb(im: Image.Image, x: int, y: int, radius: int = 9) -> tuple[int, int, int]:
    arr = np.asarray(im.convert("RGB"))
    pixels = arr[y - radius:y + radius + 1, x - radius:x + radius + 1].reshape(-1, 3)
    return tuple(int(v) for v in np.median(pixels, axis=0))


def extract_scale(filename: str, values: list[str], xs: list[int], ys: list[int]) -> list[dict]:
    im = Image.open(REF / filename)
    rows = []
    for value, x in zip(values, xs):
        colors = [median_rgb(im, x, y) for y in ys]
        rows.append({"value": value, "colors": colors})
    return rows


def build_scales() -> dict[str, dict]:
    ph_7_14_values = [str(7 + i * 0.5).removesuffix(".0") for i in range(15)]
    ph_7_14_xs = [60, 110, 158, 207, 255, 304, 352, 401, 449, 498, 546, 595, 643, 692, 740]
    ph_7_14_ys = [585, 675]
    return {
        "soft_ph": {
            "name": "软化水 pH",
            "unit": "pH",
            "source": "pH7-14.png",
            "rows": extract_scale("pH7-14.png", ph_7_14_values, ph_7_14_xs, ph_7_14_ys),
        },
        "hardness": {
            "name": "软化水硬度",
            "unit": "mg/L",
            "source": "总硬度0-20.png",
            "rows": extract_scale("总硬度0-20.png", ["0", "5", "10", "20"], [195, 330, 465, 600], [650]),
        },
        "boiler_ph": {
            "name": "炉水 pH",
            "unit": "pH",
            "source": "pH7-14.png",
            "rows": extract_scale("pH7-14.png", ph_7_14_values, ph_7_14_xs, ph_7_14_ys),
        },
        "chloride": {
            "name": "氯离子",
            "unit": "mg/L",
            "source": "氯离子0-3000.png",
            "rows": extract_scale("氯离子0-3000.png", ["0", "500", "1000", "1500", "2000", "3000"], [105, 224, 341, 461, 581, 699], [675]),
        },
        "phosphate": {
            "name": "磷酸根",
            "unit": "mg/L",
            "source": "磷酸根0-500.png",
            "rows": extract_scale("磷酸根0-500.png", ["0", "10", "25", "50", "100", "250", "500"], [90, 193, 296, 400, 503, 606, 709], [670]),
        },
        "sulfite": {
            "name": "亚硫酸根",
            "unit": "mg/L",
            "source": "亚硫酸根0-400.png",
            "rows": extract_scale("亚硫酸根0-400.png", ["0", "10", "30", "50", "100", "180", "400"], [91, 193, 295, 397, 499, 601, 699], [665]),
        },
    }


def write_csv(scales: dict[str, dict]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["项目编码", "项目", "数值", "单位", "色块", "R", "G", "B", "HEX", "来源"])
        for code, scale in scales.items():
            for row in scale["rows"]:
                for index, rgb in enumerate(row["colors"], start=1):
                    writer.writerow([
                        code, scale["name"], row["value"], scale["unit"], index,
                        *rgb, "#%02X%02X%02X" % rgb, scale["source"],
                    ])


def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill=INK) -> None:
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1] - (box[3] - box[1]) / 2), text, font=fnt, fill=fill)


def marker(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, marker_id: int) -> None:
    patterns = [0xA35C, 0x5CA3, 0xC936, 0x36C9]
    cell = size // 6
    draw.rectangle((x, y, x + cell * 6, y + cell * 6), fill="white", outline=INK, width=5)
    bits = patterns[marker_id]
    for row in range(6):
        for col in range(6):
            black = row in (0, 5) or col in (0, 5)
            if 1 <= row <= 4 and 1 <= col <= 4:
                black = bool(bits & (1 << ((row - 1) * 4 + col - 1)))
            if black:
                draw.rectangle((x + col * cell, y + row * cell, x + (col + 1) * cell, y + (row + 1) * cell), fill="black")
    centered(draw, (x + size // 2, y + size + 48), f"ID{marker_id}", font(34, True))


def scale_column(draw: ImageDraw.ImageDraw, scale: dict, x: int, y: int, width: int, max_height: int) -> None:
    rows = scale["rows"]
    count = len(rows)
    gap = 10 if count <= 7 else 5
    h = min(105, (max_height - (count - 1) * gap) // count)
    swatch_w = 84
    dual = len(rows[0]["colors"]) == 2
    for i, row in enumerate(rows):
        yy = y + i * (h + gap)
        colors = row["colors"]
        if dual:
            each = (swatch_w - 6) // 2
            draw.rectangle((x, yy, x + each, yy + h), fill=colors[0], outline=(160, 165, 170), width=2)
            draw.rectangle((x + each + 6, yy, x + each * 2 + 6, yy + h), fill=colors[1], outline=(160, 165, 170), width=2)
        else:
            draw.rectangle((x, yy, x + swatch_w, yy + h), fill=colors[0], outline=(160, 165, 170), width=2)
        draw.text((x + swatch_w + 14, yy + max(0, (h - 29) // 2)), row["value"], font=font(28), fill=INK)


def draw_board(scales: dict[str, dict]) -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((35, 35, W - 35, H - 35), radius=42, fill=(250, 250, 249), outline=(165, 172, 178), width=5)

    marker_size = 235
    marker(d, 90, 90, marker_size, 0)
    marker(d, W - 90 - marker_size, 90, marker_size, 1)
    marker(d, 90, H - 90 - marker_size - 60, marker_size, 2)
    marker(d, W - 90 - marker_size, H - 90 - marker_size - 60, marker_size, 3)

    # Color-control strips are layout references; analyte colors come from the supplied images.
    spectrum = [(230, 38, 43), (246, 142, 33), (244, 211, 42), (36, 161, 83), (28, 157, 181), (36, 92, 176), (126, 67, 160), (218, 37, 124)]
    sx0, sx1, sy0, sy1 = 430, W - 430, 95, 205
    seg = (sx1 - sx0) / len(spectrum)
    for i, c in enumerate(spectrum):
        d.rectangle((int(sx0 + i * seg), sy0, int(sx0 + (i + 1) * seg), sy1), fill=c)

    centered(d, (W // 2, 350), "炉保保水质检测操作台", font(88, True))
    centered(d, (W // 2, 438), "宣传图 RGB 提取打样版  V0.1", font(32), MUTED)

    work_x0, work_x1 = 430, W - 430
    group_y0, group_y1 = 520, 670
    total_w = work_x1 - work_x0
    slot_w = total_w // 7
    d.rounded_rectangle((work_x0, group_y0, work_x0 + slot_w * 2 - 8, group_y1), radius=18, fill=GREEN_BG, outline=GREEN, width=4)
    d.rounded_rectangle((work_x0 + slot_w * 2 + 8, group_y0, work_x1, group_y1), radius=18, fill=BLUE_BG, outline=BLUE, width=4)
    centered(d, (work_x0 + slot_w, 595), "软化水", font(52, True), GREEN)
    centered(d, (work_x0 + slot_w * 4 + slot_w // 2, 595), "炉水", font(52, True), BLUE)

    slots = [
        ("S1", "pH", "soft_ph", GREEN, GREEN_BG),
        ("S2", "硬度", "hardness", GREEN, GREEN_BG),
        ("B1", "pH", "boiler_ph", BLUE, BLUE_BG),
        ("B2", "总碱度", None, BLUE, BLUE_BG),
        ("B3", "氯离子", "chloride", BLUE, BLUE_BG),
        ("B4", "磷酸根", "phosphate", BLUE, BLUE_BG),
        ("B5", "亚硫酸根", "sulfite", BLUE, BLUE_BG),
    ]
    card_y0, card_y1 = 700, 3005
    for i, (code, name, scale_key, accent, pale) in enumerate(slots):
        x0 = work_x0 + i * slot_w + 4
        x1 = work_x0 + (i + 1) * slot_w - 8
        d.rounded_rectangle((x0, card_y0, x1, card_y1), radius=18, fill=(249, 250, 250), outline=accent, width=3)
        d.rounded_rectangle((x0 + 20, card_y0 + 20, x0 + 118, card_y0 + 88), radius=10, fill=accent)
        centered(d, (x0 + 69, card_y0 + 54), code, font(38, True), "white")
        centered(d, ((x0 + x1) // 2, card_y0 + 145), name, font(45, True))

        tag_x, tag_y, tag_size = x0 + 36, card_y0 + 230, 105
        marker(d, tag_x, tag_y, tag_size, i % 4)
        centered(d, (tag_x + tag_size // 2, tag_y + tag_size + 20), "↑", font(42, True), accent)

        tray_x0, tray_x1 = x0 + 35, x0 + 185
        tray_y0, tray_y1 = card_y0 + 520, card_y1 - 120
        d.rounded_rectangle((tray_x0, tray_y0, tray_x1, tray_y1), radius=16, fill=(164, 169, 170), outline=(100, 105, 106), width=4)
        d.rounded_rectangle((tray_x0 + 35, tray_y0 + 40, tray_x1 - 35, tray_y1 - 45), radius=10, fill=(222, 225, 223), outline=(125, 130, 130), width=3)
        d.rectangle((tray_x0 + 49, tray_y1 - 220, tray_x1 - 49, tray_y1 - 80), outline=accent, width=5)
        centered(d, ((tray_x0 + tray_x1) // 2, tray_y1 - 32), "显色端", font(24, True))

        scale_x = x0 + 220
        scale_y = card_y0 + 525
        if scale_key:
            scale_column(d, scales[scale_key], scale_x, scale_y, x1 - scale_x - 20, tray_y1 - scale_y - 10)
            unit = scales[scale_key]["unit"]
            centered(d, ((scale_x + x1) // 2, tray_y1 + 20), unit, font(26), MUTED)
        else:
            d.rounded_rectangle((scale_x, scale_y, x1 - 25, scale_y + 520), radius=14, fill=(238, 241, 243), outline=(155, 163, 170), width=3)
            centered(d, ((scale_x + x1 - 25) // 2, scale_y + 210), "待提供", font(33, True), MUTED)
            centered(d, ((scale_x + x1 - 25) // 2, scale_y + 265), "总碱度色卡", font(28), MUTED)
            centered(d, ((scale_x + x1 - 25) // 2, scale_y + 345), "不编造颜色", font(25), (160, 70, 70))

    # Bottom color controls and version block.
    swatches = [(24, 24, 24), (80, 80, 80), (145, 145, 145), (205, 205, 205), (245, 245, 245),
                (220, 38, 45), (32, 160, 80), (35, 88, 180), (20, 170, 195), (215, 40, 145), (245, 205, 25)]
    bx, by, bw, bh = 435, 3140, 245, 125
    for c in swatches:
        d.rectangle((bx, by, bx + bw, by + bh), fill=c, outline=(120, 125, 130), width=2)
        bx += bw + 12
    d.rounded_rectangle((W - 1430, 3095, W - 430, 3335), radius=14, fill=(240, 243, 245), outline=(115, 125, 134), width=3)
    d.text((W - 1390, 3130), "板卡编号：LBB-RGB-V01", font=font(31, True), fill=INK)
    d.text((W - 1390, 3185), "版本：V0.1   日期：2026-09-04", font=font(28), fill=INK)
    d.text((W - 1390, 3240), "用途：结构与颜色初步打样", font=font(28), fill=INK)
    d.text((430, 3362), "注意：色阶 RGB 取自用户提供的宣传图片，仅供样机；正式识别与印刷必须以标准液、真实试纸和实体测色结果重新标定。", font=font(27), fill=(135, 57, 57))

    OUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT_IMAGE, dpi=(300, 300), optimize=True)


def main() -> None:
    scales = build_scales()
    write_csv(scales)
    draw_board(scales)
    print(OUT_IMAGE)
    print(OUT_CSV)


if __name__ == "__main__":
    main()
