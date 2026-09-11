# SWE-Memory-Policy

将编码 Agent 的历史工具观察渲染为 PNG，并按**视觉 Token 目标比例**或**宽高倍率**缩小。
不调用 LLM、不执行工具、不需要 API 密钥。默认保留最近 3 组 OA 为文本，仅渲染更早的观察。

本仓库的 compact 核心同步自本机 recent3 实验工作树（2026-09-11）。
原始观察不被改写；清理、去注释、路径简写等仅作用于图片中的视觉副本。
**compact 模式不是逐字无损编码**，不要将图片或视觉转录当作原始轨迹。

## 安装

Python >= 3.11，依赖 Pillow 11.3.0、fonttools 4.59.0。

```bash
python -m pip install -e ".[test]"
```

需要本机字体。默认查找 Cascadia Mono、Noto Sans CJK 和 DejaVu；也可指定已有字体：

```bash
export IMAGE_MEMORY_FONT_PATHS="/path/to/DejaVuSansMono.ttf:/path/to/NotoSansCJK-Regular.ttc"
```

字体缺失会报错，缺少的 Unicode 字形按核心实现使用可审计的码点标签。
相同 PNG 需要相同代码、依赖和字体文件，不能只固定字号。仓库不分发字体二进制。

## 快速开始

示例全部为人工构造，不含真实任务轨迹：

```bash
# 显式选中的单条观察：始终渲染，不应用 recent 窗口
swe-memory-render examples/observation.json --output-dir artifacts/example \
  --scale-mode token --factors 1 2 2.5 4 5 10

# 从完整轨迹选择早于最近 3 组 OA 的观察
swe-memory-render /path/to/task.traj.json --output-dir artifacts/history \
  --recent 3 --scale-mode token --factors 1 2 4 8 10

# 复现 clean_4p0 等宽高缩放语义
swe-memory-render /path/to/request.json --output-dir artifacts/linear \
  --recent 3 --scale-mode linear --factors 1 2 2.5 4 5 10
```

也可运行 `python -m swe_memory_policy.offline`，参数相同。
输出目录必须不存在，防止覆盖历史产物。使用 `--recent 0` 渲染所有已完成 OA。

### 输入格式

1. UTF-8 `.txt`：一条完整观察字符串，缺少工具名称/命令时无法利用命令辅助分类。
2. JSON 单条观察：见 [examples/observation.json](examples/observation.json)，
   `content` 是工具返回文本；可含 `<returncode>`、`<output>` 等原生包装。
3. Responses 请求：`{"input": [...]}`，或包含 `transformed_request.input` 的快照；
   按 `function_call.call_id` 与 `function_call_output.call_id` 匹配。
4. mini-SWE-agent Responses 轨迹：`{"messages": [...]}`；
   展开 `object="response"` 的 `output`，保留工具返回的因果顺序。

recent 的单位是 OA 工具批次，不是单个工具或单条 message。并行批次整体保留或整体渲染。
重复 ID、缺失结果、非文本结果会报错，不猜测配对。
完整轨迹尾部只有调用、没有返回的未完成批次会跳过，并写入
`ignored_terminal_call_ids`；这不代表这些调用已经执行成功。
仅保存压缩后图片的历史无法自动恢复原始文本。

### 输出

```text
output/
  base/OA0001_Tool001_p001.png
  token_2p1/OA0001_Tool001_p001.png
  token_5p2/OA0001_Tool001_p001.png
  manifest.json
```

目录倍率使用精确分数：`2p1` = 2/1，`5p2` = 5/2 = 2.5。
manifest 包含 OA/工具位置、分类、原始观察 SHA256、图片相对路径与 SHA256、
源尺寸、输出尺寸、目标 Token、估计 Token 和实际估计比例。
最新文本窗口只记录索引；不会导出原始请求、推理密文或修改后的模型请求。
图片及 manifest 本身仍可能包含私有代码/路径，**不要自动提交这些生成物**。

## 两种倍率不可混用

| 模式 | X 倍的定义 | 与本机在线条件的关系 |
|---|---|---|
| `linear` | 宽、高分别除以 X；整数向下取整，最小 1 像素 | clean_1p0 / 2p0 / 2p5 / 4p0 / 5p0 / 10p0 |
| `token` | 目标为 1× 页面估计视觉 Token 的 1/X | 本机在线注册 clean_token2p0；离线复用同一函数支持其他正倍率 |

8× 在离线命令中可用，但不因此声称本机曾注册或完成在线 clean_8p0 实验。

Token 模式原样使用本机 `openai_high_detail_tiles_v1` 历史估计器和候选尺寸选择。
它不是所有模型的通用计费公式，也不保证供应商实际 Input 精确下降 1/X。
候选尺寸按“与目标 Token 的差距最小 → 宽高比失真最小 → 面积最大”选择，
可能不保持宽高比。由于离散分档和最小 Token 下限，不同倍率可能得到同一尺寸。
以 `achieved_visual_token_ratio` 为准；细节见 [渲染流程与限制](docs/RENDERING.md)。

## Python 调用

```python
import json
from fractions import Fraction
from pathlib import Path
from swe_memory_policy.offline import render_history

value = json.loads(Path("examples/observation.json").read_text())
manifest = render_history(
    value, Path("artifacts/python"),
    factors=(Fraction(1), Fraction(2), Fraction(5, 2)),
    scale_mode="token",
)
```

底层 `render_compact_observation`、`render_text_pages`、
`downscale_png_to_visual_token_ratio` 和历史解析接口继续可单独使用。
旧的 fixed/dynamic composition 保留为兼容接口，但不属于 recent3 clean 流程。

## 验证与来源

```bash
python -m pytest
ruff check src/swe_memory_policy/offline.py tests/test_offline.py
```

布局断言以实验的 Cascadia Mono 为第一字体；只使用 DejaVu 时部分宽度/高度断言会不同。
本次使用实验镜像字体、Pillow 11.3.0 和 fonttools 4.59.0 验证：88 项测试通过。
字体不打包上传，部署时需自行提供相同文件。

- [同步来源与边界](PROVENANCE.md)
- [渲染组件、缩放算法、回退策略](docs/RENDERING.md)
- [与旧 GitHub 版本的差异](docs/SYNC_REPORT.md)
- [核心源文件指纹](docs/LOCAL_SOURCE_MANIFEST.json)

仓库不含模型凭据、API 代理、Docker 调度器、数据集、实验轨迹或生成图片。
