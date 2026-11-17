<!--
骨架：论文型（默认配合 styles/academic-paper.yaml）
特点：论文元信息前置（论文 / 项目页 / 数据 / 权重链接），然后是 TL;DR、方法图、复现步骤、结果、引用；
     复现命令必须能在仓库中找到对应脚本或配置。
使用：Agent 复制本模板，替换 {占位}，删除不适用的段落与所有注释。
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="{论文标题}：{一句话贡献}" src="assets/readme/hero-light.svg" width="100%">
</picture>

<p align="center">
  <!-- 只放真实存在的链接；没有的删除 -->
  <a href="{paper_url}"><b>论文</b></a> ·
  <a href="{project_page}">项目页</a> ·
  <a href="{data_url}">数据集</a> ·
  <a href="{weights_url}">模型权重</a> ·
  <a href="#引用">引用</a>
</p>

<!-- 作者与机构：只写 CITATION.cff / 论文中的真实信息 -->
<p align="center">{作者 1}<sup>1</sup> · {作者 2}<sup>2</sup><br><sup>1</sup>{机构 1} · <sup>2</sup>{机构 2}</p>

> [!NOTE]
> {会议 / 期刊录用信息或 "预印本"；没有则删除}

## TL;DR

{1–2 句：问题、方法、主要发现。不写未在论文中报告的数字。}

## 方法

<!-- Figure 风格方法图：assets/readme/method-light.svg / method-dark.svg，或 Mermaid -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/method-dark.svg">
  <img alt="图 1：{方法图描述}" src="assets/readme/method-light.svg" width="100%">
</picture>

<sub>图 1. {图注：说明各部分含义}</sub>

## 复现

### 环境

```bash
{conda / pip / uv 安装命令}
```

### 数据

```bash
{下载或准备数据的真实命令}
```

### 训练 / 推理

```bash
{真实脚本与配置路径，例如 python train.py --config configs/xxx.yaml}
```

<details>
<summary>完整配置与超参数</summary>

| 参数 | 值 | 说明 |
| :-- | :-- | :-- |
| `{key}` | `{value}` | {说明} |

</details>

## 结果

<!-- 表格数值必须与论文一致并注明出处（Table N）；没有则删除本节 -->

| 方法 | {指标 A} | {指标 B} |
| :-- | --: | --: |
| {基线} | {值} | {值} |
| **{本文}** | **{值}** | **{值}** |

<sub>数据来自论文 Table {N}。</sub>

## 引用

```bibtex
{来自 CITATION.cff 或论文的 BibTeX，不要自行编造字段}
```

## 致谢

{保留原有致谢}

## 许可证

{保留原有许可证声明；代码、数据、权重许可证不同时分别列出}
