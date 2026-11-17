<!--
骨架：便当型（默认配合 styles/bento-grid.yaml）
特点：hero 本身就是特性总览；正文用不等宽的两列表格延续"格子"节奏；
     适合有多个并列卖点（运行时、集成、插件）的框架 / 平台 / SDK。
使用：Agent 复制本模板，替换 {占位}，删除不适用的段落与所有注释。
-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="{name}：{一句话定位}。格子里依次是：{格子 1 内容}、{格子 2 内容}……" src="assets/readme/hero-light.svg" width="100%">
</picture>

<!-- hero 里的格子文字必须在 alt 或下方正文中复述，便于搜索与读屏 -->

**{name}** {一句话定位，补全 hero 里没写下的那半句}

[快速开始](#快速开始) · [示例](#示例) · [集成](#集成) · [文档]({docs_url})

## 快速开始

```bash
{安装命令}
```

```{lang}
{≤ 10 行最小示例，与 hero 代码格一致}
```

## 特性

<!-- 不等宽两列：重要的放宽格（约 60%），次要的放窄格（约 40%）；每行左右交换宽窄 -->

<table>
  <tr>
    <td width="60%" valign="top">
      <h3>{最重要的特性}</h3>
      <p>{一句解释}</p>

```{lang}
{一段真实代码，≤ 6 行}
```

</td>
    <td width="40%" valign="top">
      <h3>{特性 2}</h3>
      <p>{一句解释}</p>
    </td>
  </tr>
  <tr>
    <td width="40%" valign="top">
      <h3>{特性 3}</h3>
      <p>{一句解释}</p>
    </td>
    <td width="60%" valign="top">
      <h3>{特性 4}</h3>
      <p>{一句解释}</p>
      <!-- 可放截图局部：<img alt="…" src="assets/readme/feature-4.png" width="100%"> -->
    </td>
  </tr>
</table>

## 示例

<!-- 链接到仓库里真实存在的 examples/ 子目录；没有则删除本节 -->

| 示例 | 说明 |
| :-- | :-- |
| [`examples/{name}`](examples/{name}) | {一句话} |

## 集成

<!-- 只列真实存在的适配器 / 插件，每项附包名或路径 -->

| 平台 | 包 | 状态 |
| :-- | :-- | :-- |
| {Node} | `{pkg}` | {稳定 / 实验} |

## 参与贡献

{贡献方式}

## 许可证

{保留原有许可证声明}
