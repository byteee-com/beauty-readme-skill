#!/usr/bin/env python3
"""
analyze_repo.py — 提取仓库信号并为风格卡打分。

用法:
    python3 analyze_repo.py <repo-path> [--json] [--styles <styles-dir>]
                            [--seed N] [--exclude style-id ...]

输出:
    - 项目类型候选、语言、生态、素材清单、主题色候选
    - 每张风格卡的得分与命中理由
    - variation：主风格的变体、全局变奏轴、可选混搭（见 references/variation.md）
    - compare_set：多方案对比时的三套组合（不同风格卡且不同骨架）
脚本只做启发式初筛，Agent 必须结合自己读到的代码与 README 调整结论。

--seed: 默认用仓库名哈希，结果可复现；用户要"再来一版"时换一个数。
--exclude: 用户说"不要这种风格"时排除对应风格卡。

依赖: Python 3.9+；可选 PyYAML（缺失时用内置的 YAML 子集解析器读取 styles/*.yaml）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", "target", ".venv", "venv", "__pycache__",
    ".next", ".nuxt", "vendor", ".idea", ".vscode", "coverage", ".turbo", ".cache",
}
MAX_FILES = 20000

LANG_BY_EXT = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".mjs": "JavaScript", ".rs": "Rust", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".swift": "Swift", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".cs": "C#", ".dart": "Dart", ".lua": "Lua",
    ".zig": "Zig", ".ex": "Elixir", ".exs": "Elixir", ".scala": "Scala", ".vue": "Vue",
    ".svelte": "Svelte", ".ipynb": "Jupyter",
}

# 语言生态色（无品牌色时的配色来源之一）
ECOSYSTEM_COLOR = {
    "Rust": "#DEA584", "Go": "#00ADD8", "Python": "#3776AB", "TypeScript": "#3178C6",
    "JavaScript": "#F7DF1E", "Ruby": "#CC342D", "Swift": "#F05138", "Kotlin": "#7F52FF",
    "Java": "#B07219", "C#": "#178600", "Dart": "#0175C2", "Elixir": "#6E4A7E",
    "Zig": "#F7A41D", "Vue": "#41B883", "Svelte": "#FF3E00",
}

CLI_DEPS = {"clap", "cobra", "click", "typer", "commander", "yargs", "oclif", "ink",
            "bubbletea", "ratatui", "argparse", "urfave/cli", "cac", "meow", "fire"}
APP_DEPS = {"react", "vue", "svelte", "next", "nuxt", "electron", "tauri", "@tauri-apps/api",
            "react-native", "expo", "flutter", "solid-js", "astro"}
GAME_DEPS = {"three", "pixi.js", "phaser", "bevy", "pygame", "godot", "babylonjs"}
AI_DEPS = {"openai", "anthropic", "@anthropic-ai/sdk", "langchain", "llama-index", "transformers",
           "torch", "ollama", "ai", "@ai-sdk/openai"}
INFRA_HINT_FILES = {"Dockerfile", "docker-compose.yml", "helm", "charts", "terraform", "k8s"}
HARDWARE_DEPS = {"embassy", "cortex-m", "cortex-m-rt", "embedded-hal", "esp-idf-sys", "esp-idf-hal",
                 "platformio", "zephyr", "rppal", "micropython", "adafruit-blinka"}
HARDWARE_HINT_FILES = ("platformio.ini", "memory.x", "Kconfig", ".kicad_pcb", ".dts", "sdkconfig",
                       "firmware/", "hardware/", "schematics/")

# ---------------------------------------------------------------- helpers
def walk(root: Path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            count += 1
            if count > MAX_FILES:
                return
            yield Path(dirpath) / f


def read_text(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def load_json(p: Path) -> dict:
    try:
        return json.loads(read_text(p))
    except (json.JSONDecodeError, ValueError):
        return {}


def load_toml(p: Path) -> dict:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        return tomllib.loads(read_text(p))
    except Exception:
        return {}


HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6})\b")


def hex_colors(text: str) -> list[str]:
    return [c.upper() for c in HEX_RE.findall(text)]


def is_neutral(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < 24


# ---------------------------------------------------------------- analysis
def analyze(root: Path) -> dict:
    files = list(walk(root))
    rel = [f.relative_to(root).as_posix() for f in files]
    rel_set = set(rel)

    # 语言
    lang_counter: Counter[str] = Counter()
    for f in files:
        lang = LANG_BY_EXT.get(f.suffix.lower())
        if lang:
            lang_counter[lang] += 1
    languages = [l for l, _ in lang_counter.most_common(5)]

    # 清单文件
    meta: dict = {"name": root.name, "description": "", "keywords": []}
    deps: set[str] = set()
    manifests = []
    has_cli_entry = False
    cli_evidence: list[str] = []

    pkg = root / "package.json"
    if pkg.exists():
        manifests.append("package.json")
        data = load_json(pkg)
        meta["name"] = data.get("name", meta["name"])
        meta["description"] = data.get("description", "")
        meta["keywords"] += data.get("keywords", []) or []
        for k in ("dependencies", "devDependencies", "peerDependencies"):
            deps |= set((data.get(k) or {}).keys())
        if data.get("bin"):
            has_cli_entry = True
            cli_evidence.append("package.json#bin")
        if data.get("homepage"):
            meta["homepage"] = data["homepage"]

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        manifests.append("pyproject.toml")
        data = load_toml(pyproject)
        proj = data.get("project", {}) or data.get("tool", {}).get("poetry", {})
        meta["name"] = proj.get("name", meta["name"])
        meta["description"] = meta["description"] or proj.get("description", "")
        meta["keywords"] += proj.get("keywords", []) or []
        for d in proj.get("dependencies", []) or []:
            if isinstance(d, str):
                deps.add(re.split(r"[<>=!~\[; ]", d, 1)[0].lower())
        if isinstance(proj.get("dependencies"), dict):
            deps |= {k.lower() for k in proj["dependencies"]}
        if proj.get("scripts") or data.get("tool", {}).get("poetry", {}).get("scripts"):
            has_cli_entry = True
            cli_evidence.append("pyproject.toml#scripts")
        urls = proj.get("urls") or {}
        if isinstance(urls, dict) and urls.get("Homepage"):
            meta["homepage"] = urls["Homepage"]

    cargo = root / "Cargo.toml"
    if cargo.exists():
        manifests.append("Cargo.toml")
        data = load_toml(cargo)
        pk = data.get("package", {})
        meta["name"] = pk.get("name", meta["name"])
        meta["description"] = meta["description"] or pk.get("description", "")
        meta["keywords"] += pk.get("keywords", []) or []
        deps |= set((data.get("dependencies") or {}).keys())
        if data.get("bin") or (root / "src/main.rs").exists():
            has_cli_entry = True
            cli_evidence.append("Cargo.toml#bin or src/main.rs")
        if pk.get("homepage"):
            meta["homepage"] = pk["homepage"]

    gomod = root / "go.mod"
    if gomod.exists():
        manifests.append("go.mod")
        text = read_text(gomod)
        for m in re.finditer(r"^\s*([\w./-]+)\s+v", text, re.M):
            deps.add(m.group(1).split("/")[-1] if "cobra" not in m.group(1) else "cobra")
            if "urfave/cli" in m.group(1):
                deps.add("urfave/cli")
        if any(r.startswith("cmd/") for r in rel) or "main.go" in rel_set:
            has_cli_entry = True
            cli_evidence.append("cmd/ or main.go")

    for candidate in ("cli.py", "__main__.py", "bin/", "cli.ts", "cli.js", "src/cli.ts", "src/cli.rs"):
        hits = [r for r in rel if r.endswith(candidate) or r.startswith(candidate)]
        if hits:
            has_cli_entry = True
            cli_evidence.append(hits[0])
            break

    deps_lower = {d.lower() for d in deps}

    # 素材
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    images = [r for r in rel if Path(r).suffix.lower() in image_exts]
    logos = [r for r in images if re.search(r"(logo|icon|brand|mark)", r, re.I)]
    screenshots = [r for r in images if re.search(r"(screen|shot|demo|preview|showcase)", r, re.I)
                   or Path(r).suffix.lower() == ".gif"]
    has_docs = any(r.startswith(("docs/", "website/", "site/")) for r in rel) or \
        any(r.endswith(("mkdocs.yml", "docusaurus.config.js", "docusaurus.config.ts", "vitepress/config.ts"))
            for r in rel)
    has_api_ref = any(re.search(r"(typedoc|api-extractor|sphinx|rustdoc|pdoc)", r, re.I) for r in rel)
    has_notebook = any(r.endswith(".ipynb") for r in rel)
    has_citation = "CITATION.cff" in rel_set or any(r.endswith(".bib") for r in rel)

    # 主题色候选：logo SVG > CSS 变量 > tailwind 配置
    color_sources: list[tuple[str, str]] = []
    for r in [x for x in logos if x.endswith(".svg")][:3]:
        for c in hex_colors(read_text(root / r, 50_000)):
            color_sources.append((c, r))
    for r in [x for x in rel if x.endswith((".css", "tailwind.config.js", "tailwind.config.ts"))][:20]:
        text = read_text(root / r, 50_000)
        for m in re.finditer(r"--(?:primary|brand|accent)[\w-]*\s*:\s*(#[0-9a-fA-F]{6})", text):
            color_sources.append((m.group(1).upper(), r))
    seen: dict[str, str] = {}
    for c, src in color_sources:
        if not is_neutral(c) and c not in seen:
            seen[c] = src
    brand_colors = [{"hex": c, "source": s} for c, s in list(seen.items())[:5]]
    if not brand_colors and languages and languages[0] in ECOSYSTEM_COLOR:
        brand_colors = [{"hex": ECOSYSTEM_COLOR[languages[0]], "source": f"ecosystem:{languages[0]}"}]

    # 现有 README
    readme_path = next((root / n for n in ("README.md", "readme.md", "README.MD", "Readme.md")
                        if (root / n).exists()), None)
    readme = read_text(readme_path) if readme_path else ""
    readme_info = {
        "path": readme_path.name if readme_path else None,
        "chars": len(readme),
        "headings": re.findall(r"^#{1,3}\s+(.+)$", readme, re.M)[:30],
        "images": len(re.findall(r"!\[|<img\s", readme)),
        "badges": len(re.findall(r"shields\.io|badge", readme)),
        "code_blocks": readme.count("```") // 2,
        "has_license_section": bool(re.search(r"^#+\s*(license|许可)", readme, re.I | re.M)),
    }
    translations = [r for r in rel if re.match(r"README\.[\w-]+\.md$", r, re.I)]

    # 项目类型打分
    text_blob = " ".join([meta["description"], " ".join(meta["keywords"]), readme[:4000]]).lower()

    def kw(*words: str) -> int:
        return sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", text_blob))

    types: Counter[str] = Counter()
    if has_cli_entry:
        types["cli"] += 3
    if deps_lower & CLI_DEPS:
        types["cli"] += 2
    types["cli"] += kw("cli", "command-line", "command line", "terminal")
    if deps_lower & {"ink", "bubbletea", "ratatui", "textual", "blessed"}:
        types["tui"] += 4
    if deps_lower & APP_DEPS:
        types["consumer-app"] += 3
    types["consumer-app"] += kw("app", "desktop", "mobile", "web app")
    if deps_lower & GAME_DEPS:
        types["game"] += 3
    types["game"] += kw("game", "play", "emulator", "roguelike", "pixel", "retro")
    if deps_lower & AI_DEPS:
        types["ai-product"] += 3
    types["ai-product"] += kw("ai", "llm", "agent", "gpt", "claude", "model")
    types["library"] += kw("library", "lib", "package", "module")
    if not has_cli_entry and manifests:
        types["library"] += 2
    types["framework"] += kw("framework")
    types["sdk"] += kw("sdk", "client", "api client")
    if any(any(h in r for h in INFRA_HINT_FILES) for r in rel):
        types["infra"] += 1
    types["infra"] += kw("kubernetes", "deploy", "infrastructure", "server", "database", "proxy")
    types["devtool"] += kw("developer", "devtool", "lint", "formatter", "bundler", "plugin", "editor")
    if has_notebook or has_citation:
        types["research"] += 3
    types["research"] += kw("paper", "research", "dataset", "benchmark", "arxiv")
    types["design-resource"] += kw("icons", "font", "typeface", "theme", "design system", "ui kit", "figma")
    types["creative"] += kw("art", "music", "creative", "drawing", "story", "visual", "generative", "zine",
                            "creative coding", "shader")
    if deps_lower & HARDWARE_DEPS:
        types["hardware"] += 3
    if any(h in r for r in rel for h in HARDWARE_HINT_FILES):
        types["hardware"] += 2
    types["hardware"] += kw("embedded", "firmware", "hardware", "microcontroller", "mcu", "arduino",
                            "esp32", "rtos", "robot", "fpga", "pcb")
    project_types = [t for t, s in types.most_common() if s > 0][:4]

    facts = {
        "has_cli_entry": has_cli_entry,
        "has_visual_subject": bool(screenshots or logos or types["game"] or types["creative"]),
        "has_screenshots": bool(screenshots),
        "has_website": bool(meta.get("homepage")),
        "has_docs_site": has_docs,
        "has_api_reference": has_api_ref,
        "many_contributors": False,  # 无法离线判断；Agent 可结合 GitHub 页面补充
    }

    return {
        "repo": str(root),
        "name": meta["name"],
        "description": meta["description"],
        "keywords": meta["keywords"],
        "homepage": meta.get("homepage"),
        "languages": languages,
        "manifests": manifests,
        "dependencies_sample": sorted(deps_lower)[:40],
        "project_types": project_types,
        "type_scores": dict(types.most_common()),
        "facts": facts,
        "cli_evidence": cli_evidence,
        "assets": {
            "logos": logos[:10],
            "screenshots": screenshots[:10],
            "image_count": len(images),
        },
        "brand_colors": brand_colors,
        "readme": readme_info,
        "translations": translations,
        "_text_blob": text_blob,
        "_files": rel,
    }


# ---------------------------------------------------------------- style cards
def _strip_comment(line: str) -> str:
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _split_top(text: str, sep: str = ",") -> list[str]:
    parts, depth, quote, cur = [], 0, None, ""
    for ch in text:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _split_key(text: str):
    """返回 (key, value)；不是 'key: value' 形式时返回 None。"""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == ":" and (i + 1 == len(text) or text[i + 1] == " "):
            return text[:i].strip().strip("\"'"), text[i + 1:].strip()
    return None


def _scalar(text: str):
    t = text.strip()
    if not t:
        return None
    if t[0] in "\"'" and t[-1] == t[0]:
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        return [_scalar(x) for x in _split_top(t[1:-1])]
    if t.startswith("{") and t.endswith("}"):
        out = {}
        for item in _split_top(t[1:-1]):
            kv = _split_key(item)
            if kv:
                out[kv[0]] = _scalar(kv[1])
        return out
    low = t.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def mini_yaml(text: str):
    """风格卡用到的 YAML 子集：缩进映射、块列表、行内 [] / {}、引号字符串、注释。"""
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if line.strip():
            lines.append([len(line) - len(line.lstrip(" ")), line.strip()])

    def block(i: int, indent: int):
        if i >= len(lines):
            return None, i
        if lines[i][1].startswith("- ") or lines[i][1] == "-":
            out = []
            while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("-"):
                rest = lines[i][1][1:].strip()
                if rest and _split_key(rest) and not rest.startswith(("[", "{", "\"", "'")):
                    lines[i] = [indent + 2, rest]
                    val, i = block(i, indent + 2)
                elif rest:
                    val, i = _scalar(rest), i + 1
                else:
                    val, i = block(i + 1, lines[i + 1][0]) if i + 1 < len(lines) else (None, i + 1)
                out.append(val)
            return out, i
        out = {}
        while i < len(lines) and lines[i][0] == indent:
            kv = _split_key(lines[i][1])
            if not kv:
                i += 1
                continue
            key, val = kv
            i += 1
            if val:
                out[key] = _scalar(val)
            elif i < len(lines) and (lines[i][0] > indent or
                                     (lines[i][0] == indent and lines[i][1].startswith("-"))):
                out[key], i = block(i, lines[i][0])
            else:
                out[key] = None
        return out, i

    return block(0, lines[0][0])[0] if lines else {}


def load_styles(styles_dir: Path) -> dict:
    try:
        import yaml  # type: ignore
        parse = yaml.safe_load
    except ImportError:
        parse = mini_yaml
    styles = {}
    for p in sorted(styles_dir.glob("*.yaml")):
        try:
            data = parse(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 无法解析 {p.name}: {e}", file=sys.stderr)
            continue
        if isinstance(data, dict) and data.get("id"):
            styles[data["id"]] = data
    if not styles:
        print(f"[warn] {styles_dir} 中没有可用的风格卡", file=sys.stderr)
    return styles


# ---------------------------------------------------------------- scoring
def score_styles(info: dict, styles: dict, exclude: set[str] | None = None) -> list[dict]:
    results = []
    ptypes = info["project_types"]
    primary = ptypes[:2]
    blob = info["_text_blob"]
    files = info["_files"]
    deps = set(info["dependencies_sample"])
    facts = info["facts"]

    for sid, style in styles.items():
        if exclude and sid in exclude:
            results.append({"id": sid, "score": None, "eligible": False, "reasons": ["用户排除"]})
            continue
        fit = style.get("fit", {}) or {}
        score, reasons = 0, []
        missing = [n for n in fit.get("needs", []) or [] if not facts.get(n, False)]
        if missing:
            results.append({"id": sid, "score": None, "eligible": False,
                            "reasons": [f"缺少前提: {', '.join(missing)}"]})
            continue
        for t in primary:
            if t in (fit.get("strong") or []):
                score += 40; reasons.append(f"项目类型 {t} 强匹配 +40"); break
        else:
            for t in primary:
                if t in (fit.get("ok") or []):
                    score += 20; reasons.append(f"项目类型 {t} 可用 +20"); break
        for t in primary:
            if t in (fit.get("avoid") or []):
                score -= 50; reasons.append(f"项目类型 {t} 不适合 −50"); break

        bonus = 0
        for sig in style.get("signals", []) or []:
            for w in sig.get("keyword", []) or []:
                if re.search(rf"\b{re.escape(w)}\b", blob):
                    bonus += 5; reasons.append(f"关键词 {w} +5")
            for f in sig.get("file", []) or []:
                pat = f.replace("*", "")
                if any(r.startswith(pat) or r.endswith(pat) for r in files):
                    bonus += 5; reasons.append(f"文件 {f} +5")
            for d in sig.get("dependency", []) or []:
                if d.lower() in deps:
                    bonus += 5; reasons.append(f"依赖 {d} +5")
            for m in sig.get("meta", []) or []:
                if facts.get(m):
                    bonus += 5; reasons.append(f"{m} +5")
        if bonus > 30:
            reasons.append(f"信号加分封顶（{bonus} → 30）")
            bonus = 30
        score += bonus
        results.append({"id": sid, "score": score, "eligible": True, "reasons": reasons})

    results.sort(key=lambda r: (r["eligible"], r["score"] or -999), reverse=True)
    return results


def recommend(results: list[dict]) -> dict:
    eligible = [r for r in results if r["eligible"]]
    if not eligible:
        return {"mode": "compare", "pick": None, "note": "没有可用风格，建议用户指定或补充素材"}
    top = eligible[0]
    if len(eligible) > 1:
        second = eligible[1]
        gap = top["score"] - second["score"]
        if top["score"] <= 0 or gap < max(5, abs(top["score"]) * 0.1):
            return {"mode": "compare", "pick": top["id"],
                    "note": f"前两名接近（{top['id']} {top['score']} vs {second['id']} {second['score']}），建议多方案对比"}
    return {"mode": "auto", "pick": top["id"], "note": "得分领先，可直接自动推荐"}


# ---------------------------------------------------------------- variation
GLOBAL_AXES = {
    "anchor": ["左重", "右重", "下沉", "中轴", "对角", "出血裁切"],
    "palette_source": ["品牌色", "截图取色", "生态色", "物件本色", "单色 + 一点"],
    "font": ["新怪诞无衬线", "衬线", "等宽", "压缩无衬线", "圆体", "中文宋 / 黑 / 楷"],
    "texture": ["平涂", "颗粒", "网点", "扫描线", "纸纹", "套印错位", "无"],
    "density": ["极简", "平衡", "信息密集"],
    "dark_mode": ["夜景", "发光屏", "负片 / 晒图", "荧光油墨", "同场景换时间"],
}


def make_rng(name: str, seed: int | None) -> tuple[random.Random, int]:
    key = name if seed is None else f"{name}:{seed}"
    value = int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:12], 16)
    return random.Random(value), value


def pick_variant(style: dict, rng: random.Random) -> dict | None:
    variants = [v for v in style.get("variants") or [] if isinstance(v, dict)]
    return dict(rng.choice(variants)) if variants else None


def pick_axes(style: dict, info: dict, rng: random.Random) -> dict:
    limits = style.get("variation_limits") or {}
    axes = {}
    for axis, options in GLOBAL_AXES.items():
        allowed = [o for o in (limits.get(axis) or options)]
        if axis == "palette_source":
            real_brand = any(not c["source"].startswith("ecosystem:") for c in info["brand_colors"])
            if real_brand and "品牌色" in allowed:
                axes[axis] = "品牌色（仓库已有，优先）"
                continue
            allowed = [o for o in allowed if o != "品牌色"] or allowed
            if not info["facts"]["has_screenshots"]:
                allowed = [o for o in allowed if o != "截图取色"] or allowed
        axes[axis] = rng.choice(allowed)
    return axes


def build_variation(info: dict, styles: dict, results: list[dict], rec: dict,
                    seed: int | None) -> dict | None:
    pick = rec.get("pick")
    if not pick or pick not in styles:
        return None
    rng, value = make_rng(info["name"], seed)
    style = styles[pick]
    variant = pick_variant(style, rng)
    axes = pick_axes(style, info, rng)
    borrow = None
    eligible = [r for r in results if r["eligible"] and r["id"] != pick]
    if eligible:
        second = eligible[0]
        items = styles.get(second["id"], {}).get("borrowable") or []
        top_score = next(r["score"] for r in results if r["id"] == pick)
        if items and second["score"] is not None and second["score"] >= max(1, top_score) * 0.6:
            borrow = {"from": second["id"], "element": rng.choice(items),
                      "note": "可选：只借一个元素，用主风格的配色重画"}
    canvas = (variant or {}).get("canvas", "?")
    signature = " · ".join(str(x) for x in [
        pick, style.get("skeleton", "?"), f"variant={(variant or {}).get('id', '-')}", canvas,
        axes["anchor"], axes["palette_source"], axes["font"], axes["texture"], axes["density"], axes["dark_mode"],
    ]) + (f" + borrow:{borrow['from']}.{borrow['element']}" if borrow else "")
    return {
        "seed": value,
        "style": pick,
        "skeleton": style.get("skeleton"),
        "alt_skeletons": style.get("alt_skeletons") or [],
        "variant": variant,
        "axes": axes,
        "borrow": borrow,
        "signature": signature,
        "note": "种子只在同样合理的选项间打破平局；概念需要时直接改，并在理由里说明",
    }


def build_compare_set(info: dict, styles: dict, results: list[dict], seed: int | None) -> list[dict]:
    """多方案对比：最多 3 套，风格卡不同且骨架不同。"""
    rng, _ = make_rng(info["name"] + "#compare", seed)
    chosen, used = [], set()
    for r in [x for x in results if x["eligible"]]:
        style = styles.get(r["id"], {})
        for sk in [style.get("skeleton")] + list(style.get("alt_skeletons") or []):
            if sk and sk not in used:
                used.add(sk)
                v = pick_variant(style, rng)
                chosen.append({"style": r["id"], "score": r["score"], "skeleton": sk,
                               "variant": (v or {}).get("id"), "canvas": (v or {}).get("canvas")})
                break
        if len(chosen) == 3:
            break
    return chosen


# ---------------------------------------------------------------- output
def main() -> int:
    ap = argparse.ArgumentParser(description="提取仓库信号并为 README 风格打分")
    ap.add_argument("repo", type=Path)
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--styles", type=Path, default=Path(__file__).resolve().parent.parent / "styles")
    ap.add_argument("--seed", type=int, default=None, help="变奏种子；默认用仓库名哈希。'再来一版'时换一个数")
    ap.add_argument("--exclude", nargs="*", default=[], help="排除的风格卡 id")
    args = ap.parse_args()

    root = args.repo.resolve()
    if not root.is_dir():
        print(f"不是目录: {root}", file=sys.stderr)
        return 2

    info = analyze(root)
    styles = load_styles(args.styles)
    results = score_styles(info, styles, set(args.exclude))
    info["style_scores"] = results
    info["recommendation"] = recommend(results)
    info["variation"] = build_variation(info, styles, results, info["recommendation"], args.seed)
    info["compare_set"] = build_compare_set(info, styles, results, args.seed)
    info.pop("_text_blob", None)
    info.pop("_files", None)

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    print(f"# {info['name']}")
    print(f"描述: {info['description'] or '（无）'}")
    print(f"语言: {', '.join(info['languages']) or '（未识别）'}")
    print(f"类型候选: {', '.join(info['project_types']) or '（未识别）'}")
    print(f"CLI 入口: {'是 ' + str(info['cli_evidence']) if info['facts']['has_cli_entry'] else '否'}")
    print(f"logo: {info['assets']['logos'][:3]}  截图: {info['assets']['screenshots'][:3]}")
    print(f"主题色: {[c['hex'] + ' (' + c['source'] + ')' for c in info['brand_colors']]}")
    print(f"README: {info['readme']['chars']} 字符, {len(info['readme']['headings'])} 个标题, "
          f"{info['readme']['images']} 张图, {info['readme']['badges']} 个徽章")
    print("\n## 风格得分")
    for r in results:
        s = "不可选" if not r["eligible"] else f"{r['score']:>4}"
        print(f"- {r['id']:<18} {s}  " + "; ".join(r["reasons"][:6]))
    rec = info["recommendation"]
    print(f"\n## 建议: 模式={rec['mode']}  风格={rec['pick']}\n{rec['note']}")
    var = info["variation"]
    if var:
        print("\n## 变奏（references/variation.md）")
        v = var["variant"] or {}
        print(f"变体: {v.get('id', '-')} ({v.get('canvas', '?')}) {v.get('hero', '')}")
        print(f"兼容骨架: {var['skeleton']} / {', '.join(var['alt_skeletons']) or '—'}")
        print("变奏轴: " + "；".join(f"{k}={val}" for k, val in var["axes"].items()))
        if var["borrow"]:
            print(f"可选混搭: 从 {var['borrow']['from']} 借「{var['borrow']['element']}」")
        print(f"签名: {var['signature']}")
    if info["compare_set"]:
        print("\n## 多方案对比候选")
        for c in info["compare_set"]:
            print(f"- {c['style']} · {c['skeleton']} · {c['variant']} ({c['canvas']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
