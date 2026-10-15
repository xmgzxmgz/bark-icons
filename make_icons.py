#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「圆形适配」的 Bark 通知图标。

问题: iOS 把通知图标裁成正圆, Bark 客户端还会把方形图按「完整放入」缩小,
     导致直接用 Apple emoji PNG 时, 内容在圆形里又小又空。

做法: 学 App 图标 —— 实心彩色圆底填满画布, emoji 缩小居中贴在圆心。
     圆形裁切后得到完整的实心圆, 视觉饱满; 底色按领域区分, 一眼可辨。

用法:
  python3 make_icons.py                 # 生成全部图标到 assets/icons/
  python3 make_icons.py --out /tmp/ico  # 指定输出目录
  python3 make_icons.py --emoji-base https://...  # 换 emoji 源

输出文件名 = <code>.png, 例如 1f916.png
"""

import argparse
import io
import math
import os
import urllib.request
from PIL import Image, ImageDraw

# 画布: 2x Retina 清晰度
SIZE = 320
# emoji 外径占圆底直径的比例 (App 图标风格取 0.62~0.70, 取 0.66)
EMOJI_RATIO = 0.66
# emoji 源 (Cloudflare 节点)
EMOJI_BASE = "https://testingcf.jsdelivr.net/gh/iamcal/emoji-data@master/img-apple-160"

# 领域图标: 代码 -> 圆底色
ICONS = {
    # 资讯线
    "1f916":       "#B04356",   # 🤖 AI · 石榴红
    "1f5a5-fe0f":  "#3E4A5A",   # 🖥️ 数据中心 · 石墨蓝
    "26a1":        "#8A9A6B",   # ⚡ 绿电 · 鼠尾草绿
    "1f4f0":       "#B04356",   # 📰 合并版 · 石榴红
    # 问候线 (随天气换)
    "1f305":       "#E8946A",   # 🌅 日出 · 暖橙
    "2600-fe0f":   "#EFA94B",   # ☀️ 晴 · 金
    "2601-fe0f":   "#8494A8",   # ☁️ 阴 · 灰蓝
    "1f327-fe0f":  "#5B7A9D",   # 🌧️ 雨 · 雨蓝
    "26c8-fe0f":   "#46536B",   # ⛈️ 雷雨 · 暗蓝
    "1f328-fe0f":  "#92A8C0",   # 🌨️ 雪 · 雪蓝
    "1f32b-fe0f":  "#9AA5A0",   # 🌫️ 雾 · 灰绿
}


def hex_rgba(s, alpha=255):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def fetch_emoji(code, base):
    url = f"{base}/{code}.png"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGBA")


def trim(im):
    """裁掉透明边距。"""
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def circle_bg(color, size):
    """抗锯齿实心圆: 4x 超采样画圆再缩小。"""
    ss = size * 4
    im = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, ss - 1, ss - 1), fill=hex_rgba(color))
    # 极淡的内高光, 让圆有一点点立体感而非死板纯色
    hi = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    dh = ImageDraw.Draw(hi)
    dh.ellipse((ss * 0.08, ss * 0.04, ss * 0.92, ss * 0.88),
               fill=(255, 255, 255, 26))
    im = Image.alpha_composite(im, hi)
    return im.resize((size, size), Image.LANCZOS)


def make_icon(code, color, emoji_base):
    emoji = trim(fetch_emoji(code, emoji_base))
    # emoji 外径 = 圆底直径 * 比例
    target = int(SIZE * EMOJI_RATIO)
    w, h = emoji.size
    scale = target / max(w, h)
    emoji = emoji.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                         Image.LANCZOS)

    canvas = circle_bg(color, SIZE)
    x = (SIZE - emoji.width) // 2
    y = (SIZE - emoji.height) // 2
    canvas.alpha_composite(emoji, (x, y))
    return canvas


def main():
    global EMOJI_RATIO
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__),
                                                  "..", "assets", "icons"))
    ap.add_argument("--emoji-base", default=EMOJI_BASE)
    ap.add_argument("--only", default="", help="只生成指定代码, 逗号分隔")
    ap.add_argument("--ratio", type=float, default=EMOJI_RATIO)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    EMOJI_RATIO = args.ratio

    codes = ([c.strip() for c in args.only.split(",") if c.strip()]
             if args.only else list(ICONS))
    for code in codes:
        color = ICONS.get(code, "#B04356")
        try:
            im = make_icon(code, color, args.emoji_base)
        except Exception as e:  # noqa: BLE001
            print(f"  [失败] {code}: {e}")
            continue
        path = os.path.join(out, f"{code}.png")
        im.save(path, "PNG", optimize=True)
        kb = os.path.getsize(path) / 1024
        print(f"  {code}.png  底色 {color}  {kb:.1f} KB")
    print(f"完成, 输出目录 {out}")


if __name__ == "__main__":
    main()
