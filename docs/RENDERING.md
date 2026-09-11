# 渲染流程与倍率定义

## 边界

输入是已经产生的工具观察，不是要执行的命令。工具名和参数只用于分类、定位路径。
适配器不调用模型，不执行 Bash，不读取命令中指向的源码文件，也不修复或重跑任务。
输出是本地 PNG 与审计 manifest，不是新的 Responses 请求。

```text
单条 content / Responses input / mini-SWE-agent messages
  → 工具调用与返回配对、OA 分组（单条观察跳过窗口选择）
  → 最近 N 组保留文本索引；更早的观察进入渲染
  → CompactObservationInput（compact_visual_whitespace_v2）
  → compact 解析与分类
      成功：标题 / 状态 / 正文区块 / suffix → 自适应宽度 PNG
      无法识别或 HeaderOverflowError：按源行排版分页 PNG
  → 保存 1× 基础页
  → 从基础页独立生成每种倍率，绝不反复缩放上一档
  → manifest：来源哈希、分类、尺寸、目标及实际估计 Token 比例
```

## compact 组件

核心实现位于 `image_response_rencent3text/tools/`。沿用本机的拼写 `rencent3`，
它是包路径，不代表另一套策略。

| 组件 | 行为及回退边界 |
|---|---|
| 包装解析 | 识别完整/截断的 mini-SWE 工具返回；拆出状态、正文与尾部。无法识别时返回外层按行渲染。 |
| 终端清理 | 处理 ANSI 和终端控制序列，记录清理信息。它不是对任意乱码的语义修复。 |
| 路径记录 | 优先识别检索结果与路径/行号记录；借助工具参数解析项目内路径和标题徽标。普通字符串不是路径就不任意改写。 |
| 截断正文 | 保留已有 head/tail、警告及省略信息，不猜测被截断部分。 |
| Python | 高置信识别后进行词法/结构处理；完整结构可生成 `{}` 等视觉标记，无法确认的代码结构保守回退。 |
| 注释与文档串 | 图片副本删除 Python 注释；仅 AST 确认为模块、类、函数 docstring 的文本被删除，普通三引号字符串保留。 |
| 换行与空白 | 硬换行可显示为 `⏎`；压缩连续空白，长填充或二进制样式空白用含计数的 PAD 标记代替。不是将全部空格全局删除。 |
| Git blame | 仅对满足识别规则的时间戳进行省略，并记录数量；不全局删除日期/数字。 |
| 结构化文本 | 单独分类 diff、traceback、pytest、JSON、listing、log、shell、empty/error/text；表格和矩阵可保留布局。 |
| 布局 | 宽度候选 768/1152/1536，标题保留 OA/Tool 与路径信息，关键内容采用更宽的最低档；高度按实际内容计算。 |
| 字体 | 记录字体指纹，缺失字形按核心策略呈现码点；没有可用字体时报错。 |

外层按行回退使用 `build_responses_observation_image_block` 和 `render_text_pages`，
与在线 proxy 的 compact-or-fallback 分支一致。终端清理仍可能发生，因此这里的
“保留源行”指排版策略，不是宣称 PNG 包含原始控制字节。

## 视觉 Token 历史估计器

`estimate_high_detail_visual_tokens` 原样同步，版本名为
`openai_high_detail_tiles_v1`，用于重现本机实验口径，**不是厂商当前模型计费保证**。

1. 当宽或高超过 768 时，先把短边映射到 768，再把长边限制到 2000。
2. 按 512×512 的 tile 向上取整。
3. `estimated_tokens = 85 + 170 × columns × rows`。

这些常量及先后顺序是本机实现的事实；不要擅自换成另一模型的 patch/tile 公式后仍声称
复现同一实验。需要新的估计器时应单独命名和验证。

Token 目标缩放的宽度候选为 `{原宽, min(原宽,512), min(原宽,768)}`，
高度候选同理。对最多 9 组尺寸，依次最小化：

1. 与 `基础页估计 Token / 倍率` 的绝对差；
2. 相对原始宽高比的失真；
3. 面积的负值（即优先保留更多像素）。

该选择不是严格预算上限，也不一定保持宽高比。单 tile 的最低估计为 255 Token，
所以小图即使目标为 10×，实际比例仍可能为 1。不同目标出现相同 PNG 是允许的，
应检查 manifest 中的 `target_visual_tokens`、`estimated_visual_tokens` 和
`achieved_visual_token_ratio`，不要只看文件夹名。

`linear` 则固定宽高分别除以倍率，最小为 1 像素；两种模式都从基础页使用 LANCZOS
派生，输出都是完整页面的缩小图，不裁剪成部分内容。

## 可复现性与隐私

- 固定核心源文件、Pillow/fonttools 版本、字体文件和输入才能比较 PNG 哈希。
- 输入轨迹需要包含原生文本；只剩图片或不可见加密历史时不声称可恢复原始观察。
- manifest 的源哈希用于审计，不能靠哈希恢复原文。
- 不自动上传生成物。PNG、路径标题和审计字段仍可能包含私有项目内容。
- 本次适配器不包含线上 cache、状态卡、blank ablation、模型 API 或任务调度器。

## 兼容说明

原 GitHub 的 composition 模块保留；原包级 `compose_*`、`render_flat_history` 和
`render_oa_display` 导出通过兼容模块保留。recent3 新入口不使用这些旧布局。
历史 `swe_memory_policy.history.render_flat_history` 直接子模块导入应改为包级导入，
或导入 `swe_memory_policy.legacy`。核心 history 文件保持本机版本。
