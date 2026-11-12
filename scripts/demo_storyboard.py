#!/usr/bin/env python3
"""确定性演示分镜：把真实提示词和输出字段生成动画 SVG（浅 / 深）与 GIF。

不录屏、不用 AI 生成：画面里的每个字都来自分镜文件，分镜文件的内容来自
项目自己的 README 和文档。提示词改了，改分镜再重跑即可。

子命令:
  extract README.md [-o storyboard.json]
      从 README 的代码块抽出提示词，生成分镜草稿。Agent 再按项目文档补全
      每段的 reply（字段名称和顺序必须来自源码或文档）。

  build storyboard.json --out DIR [--fonts-dir DIR ...] [--gif] [--gif-width 960] [--fps 10]
        [--gif-modes light,dark] [--gif-start begin|final] [--gif-hold 300]
      每个 scene 输出 <id>{suffix}-light.svg / -dark.svg（只播一次的 CSS 动画，
      静态状态 = 最终帧，带 prefers-reduced-motion 降级），作为源文件和静态兜底。
      --gif 时另出 gif/<id>{suffix}-<mode>.gif：无限循环，README 演示的主格式。
      --gif-start begin（默认）从打字开始播；final 让首帧即最终帧，适合只显示首帧的平台。

分镜格式（JSON）:
{
  "project": "my-tool", "suffix": "", "label": "ILLUSTRATIVE · EXAMPLE VALUES",
  "demo": "DEMO", "you": "YOU", "agent": "AGENT", "label_tracking": 1.5,
  "fonts": {"mono": "JBM-Regular.ttf", "monob": "JBM-Bold.ttf", "head": "Oswald-Bold.ttf",
            "headm": "Oswald-Medium.ttf", "fallback": [...], "fallback_bold": [...]},
  "themes": {"light": {"paper","ink","muted","acc","hair","bubble","edge","shadow","gif_bg"},
             "dark": {...}},
  "scenes": [{
    "id": "preview", "title": "PREVIEW", "prompt": "…", "summary": "…（写进 <desc>）",
    "reply": [
      {"kind": "line", "k": "LABEL", "v": "value", "tone": "ink|muted|acc", "bold": false},
      {"kind": "grid", "cols": 4, "cells": [["LABEL", "value"], …]},
      {"kind": "rule"}
    ],
    "footer": {"k": "NEXT", "v": "Confirm …", "command": true, "stamp": ["AWAITING", "CONFIRMATION"]}
  }]
}

依赖：fonttools；GIF 需要 rsvg-convert 或 resvg，以及 ImageMagick（magick）。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

W = 1280
CARD = 24
P, R = 72, 1208          # 内容左右边界
VX = P + 250             # line 类条目的值所在列
STEP = 0.22              # 条目之间的出现间隔（秒）

CJK = "\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f"
TOKEN = re.compile(rf"[{CJK}]|[^\s{CJK}]+\s*|\s+")


def esc(s: str) -> str:
    return escape(s, quote=True)


# --------------------------------------------------------------------------- fonts
class Fonts:
    def __init__(self, spec: dict, dirs: list[Path]):
        self.spec, self.dirs, self.cache = spec, dirs, {}

    def load(self, name: str):
        if name not in self.cache:
            p = Path(name)
            cands = [p] if p.is_absolute() else [d / name for d in self.dirs] + [p]
            for c in cands:
                if c.exists():
                    f = TTFont(str(c))
                    self.cache[name] = (f.getBestCmap(), f.getGlyphSet(), f["head"].unitsPerEm)
                    break
            else:
                raise SystemExit(f"找不到字体 {name}，请用 --fonts-dir 指定所在目录")
        return self.cache[name]

    def glyph(self, role: str, ch: str):
        bold = role in ("monob", "head", "headm")
        chain = [self.spec[role]] + list(self.spec.get("fallback_bold" if bold else "fallback", []))
        for name in chain:
            cmap, gs, upm = self.load(name)
            g = cmap.get(ord(ch))
            if g:
                return name, g, gs[g].width, upm
        raise SystemExit(f"字符 {ch!r} 不在 {role} 及其回退字体中")


class Doc:
    """收集用到的字形（每个字形只定义一次，用 <use> 引用），并负责排字。"""

    def __init__(self, fonts: Fonts):
        self.fonts, self.defs = fonts, {}

    def gid(self, fname: str, gname: str):
        key = (fname, gname)
        if key not in self.defs:
            _, gs, _ = self.fonts.load(fname)
            pen = SVGPathPen(gs, ntos=lambda n: str(round(n)))
            gs[gname].draw(pen)
            self.defs[key] = (f"g{len(self.defs)}", pen.getCommands())
        return self.defs[key]

    def measure(self, s: str, role: str, size: float, ls: float = 0) -> float:
        w = 0.0
        for ch in s:
            _, _, adv, upm = self.fonts.glyph(role, ch)
            w += adv * size / upm
        return w + ls * max(len(s) - 1, 0)

    def text(self, x, y, s, role, size, fill, anchor="start", ls=0.0):
        w = self.measure(s, role, size, ls)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        runs, cx = [], x
        for ch in s:
            fname, g, adv, upm = self.fonts.glyph(role, ch)
            k = size / upm
            if not runs or runs[-1][0] != fname:
                runs.append([fname, k, cx, []])
            gid, d = self.gid(fname, g)
            if d:
                runs[-1][3].append((gid, (cx - runs[-1][2]) / k))
            cx += adv * k + ls
        parts = []
        for _, k, x0, uses in runs:
            if uses:
                u = "".join(f'<use xlink:href="#{g}" x="{xo:.0f}"/>' if round(xo) else f'<use xlink:href="#{g}"/>' for g, xo in uses)
                parts.append(f'<g transform="matrix({k:.5g} 0 0 {-k:.5g} {x0:.1f} {y:.1f})">{u}</g>')
        return f'<g fill="{fill}" aria-label="{esc(s)}">{"".join(parts)}</g>', w

    def wrap(self, s, role, size, maxw, ls=0.0):
        lines, cur = [], ""
        for t in TOKEN.findall(s):
            if cur.strip() and self.measure((cur + t).rstrip(), role, size, ls) > maxw:
                lines.append(cur.rstrip())
                cur = t.lstrip()
            else:
                cur += t
        if cur.strip():
            lines.append(cur.rstrip())
        return lines


# --------------------------------------------------------------------------- layout
def layout(doc: Doc, sb: dict, scene: dict, idx: int, total: int, th: dict):
    """返回 (items, height)。item = {svg, anim}；anim 为 None 表示静态。"""
    items, tr = [], sb.get("label_tracking", 1.5)
    t = 0.3

    def add(svg, anim=None):
        items.append({"svg": svg, "anim": anim})

    def fade(start):
        return {"kind": "fade", "start": round(start, 3), "dur": 0.3}

    # header
    s, w = doc.text(P, 92, sb["project"], "head", 28, th["ink"], ls=1)
    add(s)
    s, _ = doc.text(P + w + 24, 91, f'{sb.get("demo", "DEMO")} {idx}/{total} · {scene["title"]}', "mono", 22, th["muted"], ls=tr)
    add(s)
    s, _ = doc.text(R, 91, sb.get("label", "ILLUSTRATIVE · EXAMPLE VALUES"), "mono", 22, th["acc"], "end", ls=tr)
    add(s)
    add(f'<rect x="{P}" y="112" width="{R - P}" height="3" fill="{th["ink"]}"/>')

    # prompt bubble (typed line by line)
    y = 166
    s, _ = doc.text(P, y, sb.get("you", "YOU"), "mono", 22, th["muted"], ls=tr)
    add(s)
    top = y + 18
    lines = doc.wrap(scene["prompt"], "monob", 26, R - P - 100)
    h = 76 + (len(lines) - 1) * 40
    add(f'<rect x="{P}" y="{top}" width="{R - P}" height="{h}" rx="10" fill="{th["bubble"]}" stroke="{th["edge"]}" stroke-width="2"/>')
    s, _ = doc.text(P + 26, top + 50, ">", "monob", 26, th["acc"])
    add(s)
    for i, ln in enumerate(lines):
        by = top + 50 + i * 40
        s, lw = doc.text(P + 62, by, ln, "monob", 26, th["ink"])
        add(s)
        dur = round(max(0.25, len(ln) * 0.009), 3)
        x0, x1 = P + 58, P + 62 + lw + 6
        add(f'<rect x="{x0}" y="{by - 29}" width="{x1 - x0:.0f}" height="38" fill="{th["bubble"]}" transform="scale(0 1)"/>',
            {"kind": "wipe", "start": round(t, 3), "dur": dur, "n": max(4, len(ln) // 2), "ox": round(x1), "oy": by})
        t += dur
    y = top + h

    # agent reply
    t += 0.35
    y += 56
    s, _ = doc.text(P, y, sb.get("agent", "AGENT"), "mono", 22, th["muted"], ls=tr)
    add(s, fade(t))
    t += 0.15
    y += 20
    for it in scene.get("reply", []):
        kind = it.get("kind", "line")
        if kind == "line":
            role = "monob" if it.get("bold") else "mono"
            size = it.get("size", 24)
            vl = doc.wrap(it["v"], role, size, R - VX)
            g = [doc.text(P, y + 28, it["k"], "mono", 22, th["muted"], ls=tr)[0]]
            for i, ln in enumerate(vl):
                g.append(doc.text(VX, y + 28 + i * 34, ln, role, size, th[it.get("tone", "ink")])[0])
            add("".join(g), fade(t))
            t += STEP
            y += 52 + (len(vl) - 1) * 34
        elif kind == "grid":
            cols = it.get("cols", 4)
            cw = (R - P) / cols
            cells = it["cells"]
            for r in range(0, len(cells), cols):
                for j, (k, v) in enumerate(cells[r:r + cols]):
                    x = P + j * cw + (20 if j else 0)
                    g = []
                    if j:
                        g.append(f'<rect x="{P + j * cw:.0f}" y="{y + 8}" width="2" height="70" fill="{th["hair"]}"/>')
                    g.append(doc.text(x, y + 32, k, "mono", 22, th["muted"], ls=tr)[0])
                    vs, vw = doc.text(x, y + 70, v, "monob", 26, th["ink"])
                    if vw > cw - 28:
                        print(f"[warn] {scene['id']}: “{v}” 超出栏宽 {vw:.0f}>{cw - 28:.0f}", file=sys.stderr)
                    g.append(vs)
                    add("".join(g), fade(t + j * 0.06))
                t += STEP
                y += 94
        elif kind == "rule":
            add(f'<rect x="{P}" y="{y + 12}" width="{R - P}" height="2" fill="{th["hair"]}"/>')
            y += 28

    f = scene.get("footer")
    if f:
        y += 10
        add(f'<rect x="{P}" y="{y}" width="{R - P}" height="3" fill="{th["ink"]}"/>', fade(t))
        y += 20
        g = [doc.text(P, y + 44, f["k"], "mono", 22, th["muted"], ls=tr)[0]]
        if f.get("command"):
            vs, vw = doc.text(VX + 20, y + 44, f["v"], "monob", 26, th["acc"])
            g.append(f'<rect x="{VX}" y="{y + 12}" width="{vw + 40:.0f}" height="46" rx="6" fill="none" stroke="{th["acc"]}" stroke-width="2"/>')
        else:
            vs, vw = doc.text(VX, y + 44, f["v"], "monob", 26, th["ink"])
        g.append(vs)
        add("".join(g), fade(t))
        t += STEP + 0.15
        if f.get("stamp"):
            cx, cy = R - 160, y + 40
            l1, l2 = (f["stamp"] + [""])[:2]
            s1 = 50 * min(1, 250 / doc.measure(l1, "head", 50, 4))
            st = [f'<g transform="rotate(-7 {cx} {cy})">',
                  f'<rect x="{cx - 150}" y="{cy - 58}" width="300" height="116" rx="10" fill="{th["paper"]}" fill-opacity="0.6" stroke="{th["acc"]}" stroke-width="5"/>',
                  f'<rect x="{cx - 140}" y="{cy - 48}" width="280" height="96" rx="6" fill="none" stroke="{th["acc"]}" stroke-width="2"/>',
                  doc.text(cx, cy + (2 if l2 else 18), l1, "head", round(s1, 1), th["acc"], "middle", ls=4)[0]]
            if l2:
                s2 = 26 * min(1, 250 / doc.measure(l2, "headm", 26, 5))
                st.append(doc.text(cx, cy + 36, l2, "headm", round(s2, 1), th["acc"], "middle", ls=5)[0])
            st.append("</g>")
            add("".join(st), {"kind": "stamp", "start": round(t, 3), "dur": 0.5, "cx": cx, "cy": cy})
        y += 96
    return items, y + 40 + CARD


# --------------------------------------------------------------------------- output
CSS = """
.m{transform-box:view-box}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes wipe{from{transform:scaleX(1)}to{transform:scaleX(0)}}
@keyframes stamp{0%{opacity:0;transform:scale(1.5)}60%{opacity:1;transform:scale(.96)}100%{opacity:1;transform:scale(1)}}
"""


def ease_out(p):
    return 1 - (1 - p) ** 3


def at_time(item, t):
    a, s = item["anim"], item["svg"]
    if not a or t is None:
        return s
    p = max(0.0, min(1.0, (t - a["start"]) / a["dur"]))
    if p >= 1:
        return s
    k = a["kind"]
    if k == "fade":
        e = ease_out(p)
        return "" if e <= 0 else f'<g opacity="{e:.3f}" transform="translate(0 {(1 - e) * 10:.2f})">{s}</g>'
    if k == "wipe":
        sc = 1 - math.floor(p * a["n"]) / a["n"]
        ox = a["ox"]
        return s.replace('transform="scale(0 1)"', f'transform="translate({ox} 0) scale({sc:.3f} 1) translate({-ox} 0)"')
    if k == "stamp":
        if p <= 0:
            return ""
        if p < 0.6:
            u = ease_out(p / 0.6)
            sc, op = 1.5 + (0.96 - 1.5) * u, u
        else:
            sc, op = 0.96 + 0.04 * (p - 0.6) / 0.4, 1
        cx, cy = a["cx"], a["cy"]
        return f'<g opacity="{op:.3f}" transform="translate({cx} {cy}) scale({sc:.3f}) translate({-cx} {-cy})">{s}</g>'
    return s


def svg_doc(doc, items, H, th, meta, t=None, bg=None):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d"{meta.get("lang", "")}>',
         f'<title id="t">{esc(meta["title"])}</title>', f'<desc id="d">{esc(meta["desc"])}</desc>']
    animated = t is None
    if animated:
        rules = []
        for i, it in enumerate(items):
            a = it["anim"]
            if not a:
                continue
            if a["kind"] == "fade":
                rules.append(f'.a{i}{{animation:fade .3s ease-out {a["start"]}s both}}')
            elif a["kind"] == "wipe":
                rules.append(f'.a{i}{{transform-origin:{a["ox"]}px {a["oy"]}px;animation:wipe {a["dur"]}s steps({a["n"]},end) {a["start"]}s both}}')
            elif a["kind"] == "stamp":
                rules.append(f'.a{i}{{transform-origin:{a["cx"]}px {a["cy"]}px;animation:stamp .5s cubic-bezier(.2,.8,.3,1.2) {a["start"]}s both}}')
        o.append("<style>" + CSS + "\n".join(rules) + "\n@media (prefers-reduced-motion:reduce){.m{animation:none!important}}\n</style>")
    o.append("<defs>" + "".join(f'<path id="{g}" d="{d}"/>' for g, d in doc.defs.values() if d) + "</defs>")
    if bg:
        o.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    card = f'x="{CARD}" y="{CARD}" width="{W - 2 * CARD}" height="{H - 2 * CARD}" rx="14"'
    if th.get("shadow"):
        o.append(f'<rect {card} transform="translate(8 8)" fill="{th["shadow"]}"/>')
    o.append(f'<rect {card} fill="{th["paper"]}" stroke="{th["edge"]}" stroke-width="2"/>')
    for i, it in enumerate(items):
        if animated:
            if it["anim"]:
                if it["anim"]["kind"] == "wipe":
                    o.append(it["svg"].replace("<rect ", f'<rect class="m a{i}" ', 1))
                else:
                    o.append(f'<g class="m a{i}">{it["svg"]}</g>')
            else:
                o.append(it["svg"])
        else:
            s = at_time(it, t)
            if s:
                o.append(s)
    o.append("</svg>")
    return "\n".join(o)


def renderer():
    for name in ("resvg", "rsvg-convert"):
        if shutil.which(name):
            return name
    return None


def to_png(tool, svg: Path, png: Path, width: int):
    if tool == "resvg":
        cmd = ["resvg", "-w", str(width), str(svg), str(png)]
    else:
        cmd = ["rsvg-convert", "-w", str(width), "-o", str(png), str(svg)]
    subprocess.run(cmd, check=True)


def build_gif(doc, items, H, th, meta, out: Path, width: int, fps: int, start: str = "begin", hold: int = 300):
    tool, magick = renderer(), shutil.which("magick")
    if not tool or not magick:
        print("[skip] GIF 需要 rsvg-convert/resvg 和 magick", file=sys.stderr)
        return None
    end = max((a["start"] + a["dur"]) for a in (i["anim"] for i in items) if a)
    bg = th.get("gif_bg", "#FFFFFF")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        frames = []
        n = int(math.ceil(end * fps)) + 1
        for i in range(n + 1):
            t = 9999 if i == n else i / fps
            sp, pp = tmp / f"f{i:04d}.svg", tmp / f"f{i:04d}.png"
            sp.write_text(svg_doc(doc, items, H, th, meta, t=t, bg=bg), encoding="utf-8")
            to_png(tool, sp, pp, width)
            frames.append(pp)
        final = frames[-1]
        delay = round(100 / fps)
        # begin：从空白/打字开始播放，循环播放时更像录屏；final：首帧即最终帧，适合只显示首帧的平台
        lead = ["-delay", "120", str(final)] if start == "final" else ["-delay", "60", str(frames[0])]
        cmd = [magick] + lead + ["-delay", str(delay)] + [str(f) for f in frames[1:-1]] + \
              ["-delay", str(hold), str(final), "+dither", "-colors", "64", "-layers", "Optimize", "-loop", "0", str(out)]
        subprocess.run(cmd, check=True)
    return out


# --------------------------------------------------------------------------- commands
def cmd_build(args):
    sb = json.loads(args.storyboard.read_text(encoding="utf-8"))
    dirs = [Path(d) for d in args.fonts_dir] + [args.storyboard.parent]
    fonts = Fonts(sb["fonts"], dirs)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    suffix = sb.get("suffix", "")
    lang = f' xml:lang="{sb["lang"]}"' if sb.get("lang") else ""
    scenes = sb["scenes"]
    for idx, scene in enumerate(scenes, 1):
        doc = Doc(fonts)
        meta = {"lang": lang,
                "title": f'{sb["project"]} · {sb.get("demo", "DEMO").lower()} {idx}/{len(scenes)} · {scene["title"]}',
                "desc": f'{sb.get("you", "YOU")}: {scene["prompt"]} — {scene.get("summary", "")} ({sb.get("label", "")})'}
        built = {}
        for mode in ("light", "dark"):
            th = sb["themes"][mode]
            items, H = layout(doc, sb, scene, idx, len(scenes), th)
            built[mode] = (items, H, th)
        for mode, (items, H, th) in built.items():
            p = out / f'{scene["id"]}{suffix}-{mode}.svg'
            p.write_text(svg_doc(doc, items, H, th, meta), encoding="utf-8")
            print(f"✓ {p}  {p.stat().st_size / 1024:.0f}KB")
        if args.gif:
            (out / "gif").mkdir(exist_ok=True)
            for mode in args.gif_modes.split(","):
                items, H, th = built[mode]
                g = build_gif(doc, items, H, th, meta, out / "gif" / f'{scene["id"]}{suffix}-{mode}.gif',
                              args.gif_width, args.fps, args.gif_start, args.gif_hold)
                if g:
                    print(f"✓ {g}  {g.stat().st_size / 1024:.0f}KB")
    return 0


def cmd_extract(args):
    text = args.readme.read_text(encoding="utf-8")
    scenes = []
    for i, m in enumerate(re.finditer(r"```(?:text|prompt|)\n(.*?)\n```", text, re.S), 1):
        before = text[:m.start()].rstrip().splitlines()
        scenes.append({"id": f"prompt-{i}", "title": "TODO", "context": before[-1] if before else "",
                       "prompt": m.group(1).strip(), "summary": "TODO",
                       "reply": [{"kind": "line", "k": "TODO", "v": "按项目文档填写：字段名称和顺序必须来自源码或文档"}],
                       "footer": None})
    draft = {"project": args.readme.resolve().parent.name, "suffix": "", "label": "ILLUSTRATIVE · EXAMPLE VALUES",
             "fonts": {"mono": "JBM-Regular.ttf", "monob": "JBM-Bold.ttf", "head": "Oswald-Bold.ttf", "headm": "Oswald-Medium.ttf"},
             "themes": {"light": {}, "dark": {}}, "scenes": scenes}
    s = json.dumps(draft, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(s + "\n", encoding="utf-8")
    else:
        print(s)
    return 0


def main():
    ap = argparse.ArgumentParser(description="确定性演示分镜 → 动画 SVG + GIF")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract", help="从 README 代码块生成分镜草稿")
    e.add_argument("readme", type=Path)
    e.add_argument("-o", "--output", type=Path)
    b = sub.add_parser("build", help="生成动画 SVG（浅/深）与可选 GIF")
    b.add_argument("storyboard", type=Path)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--fonts-dir", action="append", default=[])
    b.add_argument("--gif", action="store_true")
    b.add_argument("--gif-width", type=int, default=960)
    b.add_argument("--fps", type=int, default=10)
    b.add_argument("--gif-modes", default="light,dark", help="逗号分隔：light,dark")
    b.add_argument("--gif-start", choices=["begin", "final"], default="begin")
    b.add_argument("--gif-hold", type=int, default=300, help="最终帧停留，单位 1/100 秒")
    args = ap.parse_args()
    return cmd_extract(args) if args.cmd == "extract" else cmd_build(args)


if __name__ == "__main__":
    sys.exit(main())
