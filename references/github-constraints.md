# GitHub 渲染限制

生成任何 README 资产前必读。这些限制决定了"什么能做、什么做了也看不到"。

## 1. README 中的 HTML

GitHub 会对 Markdown 中的 HTML 做白名单过滤（sanitize）。

**可用**：`<p align="center">`、`<div align="center">`、`<img>`（`src` `alt` `width` `height` `align`）、`<picture>` + `<source media srcset>`、`<details>` / `<summary>`、`<br>`、`<sub>` / `<sup>`、`<kbd>`、`<table>` 系列、`<a href>`

**会被剥离**：`style` 属性、`<style>`、`<script>`、`class`、`id`（会被加 `user-content-` 前缀）、`<iframe>`、`<video>`（直接写标签；但上传到 issue 的视频链接可显示）、表单元素

结论：**README 本身没有 CSS**。所有视觉效果只能靠图片（SVG/PNG/GIF）和原生 Markdown 结构。

## 2. 通过 `<img>` 引用的 SVG

GitHub 通过 camo 代理以图片方式加载 SVG，相当于浏览器的"图片模式"：

| 特性 | 是否可用 | 说明 |
|---|---|---|
| SVG 内 `<style>` / CSS | ✅ | 可用，包括 `@media (prefers-color-scheme)` |
| CSS `@keyframes` 动画 | ✅ | 可用，是首选动效方式 |
| SMIL `<animate>` | ✅ | 可用，但优先 CSS |
| `<script>` / 事件 | ❌ | 完全不执行 |
| 外部字体（`@import`、`url()` 远程） | ❌ | 不会加载 |
| base64 内嵌字体 `@font-face` | ⚠️ | 可用但体积大，建议先子集化 |
| 外部图片 `<image href="https://…">` | ❌ | 不加载；必须 base64 内嵌 |
| `<foreignObject>` | ⚠️ | 部分浏览器可渲染但不稳定，**禁止使用** |
| 链接 `<a>` | ❌ | SVG 内链接不可点；用外层 Markdown 链接包裹整图 |
| `filter`（模糊、阴影） | ✅ | 可用，但大面积滤镜会拖慢渲染，适度使用 |

## 3. 字体策略（按优先级）

1. **文字转路径**（`scripts/text_to_path.py`）：最稳定，各平台一致；缺点是不可再编辑文字 → 保留一份 `*.src.svg` 源文件。
2. **子集化 base64 嵌入**：只嵌入用到的字形，控制在 30KB 以内。
3. **系统字体栈**：仅用于正文型小字，接受跨平台差异。
   - 无衬线：`-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif`
   - 等宽：`ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
   - 中文：`"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`

## 4. 尺寸与布局

- GitHub 内容区最大宽度约 **830–1012px**（取决于是否有侧栏）；移动端约 360px。
- hero 推荐 `viewBox="0 0 1280 640"`（2:1）或 `1280 480`；`<img width="100%">` 让其自适应。
- 关键文字在移动端缩到约 28% 时仍需可读：hero 主标题 ≥ 72px（在 1280 宽画布上），副标题 ≥ 32px。
- 章节标题图推荐 `1280 × 200`。
- 安全区：关键信息距边缘 ≥ 64px。

## 5. 深浅色

两种方式，按需选择：

**A. `<picture>` 切换两张图**（最可靠，推荐用于 hero）

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="…" src="assets/readme/hero-light.svg" width="100%">
</picture>
```

**B. SVG 内 `@media (prefers-color-scheme: dark)`**（单文件，适合简单图）

注意：方式 B 跟随的是**系统**偏好，而非 GitHub 的主题设置；用户在 GitHub 手动切主题时可能不一致。hero 优先用方式 A。

另：GitHub 支持在图片 URL 后加 `#gh-dark-mode-only` / `#gh-light-mode-only`，但已被 `<picture>` 方案取代，不推荐新项目使用。

## 6. 文件体积与缓存

- 单个 SVG 建议 < 200KB；含 base64 位图的混合 SVG < 1MB。
- GIF < 5MB（GitHub 上限 10MB，过大加载慢）。
- camo 会缓存图片；修改后若不刷新，可在文件名中加版本号（`hero.v2.svg`），不要用 query string。

## 7. 其他

- 相对路径基于 README 所在目录；在子目录 README 中注意路径层级。
- 锚点：标题自动生成锚点（小写、空格转 `-`、去除标点）；中文标题锚点保留中文。
- npm / PyPI / crates.io 渲染 README 时**不走 GitHub 规则**：相对路径图片可能失效。若项目会发布到包管理器，图片使用 `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/…` 绝对地址（这是仓库自身文件，不算外链图床）。
