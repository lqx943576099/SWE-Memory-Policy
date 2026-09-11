# 与 GitHub 旧版本的同步差异

核对日期：2026-09-11。比较基点：
`1edd2a9fe0ab774a701cd9cf73e280b28c61f91c`（此前 main）。

结论：旧 GitHub 渲染代码与本机 recent3 实验代码不一致。

| 范围 | 旧 GitHub | 本次同步 |
|---|---|---|
| 原生 Responses 观察 | 主要为早期 chat/OA 历史接口 | 增加严格调用 ID 配对和最近 OA 窗口分区 |
| 视觉排版 | 基础黑白文本页和组合画布 | 同步 compact 类型分类、标题/路径徽标、结构化正文与回退 |
| 清理规则 | 无当前 compact 组件树 | 同步终端清理、Python 注释/docstring、空白、blame 时间策略 |
| 倍率 | 早期 fixed/dynamic composition | 同步线性缩放和视觉 Token 目标缩放函数 |
| 使用入口 | 需要外部 adapter | 新增离线 `swe-memory-render` / `python -m swe_memory_policy.offline` |
| 文档 | 早期策略说明 | 更新输入、输出、recent3、倍率区别、Token 下限及隐私边界 |

本机权威源为 `luna-recent3-cacheaware-stratified20/SWE-Memory-Policy`，
在线集成参考相邻 `image-memory/src/image_memory/proxy.py` 和 `conditions.py`。
不是采用较旧的主仓库嵌入副本，也不把远端早期文件覆盖回实验工作树。

同步的 renderer、parsing、structured_text、python_compact、path_records、
terminal_sanitize、rendering 和 history 核心文件均保持本机字节；
新增 offline adapter 只负责输入适配、窗口选择、调用现有渲染/缩放函数和保存 manifest。
包级 `__init__.py` 额外保留旧公共接口兼容导出。

只同步源代码、测试、人工示例和说明文档。没有上传代理配置、密钥、请求、实验轨迹、
数据集、PNG、字体二进制或运行器，也没有修改任何已有实验结果。
