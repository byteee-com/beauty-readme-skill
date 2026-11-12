# README 动效与 GIF

**默认不加动效。** 用户明确要求，或风格卡 `motion.default: true` 且用户没有拒绝时，才考虑动效。

## 1. 先判断：要不要动

是否加动效，看**动效是否表达了概念里的关键状态变化**，跟手上有什么模型无关。

| 问题 | 不满足时 |
|---|---|
| 概念里有没有一个"之前 → 之后"的瞬间？（盖章、抵达、通过闸口、构建变绿） | 不动 |
| 去掉动效后，读者是否少理解了一件事？ | 不动，动效只是装饰 |
| 只动一处时，这处是不是全图的焦点？ | 改动焦点，或不动 |

**一张 README 最多一处动效，通常放在 hero。** 流程图、架构图是用来读的，保持静态。

## 2. 硬性规则（SVG 和 GIF 都适用）

1. **最终帧 = 完整的静态设计。** 不播放动画的客户端（npm、PyPI、社交卡片、部分渲染器、RSS）看到的就是成品。
2. **GIF 的首帧也必须能单独看懂。** npm、PyPI 和社交卡片只显示 GIF 首帧，GitHub 加载时也先显示首帧。
3. 关键信息不能只在动画中途出现。
4. 必须有 `prefers-reduced-motion` 降级，降级后直接显示最终帧。
5. 写进 DESIGN.md 的 `Motion` 段：时间轴（时刻 / 元素 / 动作）、为什么动、降级方式、体积。

## 3. 选路线

| 要动的东西 | 路线 | 条件 |
|---|---|---|
| 文字、结构、状态（印章、路线流动、闸口亮起、打字、步骤高亮） | **SVG + CSS `@keyframes`** | 默认路线 |
| 路径变形（CSS 做不到） | SVG + SMIL | 仅在必要时 |
| 角色、材质、产品主体的有机运动 | **生成 GIF** | 检测到 GIF 生成能力，且风格卡 `allows_gif: true` |
| 真实产品操作、每条 prompt 的真实效果 | **演示 GIF**（见第 6 节） | 有真实录屏或截图 |
| 超过 15s 的演示 | MP4（上传到 issue 或 release 后链接） | — |

能力检测分两项（见 SKILL.md 第 3 节）：**静态生图**和 **GIF 生成**是两种能力，有静态生图不等于能出 GIF。**没检测到就当作没有**，不要猜，也不要让用户手动去别的工具里生成。

## 4. SVG 动效规范

默认参数：

- **只播一次**，总时长 ≤ 2s；用户明确要求时才循环（循环仅限光标、指示灯这类小元素）。
- 单个元素 150–500ms。
- 只动 `transform` 和 `opacity`，不动布局属性和滤镜。
- 用 `animation-fill-mode: both`，起点状态写在 keyframes 里；**元素本身的静态属性就是最终帧**。这样 reduced-motion 只需要 `animation: none`。
- 动画 class 放在**外层 `<g>`** 上，不放在 `<text>` 上。文字转路径时 `<text>` 会被替换，外层分组和 class 会保留。
- 元素本身已有 `transform` 属性（如 `rotate`）时，再包一层 `<g>` 承载 CSS transform，避免 CSS 覆盖原有旋转。

```svg
<style>
  .mv-route { transform-box: fill-box; transform-origin: left center;
              animation: mv-draw .8s cubic-bezier(.4,0,.2,1) both; }
  .mv-stamp { transform-box: fill-box; transform-origin: center;
              animation: mv-stamp .5s cubic-bezier(.2,.8,.3,1.2) 1.25s both; }
  @keyframes mv-draw  { from { transform: scaleX(0); } to { transform: scaleX(1); } }
  @keyframes mv-stamp { 0% { opacity: 0; transform: scale(1.5); }
                        60% { opacity: 1; transform: scale(.96); }
                        100% { opacity: 1; transform: scale(1); } }
  @media (prefers-reduced-motion: reduce) { .mv-route, .mv-stamp { animation: none; } }
</style>

<line class="mv-route" … />
<g class="mv-stamp">
  <g transform="rotate(-9 1088 392)"> … </g>   <!-- 原有旋转保留在内层 -->
</g>
```

### 打字效果

用 `clip-path` 或逐字 `<tspan>` 透明度实现，不用 JS。逐字字符数 ≤ 40，超过就改成逐行出现。`steps(n)` 的 n 等于字符数，等宽字体效果最好。

## 5. 生成 GIF（AI 生成）

前提：检测到 GIF 生成能力，风格卡 `allows_gif: true`（默认只有 `editorial-poster`）。

1. **GIF 只做动态层**：角色、材质、氛围。关键文字（项目名、命令、字段）留在 Markdown 或 SVG 里，因为生成模型逐帧渲染的文字会漂移。
2. 先定首帧，并确认首帧单独成立，再生成动画。
3. 浅色、深色各一版，或用透明背景，用 `<picture>` 切换。
4. 体积：hero ≤ 2MB，单图上限 5MB；超出就降帧率、缩尺寸或缩短时长。**交付时报告实际体积。**
5. 在 DESIGN.md 记录提示词、所用工具和参数，便于复现。
6. 不生成真实人物，不冒充真实产品界面。

## 6. 演示 GIF（证据类）

"每条 prompt 实际会产生什么效果"属于**证据**，不是插画。要求文字逐字准确，所以：

| 方案 | 何时用 |
|---|---|
| **确定性分镜**（默认） | 输入输出可以从 README、源码、文档或测试中逐字取到。不用录屏，提示词改了重跑即可 |
| 真实录屏 | 用户已有录屏，或需要展示真实界面的视觉细节：`vhs`（终端）、`asciinema` + `agg`、屏幕录制后用 `ffmpeg` 转换 |
| AI 生成 GIF | **不用于演示**，文字会漂移，也等于伪造证据 |

### 6.1 用 `scripts/demo_storyboard.py` 生成分镜演示

1. `demo_storyboard.py extract README.md -o assets/readme/src/demo.json`：从 README 代码块抽出提示词，生成草稿。
2. Agent 按项目文档补全每段：
   - `title`、`summary`（写进 `<desc>`）；
   - `reply`：`line`（标签 + 值）、`grid`（多栏字段）、`rule`（分隔线）；
   - `footer`：结尾一行，可设为可复制指令样式（`command: true`），可加印章（`stamp`）。
   - **字段名称、顺序、状态值必须来自源码或文档**；数值用明显的示例值（`owner/repo`、`@you`）。
   - `themes` 与 `fonts` 沿用 DESIGN.md 的 token；中文版另建一份分镜，设置 `suffix: "-zh-CN"`、`lang`，并在 `fallback` 里加入 CJK 字体。
3. `demo_storyboard.py build demo.json --out assets/readme/demo --fonts-dir <dir> --gif`：
   - `gif/<id>{suffix}-{light,dark}.gif` 是 **README 里用的主格式**：无限循环，从打字开始播放，结尾在最终帧停留 3 秒（`--gif-hold`）后重播。演示模拟的是录屏，只播一次的话，用户滚动到演示位置时动画往往已经播完。
   - 同时输出浅色、深色动画 SVG：文字转路径、相同字形只定义一次（中文 ≈ 60–80KB），只播一次，静态状态就是最终帧。它们是源文件，也是静态兜底。
   - `--gif-start final` 让首帧就是最终画面，适合只显示首帧的平台（npm、PyPI、社交卡片）；要发到这些平台时单独出一份。
   - 体积：每个 GIF ≤ 1MB（960px、10fps、64 色时约 0.4–0.9MB）；超出就降 `--fps`、`--gif-width`，或缩短回复。
4. 卡片页眉固定显示 `label`（默认 `ILLUSTRATIVE · EXAMPLE VALUES`）；README 第一个演示下方再加一行说明，并链接字段出处。
5. 在 README 里，每个演示放在对应提示词代码块的**下方**（代码块保留，方便复制），用 `<picture>` 切换浅色、深色 GIF。
6. 在 DESIGN.md 记录：每段的提示词、字段出处（文件:行）、体积、重建命令。

- 演示是第 1 节"一张 README 最多一处动效"的例外：它们是证据，放在正文里，每条提示词一段。
- 每段演示对应一条真实 prompt 或命令；画面里的 prompt 文本和输出字段必须与源码或文档一致，在 DESIGN.md 标出处。
- 每段 ≤ 15s。循环 GIF 的首帧是 prompt 卡片的开头；只显示首帧的平台用 `--gif-start final` 版本。
- 第 2 节"首帧必须能单独看懂"在这里的含义：README 里的循环版允许首帧从空白开始，因为同一张卡片下面就是提示词代码块；发到只显示首帧的平台的版本必须用最终帧作为首帧。
- 多条 prompt 时，每条一个短 GIF，放在 `<details>` 或表格里，不要拼成一个长 GIF。
- 仓库里没有可录的真实效果时，在交付说明里列为"缺失的证据"，不要补画假的。

转换参考：

```bash
ffmpeg -i in.mp4 -vf "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" out.gif
```

始终保留一份静态 SVG 或 PNG 作为可编辑源，以及不支持动图时的回退。
