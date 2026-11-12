<!--
骨架：文档型（配合 styles/swiss-grid.yaml）
特点：克制、规格书式；视觉重量 L1（字标 hero），架构复杂时 L2 加一张架构图；
     大量使用原生 Markdown 结构（导航行、表格、details、Mermaid）。
使用：Agent 复制本模板，替换 {占位}，删除不适用的段落与所有注释。
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="{name}：{一句话定位}" src="assets/readme/hero-light.svg" width="100%">
</picture>

<p>
  <a href="#安装">安装</a> ·
  <a href="#快速上手">快速上手</a> ·
  <a href="#api">API</a> ·
  <a href="{docs_url}">文档</a> ·
  <a href="#对比">对比</a>
</p>

<!-- 徽章：一行，左对齐 -->

---

## 概览

{2–3 句话：它是什么、解决什么问题、核心设计原则。}

| | |
| :-- | :-- |
| **适用于** | {场景} |
| **不适用于** | {非目标} |
| **运行环境** | {Node 18+ / Python 3.9+ / …} |
| **依赖** | {零依赖 / 列出关键依赖} |

## 安装

```bash
{包管理器安装命令}
```

<details>
<summary>其他包管理器</summary>

```bash
{pnpm / yarn / bun / pip / poetry……}
```

</details>

## 快速上手

```{lang}
{≤ 10 行最小示例}
```

{一句话解释示例做了什么，以及输出是什么。}

## 核心概念

<!-- 每个概念一个三级标题 + 一段解释 + 可选代码。概念 ≤ 5 个。 -->

### {概念 1}

{解释}

### {概念 2}

{解释}

<!-- L2：架构复杂时使用 Mermaid；需要品牌一致性时改用 assets/readme/architecture.svg -->

```mermaid
flowchart LR
  A[{输入}] --> B[{核心模块}] --> C[{输出}]
```

## API

<!-- 只列最常用的 API；完整参考链接到文档站 -->

| API | 说明 |
| :-- | :-- |
| `{fn}(…)` | {说明} |

完整 API 见 [{docs_url}]({docs_url})。

## 对比

<!-- 只写可验证的差异；不写主观评价。没有可靠对比时删除本节。 -->

| | {name} | {替代方案 A} | {替代方案 B} |
| :-- | :-: | :-: | :-: |
| {特性} | ✓ | ✗ | 部分 |

## 生态

- [{插件 / 集成}]({url})：{说明}

## 参与贡献

{贡献方式}

## 许可证

{保留原有许可证声明}
