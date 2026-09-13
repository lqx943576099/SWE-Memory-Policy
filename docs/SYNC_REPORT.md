# 本次更新：统一为 Token 比例压缩

更新日期：2026-09-13。

| 范围 | 之前 | 现在 |
|---|---|---|
| 倍率定义 | 同时提供 Token 模式和宽高各除以倍率的模式 | 仅保留 Token 比例预算；删除 `--scale-mode` |
| Token 估算 | 历史 tile 估计器，选择最接近目标的有限候选尺寸 | 冻结 Luna/high patch v2，严格要求估算 Token 不超过 `floor(T₁/k)` |
| 尺寸选择 | 有限宽高候选可能改变比例或超过目标 | 保持原宽高比的整数序列，选预算内最大、无需二次预处理的尺寸 |
| 1× | 基础图可能经过重存 | 复制原 PNG，尺寸 / 像素 / 字节不变 |
| 不可达预算 | 可能仍输出超过目标预算的图片 | 保留基础图，单档记录 `unattainable_budget`；CLI 退出码 2 |
| Python 套件边界 | 外层缩进和列 0 多行字符串可触发错误的闭合边界 | 仅闭合已经确认并由 renderer 打开的套件 |
| 旧兼容代码 | fixed / dynamic composition、旧宽高策略等 | 移除不再使用的缩放和兼容分支 |
| 文档与展示 | 文字说明为主，无公开完整倍率图库 | 补充宽度选取、模块、`{}`、路径替代、边界表与同图 1–10× 图库 |

`offline.py` 负责输入适配、recent OA 选择和记录 manifest；`vision_tokens.py` 负责
冻结估算器和严格尺寸计划；compact 模块负责观察解析、分类和排版。
这些职责均不调用模型、不执行工具。

迁移示例：

```bash
# 统一入口；倍率指每张基础页估算视觉 Token 的压缩倍率。
swe-memory-render examples/render_gallery.json --output-dir artifacts/example \
  --factors 1 2 3 4 5 6 7 8 9 10
```

原来的 `--scale-mode linear` / `--scale-mode token` 均应去掉。
宽高缩放函数及旧缩放策略导入已删除，调用方应使用
`downscale_png_to_visual_token_ratio` 或离线 `render_history`。
历史宽高实验结果仍具有原来的定义，不能因代码更新而改称 Token 倍率结果。

本次只修改公开仓库的代码、测试、人工例子及文档。既有实验任务、结果目录、轨迹和
Docker 运行环境均未被覆盖或清理。

## 验证

Python 3.11 的独立虚拟环境、固定依赖和记录的字体下，**150 项测试通过**；
全仓 Ruff 检查通过，可编辑安装与 wheel 构建通过，wheel 中不含已删除的旧缩放模块。
公开图库包含 10 张真实 renderer 输出，逐一校验了尺寸、严格 Token 预算与 PNG SHA256；
图片、源码和字体指纹记录在图库 manifest 中。
