# Beauty README 设计记录

## Concept

把这份 README 做成一张排版校样。左侧是最终字标，右侧用叠页、裁切十字和竖向标尺呈现文档结构。深色版以校样显示器的虚线页框和坐标网格呈现同一份内容。

考虑过用三张风格卡做成样本册，以及直接展示 JSON 的终端记录。样本册会分散首屏的焦点，终端记录无法同时展示 README 的版式结构。排版校样能同时容纳页面轮廓和实际风格推荐。

## Evidence

| 内容 | 出处 |
| :-- | :-- |
| `recommendation.pick` 为 `swiss-grid`，`recommendation.mode` 为 `auto` | 本次改版前运行 `python3 scripts/analyze_repo.py . --json` 的结果，字段定义见 [analyze_repo.py](../../scripts/analyze_repo.py#L418-L451)。这份封面记录的是改版前的分析，新增 GIF 后脚本也会把演示算入素材。 |
| 校样里的安装和内置风格 | [README 的实际章节](../../README.md) |
| 自动推荐分镜 | [可复制的提示词](../../README.md#L43-L61)、改版前的推荐字段，以及本次生成的 README 与封面 |
| 只做素材分镜 | [素材交付规则](../../SKILL.md#L40-L48)、[图片嵌入示例](../../references/native-markdown.md#L33-L43)和本次生成的封面文件名 |

分析初次运行时瑞士网格得 30 分，霓虹终端和编辑海报未满足风格卡的素材前提。项目是带辅助脚本的 Agent 技能，文档型骨架适合把安装和第一条提示词放在封面后面。沿用 [瑞士网格](../../styles/swiss-grid.yaml) 与[文档型骨架](../../skeletons/document.md)，视觉重量 L1，两个演示内折，不加章节装饰图。

## 配色与字体

蓝色来自脚本给出的 Python 生态色候选 `#3776AB`。调整明度后分别用于浅色纸面和深色校样屏。强调色集中在推荐结果，面积约占封面的 4.5%。

| 用途 | 浅色 | 深色 |
| :-- | :-- | :-- |
| 背景 | `#F0F4F8` | `#121D2B` |
| 前景 | `#142235` | `#ECF4FC` |
| 次要文字 | `#42556D` | `#B0C1D3` |
| 校样纸面 | `#FAFCFF` | `#1A2A3E` |
| 强调背景 | `#275591` | `#A3CCFF` |
| 强调文字 | `#FFFFFF` | `#12243A` |
| 分隔线 | `#B3C1D0` | `#536B84` |

字标用 Inter 850，中文用思源黑体 Medium，技术字段用 Monaco。分镜标题用 Inter 650。发布用 SVG 均把文字转换为路径。采用左重右轻的构图、可见的裁切网格和 176px 对 22px 的字号差。最小技术标签在 830px 预览中约为 14.3px，移动端的项目名与定位约为 49.5px 和 11.8px。关键交付字段也在 Markdown 中提供文字说明。

## Motion

右侧校样从检查到确认，呼应封面展示的风格推荐过程。左侧字标和定位、右侧的推荐文字全程保持可读。

| 时段 | 动作 |
| :-- | :-- |
| 0–0.65 秒 | 展示完整的校样 |
| 0.65–2.03 秒 | 勾号淡至底稿，校对线从页首扫向推荐结果 |
| 1.97–2.85 秒 | 勾号沿原路径重绘，四个定位角短暂框出结果 |
| 2.85–4.50 秒 | 回到完整校样，停留后循环 |

由原 SVG 逐帧渲染，用 FFmpeg 编成 1120 × 476、16 fps 的 [浅色 GIF](hero-light.gif)和[深色 GIF](hero-dark.gif)，每版约 99 KiB。首尾帧均为完整封面。README 根据主题选择 GIF。启用减少动态效果时使用对应主题的静态 SVG。

## 源文件与重建

封面的可编辑源为 [浅色](src/hero-light.src.svg)和[深色](src/hero-dark.src.svg) SVG。[分镜配置](src/demo.json)包含两条提示词、交付字段和两套配色。动画 SVG 为减少动态效果偏好的读者提供静态状态，GIF 用于默认演示。

将 `Inter-850.ttf`、`Inter-650.ttf`、`SourceHanSansCN-Medium.otf` 和 `Monaco.ttf` 放进本地字体目录。可用 FontTools 把可变版 Inter 固定在对应字重。封面转换时用 `--font-map` 把 `wordmark`、`cjk` 和 `mono` 分别映射到 Inter 850、思源黑体与 Monaco。以下命令从仓库根目录运行。

```bash
python3 scripts/text_to_path.py assets/readme/src/hero-light.src.svg \
  --font /path/to/fonts/Inter-650.ttf --font-map /path/to/font-map.json \
  -o assets/readme/hero-light.svg
python3 scripts/text_to_path.py assets/readme/src/hero-dark.src.svg \
  --font /path/to/fonts/Inter-650.ttf --font-map /path/to/font-map.json \
  -o assets/readme/hero-dark.svg
python3 scripts/demo_storyboard.py build assets/readme/src/demo.json \
  --out assets/readme/demo --fonts-dir /path/to/fonts \
  --gif --gif-width 830 --fps 9 --gif-start final
python3 scripts/lint_svg.py assets/readme --strict
python3 scripts/render_preview.py assets/readme --github
```

| 分镜 | 浅色 GIF | 深色 GIF | 时长 |
| :-- | --: | --: | --: |
| 自动推荐 | 141 KiB | 136 KiB | 5.96 秒 |
| 只做素材 | 124 KiB | 118 KiB | 6.07 秒 |

## Review log

- 首版在 830px 和 360px 渲染后，字标的字母间隙偏紧。字距从 −11px 改为 −5px，拉开两行基线距离，将中文定位从 38px 放大到 42px。
- 增加演示素材后重跑分析脚本，推荐变为编辑海报。给封面说明和自动推荐演示补上「改版前」，保留本次排版选择的实际依据。
- 终版检查深浅两套在 GitHub 桌面与移动端宽度的渲染。两套封面使用同一组字段，标题与关键句无裁切。8 个 SVG 通过严格检查，四个 GIF 低于 142 KiB，首帧均为完整分镜。
