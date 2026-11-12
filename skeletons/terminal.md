<!--
骨架：终端型（配合 styles/terminal-neon.yaml）
特点：首屏即用法；视觉重量 L1；"开始"紧跟 hero。
使用：Agent 复制本模板，替换 {占位}，删除不适用的段落与所有注释。
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="{name}：{一句话定位}" src="assets/readme/hero-light.svg" width="100%">
</picture>

<p align="center">
  <!-- 徽章：最多一行，只放版本 / CI / 许可证 -->
  <a href="{release_url}"><img alt="version" src="https://img.shields.io/{registry}/v/{package}?style=flat-square&color={accent_hex}"></a>
  <a href="{ci_url}"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/{owner}/{repo}/{workflow}.yml?style=flat-square"></a>
  <a href="LICENSE"><img alt="license" src="https://img.shields.io/github/license/{owner}/{repo}?style=flat-square"></a>
</p>

```bash
{最常用的安装命令}
```

```console
$ {最小可运行命令}
{真实输出，≤ 6 行}
```

<details>
<summary>其他安装方式</summary>

```bash
{brew / cargo / go install / 二进制下载……}
```

</details>

## 为什么用 {name}

<!-- 最多 3 条，每条对应一个可验证的命令或对比 -->

- **{价值 1}**：{一句解释}
- **{价值 2}**：{一句解释}
- **{价值 3}**：{一句解释}

<!-- 可选：与替代工具的对比，用代码块并排而不是表格 -->

```bash
# 以前
{替代方案的写法}

# 现在
{name 的写法}
```

## 用法

```text
{真实的 --help 输出，可截取主要部分}
```

### 常见场景

<!-- 每个场景 = 一句话目标 + 一个代码块 -->

**{场景 1}**

```bash
{命令}
```

**{场景 2}**

```bash
{命令}
```

## 配置

<details>
<summary>完整配置项</summary>

| 选项 | 默认值 | 说明 |
| :-- | :-- | :-- |
| `{key}` | `{default}` | {说明} |

</details>

## 兼容性与限制

- 平台：{macOS / Linux / Windows}
- 依赖：{运行时版本}
- 不做什么：{非目标}

## 参与贡献

{贡献方式，链接到 CONTRIBUTING.md}

## 许可证

{保留原有许可证声明}
