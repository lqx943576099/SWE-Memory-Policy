# 渲染流程、Token 预算与回退

## 1. 输入与 recent3 窗口

工具已经执行完毕，本库只处理它的返回文本。命令字符串用于辅助识别内容和来源路径，
不会被执行，也不会读取命令指向的文件。

Responses 的调用和返回按 `call_id` 严格配对，再按 OA 工具批次分组。
最近 3 组完整 OA 保留文本索引；更早的观察各自生成图片。并行工具调用共享一次 OA 分组，
不会把一个并行批次拆成半文本、半图片。显式单条 `content` 输入直接渲染，跳过窗口选择。
没有 overlap 截断、历史去重替代、编辑阶段清理或历史链删除策略。

重复调用 ID、缺失的中途返回、非文本结果属于输入错误，不推测配对。
mini-SWE 轨迹最后只有调用而无返回的未完成批次会被跳过，ID 写入
`ignored_terminal_call_ids`；这不表示该调用成功。

## 2. 先解析协议，再按内容分类

主流程位于 `src/swe_memory_policy/image_response_rencent3text/tools/`。
包名沿用原实现的 `rencent3` 拼写。

解析器只识别**从开头到结尾完整匹配**的 mini-SWE 包装：可选 `exception`、
`returncode`、`output`；或 `warning` / `output_head` / `elided_chars` / `output_tail`
构成的已截断观察。正文中恰巧存在 XML 标签不会被当成外层协议。

分类顺序如下，优先命中的模块决定排版：

1. **grep / rg 路径记录**：命令和每条输出同时符合严格规则时，按文件连续分组。
2. **已截断输出**：显示 `Truncated output`、`Output head`、`Output tail`，不将 head/tail 拼成连续 Python。
3. **Python**：读取项目内 `.py` 文件的 `cat/sed/head/tail` 命令可确认；无此命令依据时，需要足够长的正文（至少 4000 字符或 80 行）并通过包含顶层函数 / 类的 AST 判断。显著的非 Python 输出有排除条件。
4. **一般结构化文本**：依次判断表格 / 矩阵、空输出、错误、diff、traceback、pytest、JSON、文件目录列表、日志、短 Shell 输出、普通结构化文本。

| 模块 | 标题与显示内容 |
|---|---|
| Python | `Prelude`、`Module`、`class X`、`X.method`、`def f`；完整 AST 不可用时为 `Python fragment` |
| 文件匹配记录 | `FILE ~/path`；每条显示行号、可选列号及视觉处理后的 payload；连续同文件才共用标题 |
| 截断 | 独立的说明、head 和 tail，不生成不可见的中间内容 |
| diff / traceback / pytest | 保留已识别类型，分别组织差异、异常或测试输出 |
| JSON / listing / log / shell / text | JSON、`Files / directories`、`Log`、`Shell output`、`Structured text` 等模块 |
| empty / error | 空输出或错误模块；非零 returncode 不被画成成功 |

Shell、Python 等是内容模块，不等同于工具名称。Bash 可以返回任意一种内容。
本代码没有独立的“协议统计失效后重试”模块；真实边界是包装解析、路径记录校验、
Python 词法 / AST 解析，以及下面的渲染回退。

## 3. Python 的 `{}` 与视觉清理

`compact_visual_whitespace_v2` 仅改变图片中的副本，输入字符串及其哈希保持原样。

- `tokenize` 确认真正的块冒号、INDENT/DEDENT 和单行 suite 后，用带生成标签的 `{}` 显示块边界。
  例如 `if ready:\n    return value` 的块可读作 `if ready: { return value }`。
  类与方法分区之间仍跟踪套件边界。
- 字典、集合以及 f-string 原有的 `{}` 仍属于源代码符号，不计入生成花括号配对统计。
- 完整代码可在已确认的结构边界闭合；不完整片段不会为了视觉“完整”而在 EOF 猜补闭合。
  词法解析失败时不插入结构 `{}`，保留可见行内容，去掉行首缩进并用 `⏎` 表示硬换行。
- `#` 注释须经 Python 词法识别后删除，字符串里的 `#` 保留。
  只有 AST 确认为模块、类或函数首部 docstring 的字符串才删除；赋值、返回值中的三引号字符串保留。
  AST 失败时不删除 docstring，但已经确认的词法注释仍可能去除。
- 修复了外层缩进与列 0 多行字符串并存时可能产生的错误 DEDENT 处理，不对未由 renderer 打开的套件生成闭合括号。
- ANSI / 终端控制序列、连续空白和确定的长填充可压缩；长填充使用带计数的 PAD 标记。
  git blame 时间仅在满足该记录类型的条件下省略，不全局删除数字或日期。

因此视觉转录不是可执行 Python，也不是逐字无损源代码。不要用它覆盖原始工具观察。

## 4. 路径如何替代与压缩

输入 `project_root` 与 manifest 的完整 `header` 记录 `project_root ≡ ~/` 对应关系。
图片的文件标题使用 `~/` 简写；图片顶部并不显示完整根路径和完整调用 ID。
例如根为 `/testbed`：

```text
命令：cat /testbed/src/example.py
标题：FILE ~/src/example.py
```

普通 Python 单文件读取只在文件标题中使用这个简写。`cat` 多文件时不能据此恢复多个文件边界；
本识别器只提取第一个符合条件的 `.py` 文件，因此示例使用单文件读取。

grep / rg 记录需要命令提供文件名和行号，所有输出行均可识别为
`路径:行号[:列号]:匹配内容`，路径可在项目根内定位，且没有不允许的 NUL / ESC。
实现对原记录逐字重建校验，通过后才将连续同文件的重复路径抽为 `FILE` 标题。
原顺序、行列号与原始 payload 保存在审计信息；图片中的 Python 匹配内容会按词法注释策略显示，
不能声称图片 payload 逐字无损。映射中记录原路径、显示路径及定位依据。
任一记录不满足要求就放弃路径专用排版，继续普通内容分类。

不对 Python 字符串、任意正文或根外路径做全局替换。
`rewrite_location_paths` 是独立辅助函数；一般 diff / traceback 的主渲染流程未调用它，
不能声称这些正文中的所有绝对路径都会被压缩。

## 5. 初始 1× 图片的宽与高

**先选阅读布局，再测量视觉 Token**。Token 预算不参与 1× 宽度档位选择。

- 宽度档为 **768 / 1152 / 1536 px**。
- Python、path records、diff、error、traceback、pytest 的最低宽度为 **1152 px**；其他类型最低为 768 px。
- 分别测量页标题、状态、尾部、模块标题与正文的最大自然行宽，计入相应内边距，取最大所需宽度。
- 从不低于类型最低宽度的档位中，选能容纳所需宽度的最小值；超过 1536 px 时使用 1536 px 并软换行。
- 直接在选中宽度上生成 PNG，字号 **18 px**。正文、标题均按实际行数增加高度；compact 页面高度自适应，不截掉尾部。
- 原有硬换行显示 `⏎`；渲染宽度造成的软换行不增加原文换行标记。

`visual_layout.width_selection` 记录候选档位、自然宽度、类型最低宽度和实际选中宽度，
可区分“原始排版宽度”与后续 Token 压缩得到的宽度。

## 6. 只按 Token 比例缩放

实现为 `vision_tokens.py`，估算器版本 **`luna_patch32_high_20260906_v2`**，
当前只接受 `model="gpt-5.6-luna"` 和 `detail="high"`。
它是一套冻结的实验 profile，不是对未知模型自动套用的通用计费器。
这些常量于 **2026-09-13** 对照 [OpenAI 图像 Token 文档](https://developers.openai.com/api/docs/guides/images-vision#patch-based-image-tokenization)核验；估算没有包含供应商实际返回的 usage。

对宽高 `(W,H)`：

1. 等比限制最长边至 **2048 px**，整数尺寸向下取整、至少 1 px。
2. 按 32×32 网格向上取整估算 patch 数；超过 **2500** 时，再等比压缩到 patch 预算内。
   实现用整数平方根及分数进行边界调整，避免浮点误差。
3. 估算 Token 为 `ceil(patch_count × 6/5)`。

其中第 1、2 步描述模型成本的**尺寸预处理估计**；它们不修改已生成的 1× 文件。

对每张基础页独立计算：

$$
T_1=\operatorname{estimate}(W_1,H_1),\quad
B_k=\left\lfloor T_1/k\right\rfloor,\quad
T_k\le B_k,\quad c_k=T_1/T_k.
$$

对 `k>1`，沿原宽高比的整数长边序列搜索（最长边不超过原图和 2048 px）：
短边为 `max(1, floor(原短边 × 新长边 / 原长边))`。
选无需进一步模型尺寸预处理、且估算 Token 不超过预算的最大长边。
由于 patch 数在这条序列上单调，二分搜索可找到预算内的最大值。

- `1×` 直接复制基础 PNG，字节不变。
- 其余档位各自从基础 PNG 使用 **一次 Lanczos** 缩放，不使用前一档结果。
- 不裁剪内容，不任意改变宽高比；整数短边取整会带来至多相应的像素舍入差异。
- 离散 patch 使不同倍率可能得到相同尺寸，或 `T_k < T_1/k`。
  使用 manifest 中的实际估算倍率，不把目录名当作实测压缩比。
- 极细长图也坚持 patch 预算，避免因二次尺寸预处理造成错误的“最大尺寸”选择。

核心字段：`baseline_visual_tokens`、`target_visual_tokens`、`token_budget`、
`estimated_visual_tokens`、`achieved_visual_token_ratio`、
`achieved_estimated_compression_factor`、`budget_satisfied` 和 `budget_slack_tokens`。
`provider_usage_measured=false` 明确表示没有发送模型请求测量账单 Token。

最低估算成本为 **2 Token**（1 个 patch 乘 6/5 后向上取整）。
预算低于 2 时，底层抛出 `UnattainableVisualTokenBudget`，不写入图片；离线入口记录
`status="unattainable_budget"`、`path=null`、`sha256=null` 和失败原因，继续其他可行档位。
顶层状态为 `partial`，CLI 在写好 manifest 后以退出码 2 结束；全部完成时为 `complete`，退出码 0。
没有“回退为超预算图片却仍然算作达到 k×”的分支。

## 7. 边界与回退一览

| 条件 | 实际行为 |
|---|---|
| 完整轨迹缺中途返回、重复 ID、非文本返回 | 报输入错误，不猜配对 |
| mini-SWE `messages` 轨迹末尾调用尚无返回 | 跳过末尾未完成批次，记录 ID；原生 Responses `input` 仍报错 |
| 不符合锚定观察包装 | 保留源行结构，分页渲染 |
| grep / rg 命令、路径、任一输出行或逐字重建不满足条件 | 放弃路径专用分支，继续普通分类 |
| 已截断包装 | 分开展示说明 / head / tail，不恢复省略正文 |
| Python AST 失败 | 使用片段方式，不删除未经 AST 确认的 docstring |
| Python tokenize 失败 | 不生成 `{}`；显示可见内容与硬换行标记 |
| 一般表格 / 矩阵需要保留布局 | 未发生可识别稀疏空白或 blame 压缩时，按源行回退 |
| 标题、代码行超宽 | 标题与正文软换行，高度增加，不截掉内容 |
| 字体缺少字形 | 用 `[[U+XXXX]]` / `[[U+XXXXXXXX]]` 显示码点并记录 |
| 没有可用字体 | 报错；若码点标签所需基本字形也不可用，同样报错 |
| 目标预算低于最低 Token | 记录不可达，不输出超预算档位 |
| 非支持模型 / detail、非法或重复倍率、已存在输出目录 | 报错，不静默切换配置或覆盖 |

源行回退使用 **2048 px** 宽、最高 **4096 px** 的页面，18 px 字号、25 px 行高；
长内容按行分页，终端控制序列仍可能清理。“按源行”是布局承诺，不是保存控制字节。
compact 标题按宽度换行、增加高度，不将普通长标题作为失败条件。

## 8. 可复现性

固定输入、源文件、Pillow / fonttools、字体字节及字体顺序，才可比较 PNG 哈希。
示例生成脚本为 [build_render_gallery.py](../scripts/build_render_gallery.py)，
输入 [render_gallery.json](../examples/render_gallery.json) 为人工构造，公开图库不是实验成功率证据。
图库 manifest 只记录字体名称和指纹，不公开本机路径，不包含模型请求。
真实输入生成的 PNG 与 manifest 仍可能包含项目私有内容，请按输入本身的权限管理。
