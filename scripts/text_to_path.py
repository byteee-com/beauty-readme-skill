#!/usr/bin/env python3
"""
text_to_path.py — 把 SVG 中的 <text> 转成 <path>，让字体在 GitHub 上各平台一致。

用法:
    python3 text_to_path.py <input.svg> --font <font.ttf|otf> [--font-map map.json] [-o output.svg]

说明:
    - 默认输出到 <input>.svg，并把原文件备份为 <input>.src.svg（可编辑源文件）。
    - --font 为默认字体；--font-map 可按 class 或 font-family 指定不同字体:
        {"title": "fonts/Display-Bold.ttf", "mono": "fonts/JetBrainsMono-Regular.ttf"}
      键先按元素 class 匹配，再按 font-family 首项匹配（不区分大小写）。
    - 支持: x / y / text-anchor / font-size / letter-spacing（属性或 <style> 中的类规则）、
      <tspan> 的内联文字（继承父级位置顺序排列，支持 dx）。
    - 不支持: 文字沿路径、竖排、复杂 OpenType 特性（连字、上下文替换）。
      遇到不支持的情况会保留原 <text> 并打印警告。
    - 转换后保留 <title>/<desc>，并在每个 <g> 上加 aria-label 保存原文字。

依赖: fonttools（pip install fonttools）
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError:
    print("需要 fonttools：pip install fonttools", file=sys.stderr)
    sys.exit(2)

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
Q = lambda t: f"{{{SVG_NS}}}{t}"  # noqa: E731


# ------------------------------------------------------------ CSS (minimal)
def parse_class_rules(root: ET.Element) -> dict[str, dict[str, str]]:
    """从 <style> 中解析简单的 .class { prop: value } 规则。"""
    rules: dict[str, dict[str, str]] = {}
    for st in root.iter(Q("style")):
        css = re.sub(r"/\*.*?\*/", "", st.text or "", flags=re.S)
        css = re.sub(r"@media[^{]*{(?:[^{}]*{[^}]*})*[^}]*}", "", css)  # 忽略媒体查询
        for sel, body in re.findall(r"([^{}]+){([^}]*)}", css):
            props = dict((k.strip().lower(), v.strip()) for k, v in
                         (p.split(":", 1) for p in body.split(";") if ":" in p))
            for s in sel.split(","):
                s = s.strip()
                for cls in re.findall(r"^\.([\w-]+)$", s):
                    rules.setdefault(cls, {}).update(props)
    return rules


def style_of(el: ET.Element, rules: dict, parent: dict | None = None) -> dict[str, str]:
    st = dict(parent or {})
    for cls in (el.get("class") or "").split():
        st.update(rules.get(cls, {}))
    for k in ("font-size", "letter-spacing", "text-anchor", "font-family", "font-weight"):
        if el.get(k):
            st[k] = el.get(k)
    if el.get("style"):
        for p in el.get("style").split(";"):
            if ":" in p:
                k, v = p.split(":", 1)
                st[k.strip().lower()] = v.strip()
    return st


def num(v: str | None, default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(r"-?[\d.]+", str(v))
    return float(m.group()) if m else default


# ------------------------------------------------------------ fonts
class FontCache:
    def __init__(self, default: Path, mapping: dict[str, str], base: Path):
        self.default = default
        self.mapping = {k.lower(): (base / v) for k, v in mapping.items()}
        self._cache: dict[Path, TTFont] = {}

    def get(self, classes: list[str], family: str | None) -> TTFont:
        path = self.default
        for c in classes:
            if c.lower() in self.mapping:
                path = self.mapping[c.lower()]
                break
        else:
            if family:
                first = family.split(",")[0].strip().strip("'\"").lower()
                path = self.mapping.get(first, self.default)
        if path not in self._cache:
            self._cache[path] = TTFont(str(path))
        return self._cache[path]


def text_to_path_d(font: TTFont, text: str, x: float, y: float, size: float,
                   letter_spacing: float) -> tuple[str, float]:
    """返回 (path d, advance 宽度)。"""
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    scale = size / upm
    hmtx = font["hmtx"]
    kern = None  # 简化：不处理 GPOS 字距
    d_parts: list[str] = []
    cursor = 0.0
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            gname = ".notdef"
        adv = hmtx[gname][0] if gname in hmtx.metrics else upm // 2
        pen = SVGPathPen(gs)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x + cursor, y))
        try:
            gs[gname].draw(tpen)
        except KeyError:
            pass
        cmds = pen.getCommands()
        if cmds:
            d_parts.append(cmds)
        cursor += adv * scale + letter_spacing
    _ = kern
    return " ".join(d_parts), cursor - letter_spacing


# ------------------------------------------------------------ main conversion
def convert(svg_path: Path, fonts: FontCache) -> tuple[ET.ElementTree, int, int]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    rules = parse_class_rules(root)
    parent_map = {c: p for p in root.iter() for c in p}
    converted = skipped = 0

    def inherited(el: ET.Element) -> dict:
        chain = []
        cur = el
        while cur in parent_map:
            cur = parent_map[cur]
            chain.append(cur)
        st: dict = {}
        for anc in reversed(chain):
            st = style_of(anc, rules, st)
        return st

    for text_el in list(root.iter(Q("text"))):
        if text_el.find(Q("textPath")) is not None or text_el.get("writing-mode"):
            print(f"[skip] 不支持 textPath / 竖排: {''.join(text_el.itertext())[:30]}", file=sys.stderr)
            skipped += 1
            continue
        base_style = style_of(text_el, rules, inherited(text_el))
        x0 = num(text_el.get("x"))
        y0 = num(text_el.get("y"))
        anchor = base_style.get("text-anchor", "start")

        # 收集片段：(文字, style, dx)
        segments: list[tuple[str, dict, float, list[str]]] = []
        classes = (text_el.get("class") or "").split()
        if text_el.text and text_el.text.strip("\n"):
            segments.append((text_el.text, base_style, 0.0, classes))
        for ts in text_el:
            if ts.tag != Q("tspan"):
                continue
            if ts.get("x") or ts.get("y"):
                print("[warn] tspan 带绝对 x/y，按顺序排列处理", file=sys.stderr)
            ts_style = style_of(ts, rules, base_style)
            ts_classes = classes + (ts.get("class") or "").split()
            segments.append((ts.text or "", ts_style, num(ts.get("dx")), ts_classes))
            if ts.tail and ts.tail.strip("\n"):
                segments.append((ts.tail, base_style, 0.0, classes))

        # 第一遍测量宽度
        pieces = []
        total = 0.0
        for txt, st, dx, cls in segments:
            font = fonts.get(cls, st.get("font-family"))
            size = num(st.get("font-size"), 16)
            ls = num(st.get("letter-spacing"), 0)
            _, w = text_to_path_d(font, txt, 0, 0, size, ls)
            pieces.append((txt, st, dx, cls, font, size, ls, w))
            total += dx + w
        offset = {"start": 0, "middle": -total / 2, "end": -total}.get(anchor, 0)

        g = ET.Element(Q("g"))
        g.set("aria-label", "".join(text_el.itertext()).strip())
        for attr in ("class", "transform", "opacity", "fill"):
            if text_el.get(attr):
                g.set(attr, text_el.get(attr))
        cursor = x0 + offset
        for txt, st, dx, cls, font, size, ls, w in pieces:
            cursor += dx
            d, _ = text_to_path_d(font, txt, cursor, y0, size, ls)
            if d:
                p = ET.SubElement(g, Q("path"))
                p.set("d", d)
                seg_cls = " ".join(c for c in cls if c not in (text_el.get("class") or "").split())
                if seg_cls:
                    p.set("class", seg_cls)
            cursor += w

        parent = parent_map[text_el]
        idx = list(parent).index(text_el)
        g.tail = text_el.tail
        parent.remove(text_el)
        parent.insert(idx, g)
        converted += 1

    return tree, converted, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 文字转路径（GitHub 字体一致性）")
    ap.add_argument("input", type=Path)
    ap.add_argument("--font", type=Path, required=True, help="默认字体文件 .ttf/.otf")
    ap.add_argument("--font-map", type=Path, help="JSON：class 或 font-family → 字体文件")
    ap.add_argument("-o", "--output", type=Path, help="输出路径（默认覆盖并备份为 .src.svg）")
    args = ap.parse_args()

    mapping = json.loads(args.font_map.read_text(encoding="utf-8")) if args.font_map else {}
    base = args.font_map.parent if args.font_map else Path.cwd()
    fonts = FontCache(args.font, mapping, base)

    tree, converted, skipped = convert(args.input, fonts)

    out = args.output
    if out is None:
        src_backup = args.input.with_suffix(".src.svg")
        if not src_backup.exists():
            shutil.copyfile(args.input, src_backup)
            print(f"源文件已备份: {src_backup}")
        out = args.input
    tree.write(out, encoding="utf-8", xml_declaration=False)
    print(f"已转换 {converted} 段文字，跳过 {skipped} 段 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
