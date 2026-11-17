#!/usr/bin/env python3
"""
render_preview.py — 用 resvg 把 SVG 渲染成 PNG 预览，可选拼成"深浅色对比图"或"移动端缩略图"。

用法:
    python3 render_preview.py <file-or-dir> [...] [--out .readme-preview] [--width 1280] [--mobile]

说明:
    - 后端优先级：resvg CLI → resvg_py → rsvg-convert（librsvg）→ magick（ImageMagick）。
      resvg 与 GitHub/浏览器最接近；rsvg-convert 次之；magick 仅作兜底。
    - --github 按 GitHub 实际显示宽度输出（桌面 830px + 移动 360px），用于自查可读性。
    - --mobile 额外输出 360px 宽版本，用于检查 hero 在手机上的可读性。
    - resvg 不执行 CSS 动画，输出的是静态帧；这与 GitHub 不播放动画时的效果一致。
    - 渲染器不支持 CSS 变量与 prefers-color-scheme：脚本会先把 `:root{--x:…}` 变量内联成具体值
      （深色取 `@media (prefers-color-scheme: dark){:root{…}}` 中的覆盖值），再交给渲染器。
    - 单文件内含深色媒体查询的 SVG（如 styles/*.example.svg）默认额外输出 `<名称>@dark.png`；
      用 --scheme light|dark|both 控制。
    - 如安装了 Pillow，会把同名的 *-light / *-dark 拼成一张 *-compare.png。

依赖: resvg（CLI 或 resvg_py）；可选 Pillow。
"""
from __future__ import annotations

import argparse
import re
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path


def find_backend():
    if shutil.which("resvg"):
        return "cli"
    try:
        import resvg_py  # type: ignore  # noqa: F401
        return "py"
    except ImportError:
        pass
    if shutil.which("rsvg-convert"):
        return "rsvg"
    if shutil.which("magick"):
        return "magick"
    return None


def run(cmd: list[str], svg: Path) -> bool:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  ✗ {svg.name}: {res.stderr.strip()}", file=sys.stderr)
        return False
    return True


DARK_MEDIA_RE = re.compile(
    r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}", re.S)
ROOT_RE = re.compile(r":root\s*\{([^{}]*)\}", re.S)
VAR_DEF_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
VAR_USE_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)")


def has_dark_media(raw: str) -> bool:
    return bool(DARK_MEDIA_RE.search(raw))


def flatten_css(raw: str, scheme: str) -> str:
    """把 CSS 变量内联为具体值，并移除深色媒体查询（渲染器不支持两者）。"""
    dark_blocks = DARK_MEDIA_RE.findall(raw)
    body = DARK_MEDIA_RE.sub("", raw)
    values: dict[str, str] = {}
    for block in ROOT_RE.findall(body):
        values.update((k, v.strip()) for k, v in VAR_DEF_RE.findall(block))
    if scheme == "dark":
        for media in dark_blocks:
            for block in ROOT_RE.findall(media):
                values.update((k, v.strip()) for k, v in VAR_DEF_RE.findall(block))
    if not values and not dark_blocks:
        return raw
    for _ in range(4):  # 变量可能引用变量
        new = VAR_USE_RE.sub(lambda m: values.get(m.group(1), (m.group(2) or "").strip() or m.group(0)), body)
        if new == body:
            break
        body = new
    return body


def render(svg: Path, png: Path, width: int, backend: str, scheme: str = "light") -> bool:
    png.parent.mkdir(parents=True, exist_ok=True)
    raw = svg.read_text(encoding="utf-8", errors="ignore")
    flat = flatten_css(raw, scheme)
    if flat != raw:
        with tempfile.NamedTemporaryFile("w", suffix=".svg", dir=svg.parent, delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(flat)
        try:
            return _render(Path(tmp.name), png, width, backend, svg)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    return _render(svg, png, width, backend, svg)


def _render(svg: Path, png: Path, width: int, backend: str, label: Path) -> bool:
    svg_label = label
    if backend == "cli":
        return run(["resvg", "--width", str(width), str(svg), str(png)], svg_label)
    if backend == "rsvg":
        return run(["rsvg-convert", "-w", str(width), "-o", str(png), str(svg)], svg_label)
    if backend == "magick":
        return run(["magick", "-background", "none", "-density", "192", str(svg),
                    "-resize", f"{width}x", str(png)], svg_label)
    import resvg_py  # type: ignore
    try:
        data = resvg_py.svg_to_bytes(svg_path=str(svg), width=width)
        png.write_bytes(bytes(data))
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {svg_label.name}: {e}", file=sys.stderr)
        return False


def compose_compare(light: Path, dark: Path, out: Path) -> bool:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return False
    a, b = Image.open(light), Image.open(dark)
    gap = 24
    w = max(a.width, b.width)
    canvas = Image.new("RGB", (w, a.height + b.height + gap), (128, 128, 128))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (0, a.height + gap))
    canvas.save(out)
    return True


def collect(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        if p.is_dir():
            out += sorted(x for x in p.rglob("*.svg") if not x.name.endswith(".src.svg"))
        elif p.suffix.lower() == ".svg":
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG → PNG 预览")
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path(".readme-preview"))
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--mobile", action="store_true", help="额外输出 360px 宽版本")
    ap.add_argument("--github", action="store_true", help="额外输出 GitHub 桌面 830px 与移动 360px 版本")
    ap.add_argument("--scheme", choices=["auto", "light", "dark", "both"], default="auto",
                    help="单文件深浅色 SVG 的渲染方案；auto = 含深色媒体查询时两套都出")
    args = ap.parse_args()

    backend = find_backend()
    if backend is None:
        print("未找到渲染器。安装方式：brew install resvg / pip install resvg-py / brew install librsvg",
              file=sys.stderr)
        return 2

    files = collect(args.paths)
    if not files:
        print("未找到 SVG 文件", file=sys.stderr)
        return 2
    print(f"渲染后端：{backend}")
    if args.github:
        args.mobile = True

    ok = 0
    rendered: dict[str, Path] = {}
    for svg in files:
        if args.scheme == "auto":
            schemes = ["light", "dark"] if has_dark_media(svg.read_text(encoding="utf-8", errors="ignore")) \
                else ["light"]
        else:
            schemes = ["light", "dark"] if args.scheme == "both" else [args.scheme]
        file_ok = True
        for scheme in schemes:
            suffix = "@dark" if scheme == "dark" and len(schemes) > 1 else ""
            stem = svg.stem + suffix
            png = args.out / (stem + ".png")
            if render(svg, png, args.width, backend, scheme):
                rendered[stem] = png
                print(f"  ✓ {png}")
            else:
                file_ok = False
            if args.github:
                g = args.out / (stem + "@github.png")
                if render(svg, g, 830, backend, scheme):
                    print(f"  ✓ {g}")
            if args.mobile:
                m = args.out / (stem + "@mobile.png")
                if render(svg, m, 360, backend, scheme):
                    print(f"  ✓ {m}")
        ok += file_ok

    for stem, png in rendered.items():
        pair = None
        if stem.endswith("-light"):
            base = stem[: -len("-light")]
            pair = rendered.get(base + "-dark")
        elif stem + "@dark" in rendered:
            base, pair = stem, rendered[stem + "@dark"]
        if pair:
            out = args.out / f"{base}-compare.png"
            if compose_compare(png, pair, out):
                print(f"  ✓ {out}（深浅色对比）")

    print(f"\n渲染完成 {ok}/{len(files)}，输出目录：{args.out}")
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
