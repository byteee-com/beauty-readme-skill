<!--
骨架：海报型（配合 styles/editorial-poster.yaml）
特点：大 hero 建立第一印象；证据（截图 / 作品）前置；视觉重量 L2，可用章节条。
     章节条与 hero 共用同一字体、配色与构图语言。
使用：Agent 复制本模板，替换 {占位}，删除不适用的段落与所有注释。
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="{name}：{一句话定位}" src="assets/readme/hero-light.svg" width="100%">
</picture>

<p align="center">
  <b>{一句话定位（与 hero 一致，便于搜索）}</b>
</p>

<p align="center">
  <a href="{demo_url}"><b>在线体验</b></a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="{docs_url}">文档</a>
</p>

<!-- 证据前置：真实截图或真实作品，宽图一张，或两列表格 -->

<p align="center">
  <img alt="{截图描述：画面中展示了什么}" src="assets/readme/screenshot-main.png" width="100%">
</p>

<!-- L2 章节条：assets/readme/section-{slug}.svg，1280×200 -->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/section-what-dark.svg">
  <img alt="它能做什么" src="assets/readme/section-what-light.svg" width="100%">
</picture>

<!-- 每条价值配一张小图或截图；没有素材时只用文字，不要用插画填充 -->

<table>
  <tr>
    <td width="50%" valign="top">
      <img alt="{功能 1 截图描述}" src="assets/readme/feature-1.png" width="100%">
      <h3>{功能 1}</h3>
      <p>{一句解释}</p>
    </td>
    <td width="50%" valign="top">
      <img alt="{功能 2 截图描述}" src="assets/readme/feature-2.png" width="100%">
      <h3>{功能 2}</h3>
      <p>{一句解释}</p>
    </td>
  </tr>
</table>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/section-start-dark.svg">
  <img alt="快速开始" src="assets/readme/section-start-light.svg" width="100%">
</picture>

## 快速开始

<!-- 面向非开发者时，先给"下载 / 在线使用"，再给源码运行方式 -->

**直接使用**：{下载链接 / 在线地址}

**从源码运行**：

```bash
git clone https://github.com/{owner}/{repo}
cd {repo}
{安装与启动命令}
```

> [!NOTE]
> {需要的 API Key、环境变量或系统要求，没有则删除}

## 案例 / 谁在使用

<!-- 只放真实案例并附链接；没有则删除本节，不要编造 -->

- **[{案例}]({url})**：{一句话说明}

## 工作原理

<!-- 可选：Mermaid 或 assets/readme/how-it-works.svg -->

{简短说明}

## 路线图

- [x] {已完成}
- [ ] {计划中}

## 参与贡献

{贡献方式}

## 许可证

{保留原有许可证声明}
