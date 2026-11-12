#!/usr/bin/env python3
"""
lint_svg.py — 检查 SVG 是否能在 GitHub README（<img> 引用）中正常显示。

用法:
    python3 lint_svg.py <file-or-dir> [...] [--strict]

规则（error 必须修复；warning 需在交付说明中解释）:
    E001 包含 <script> 或 on* 事件属性
    E002 使用 <foreignObject>
    E003 引用远程资源（http/https 的 href、@import、url()）
    E004 缺少 viewBox
    E005 XML 无法解析
    W101 缺少 <title>（无障碍）
    W102 文件超过 200KB（含位图时 1MB）
    W103 使用了未内嵌的自定义字体（font-family 首选不在系统字体白名单）
    W104 有动画但缺少 prefers-reduced-motion 降级
    W105 文字距画布边缘小于 48px（粗略检测 x/y 属性）
    W106 SVG 内 <a> 链接（在 GitHub 中不可点击）
    W107 按 GitHub 实际显示宽度换算后，文字有效字号 < --min-px（默认 14px）
         装饰性微文字可加 data-decorative="true" 跳过检查

--display-width: GitHub 正文栏宽度（默认 830）。显示比例 = min(1, display-width / viewBox 宽)。

--strict: warning 也视为失败（退出码 1）。
依赖: 仅 Python 标准库。
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "{http://www.w3.org/2000/svg}"

SYSTEM_FONTS = {
    "-apple-system", "blinkmacsystemfont", "segoe ui", "noto sans", "helvetica", "helvetica neue",
    "arial", "sans-serif", "serif", "monospace", "ui-monospace", "sfmono-regular", "sf mono",
    "menlo", "consolas", "liberation mono", "georgia", "times new roman", "pingfang sc",
    "hiragino sans gb", "microsoft yahei", "noto sans cjk sc", "songti sc", "iowan old style",
    "system-ui", "courier new",
}

REMOTE_RE = re.compile(r"""(?:href\s*=\s*["']https?://|@import|url\(\s*["']?https?://)""", re.I)
FONT_FAMILY_RE = re.compile(r"font-family\s*[:=]\s*([^;\"}>]+)", re.I)


class Report:
    def __init__(self, path: Path):
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def e(self, code: str, msg: str):
        self.errors.append(f"{code} {msg}")

    def w(self, code: str, msg: str):
        self.warnings.append(f"{code} {msg}")


def local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([\d.]+)(?:px)?", re.I)
CSS_RULE_RE = re.compile(r"([.#]?[\w-]+)\s*{([^}]*)}")


def css_sizes(raw: str) -> dict[str, float]:
    """粗略解析 <style> 中 .class{font-size:N} 规则。"""
    out: dict[str, float] = {}
    for blk in re.findall(r"<style[^>]*>(.*?)</style>", raw, re.S | re.I):
        for sel, body in CSS_RULE_RE.findall(blk):
            m = FONT_SIZE_RE.search(body)
            if m and sel.startswith("."):
                out[sel[1:]] = float(m.group(1))
    return out


def font_size_of(el, parents: dict, classes: dict[str, float]) -> float | None:
    cur = el
    while cur is not None:
        if cur.get("data-decorative") == "true":
            return None
        fs = cur.get("font-size")
        if fs:
            try:
                return float(fs.replace("px", ""))
            except ValueError:
                return None
        m = FONT_SIZE_RE.search(cur.get("style", ""))
        if m:
            return float(m.group(1))
        for c in (cur.get("class") or "").split():
            if c in classes:
                return classes[c]
        cur = parents.get(cur)
    return 16.0  # SVG 默认


def lint(path: Path, display_width: float = 830, min_px: float = 14) -> Report:
    r = Report(path)
    raw = path.read_text(encoding="utf-8", errors="ignore")
    size = path.stat().st_size

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as ex:
        r.e("E005", f"XML 解析失败: {ex}")
        return r

    has_raster = "data:image/" in raw
    limit = 1_000_000 if has_raster else 200_000
    if size > limit:
        r.w("W102", f"文件 {size // 1024}KB，超过建议上限 {limit // 1024}KB")

    if root.get("viewBox") is None:
        r.e("E004", "根元素缺少 viewBox，无法自适应宽度")

    vb = (root.get("viewBox") or "").split()
    vb_w = float(vb[2]) if len(vb) == 4 else None
    vb_h = float(vb[3]) if len(vb) == 4 else None

    scale = min(1.0, display_width / vb_w) if vb_w else 1.0
    parents = {c: p for p in root.iter() for c in p}
    classes = css_sizes(raw)
    small: list[str] = []
    for el in root.iter():
        if local(el.tag) not in ("text", "tspan"):
            continue
        txt = "".join(el.itertext()).strip()
        if not txt or (local(el.tag) == "text" and len(el) and not (el.text or "").strip()):
            continue
        fs = font_size_of(el, parents, classes)
        if fs is None:
            continue
        # 粗略考虑祖先 transform scale(...)
        k, cur = 1.0, el
        while cur is not None:
            m = re.search(r"scale\(\s*([\d.]+)", cur.get("transform", ""))
            if m:
                k *= float(m.group(1))
            cur = parents.get(cur)
        eff = fs * k * scale
        if eff < min_px:
            small.append(f"{eff:.1f}px「{txt[:18]}」")
    if small:
        r.w("W107", f"显示宽度 {display_width:.0f}px 下（比例 {scale:.2f}）有 {len(small)} 处文字 < {min_px:.0f}px："
                    + "，".join(small[:6]) + (" …" if len(small) > 6 else ""))

    has_title = False
    for el in root.iter():
        name = local(el.tag)
        if name == "script":
            r.e("E001", "包含 <script>，GitHub 不会执行")
        if name == "foreignObject":
            r.e("E002", "使用 <foreignObject>，渲染不稳定，请改用原生 SVG 元素")
        if name == "title":
            has_title = True
        if name == "a":
            r.w("W106", "SVG 内 <a> 在 GitHub 中不可点击，请在 Markdown 外层包裹链接")
        for attr in el.attrib:
            if local(attr).lower().startswith("on"):
                r.e("E001", f"<{name}> 带有事件属性 {local(attr)}")
        if name == "text" and vb_w and vb_h:
            try:
                x = float(el.get("x", "nan"))
                y = float(el.get("y", "nan"))
            except ValueError:
                continue
            anchor = el.get("text-anchor", "start")
            # 仅检查顶层（无 transform 祖先难以判断，粗略处理）
            if anchor == "start" and x == x and x < 48:
                r.w("W105", f"<text> x={x} 距左边缘 < 48px：{(el.text or '').strip()[:20]}")
            if anchor == "end" and x == x and vb_w - x < 48:
                r.w("W105", f"<text> x={x} 距右边缘 < 48px：{(el.text or '').strip()[:20]}")
            if y == y and (y < 40 or vb_h - y < 24):
                r.w("W105", f"<text> y={y} 距上下边缘过近：{(el.text or '').strip()[:20]}")

    if not has_title:
        r.w("W101", "缺少 <title>，屏幕阅读器无法描述图片")

    for m in REMOTE_RE.finditer(raw):
        r.e("E003", f"引用远程资源：{raw[m.start():m.start() + 60]!r}")

    embedded_fonts = set(f.lower() for f in re.findall(r"@font-face\s*{[^}]*font-family\s*:\s*['\"]?([^;'\"]+)", raw, re.I))
    for m in FONT_FAMILY_RE.finditer(raw):
        families = [f.strip().strip("'\"").lower() for f in m.group(1).split(",")]
        if not families or not families[0]:
            continue
        first = families[0]
        if first.startswith("var("):
            continue
        if first not in SYSTEM_FONTS and first not in embedded_fonts:
            fallback_ok = any(f in SYSTEM_FONTS for f in families[1:])
            hint = "（有系统字体回退）" if fallback_ok else "（且无系统字体回退）"
            r.w("W103", f"首选字体 '{first}' 未内嵌，访客可能看到回退字体{hint}；正式产出建议文字转路径")

    animated = "@keyframes" in raw or re.search(r"<animate|<animateTransform|<animateMotion", raw)
    if animated and "prefers-reduced-motion" not in raw:
        r.w("W104", "包含动画但没有 prefers-reduced-motion 降级")

    # 去重
    r.errors = list(dict.fromkeys(r.errors))
    r.warnings = list(dict.fromkeys(r.warnings))
    return r


def collect(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        if p.is_dir():
            out += sorted(p.rglob("*.svg"))
        elif p.suffix.lower() == ".svg":
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub README SVG 兼容性检查")
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--strict", action="store_true", help="warning 也视为失败")
    ap.add_argument("--display-width", type=float, default=830, help="GitHub 正文栏显示宽度（默认 830）")
    ap.add_argument("--min-px", type=float, default=14, help="有效字号下限（默认 14）")
    args = ap.parse_args()

    files = collect(args.paths)
    if not files:
        print("未找到 SVG 文件", file=sys.stderr)
        return 2

    total_e = total_w = 0
    for f in files:
        rep = lint(f, args.display_width, args.min_px)
        total_e += len(rep.errors)
        total_w += len(rep.warnings)
        status = "✗" if rep.errors else ("!" if rep.warnings else "✓")
        print(f"{status} {f}")
        for e in rep.errors:
            print(f"    error   {e}")
        for w in rep.warnings:
            print(f"    warning {w}")

    print(f"\n{len(files)} 个文件，{total_e} error，{total_w} warning")
    if total_e or (args.strict and total_w):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
