# BV1mJ411r7ZB 高等代数 114 集批量处理方案

## 目标
B站「高等代数学-复旦大学-谢启鸿」114 集，每集生成独立笔记，再汇总成总笔记。

## 方式
纯音频模式（`--audio`），跳过帧提取和 OCR。

## 脚本
`scripts/batch_process.py`

### 第一阶段：114 集逐一处理

```
for ep in [1..114]:
  workspace = workspace/BV1mJ411r7ZB/ep{XX}/
  notes/ep{XX}.md 已存在 → 跳过（续跑）
  否则 → 下载音频 → ASR → LLM(DeepSeek) → 输出 ep{XX}.md
```

- 每集独立 workspace 隔离
- 单集失败 try/except 继续下一集
- 预计 114 × ~6min = ~12 小时

### 第二阶段：分层合并总笔记

```
Layer 1 (每组 ~20 集):
  ep01~ep20 → LLM → summary_1.md
  ep21~ep40 → LLM → summary_2.md
  ep41~ep60 → LLM → summary_3.md
  ep61~ep80 → LLM → summary_4.md
  ep81~ep100 → LLM → summary_5.md
  ep101~ep114 → LLM → summary_6.md

Layer 2:
  summary_1~6 → LLM → 总笔记.md
```

每层续跑支持：检测 `summary_N.md` 已存在则跳过。

### 配置参数

- LLM: openai (DeepSeek) / deepseek-chat / https://api.deepseek.com/v1
- Cookies: chrome
- 语言: zh
- 每集最大帧: 0（音频模式）
- 保留中间文件: 是（续跑需要）

### 输出目录

```
notes/BV1mJ411r7ZB/
├── ep01.md
├── ep02.md
├── ...
├── ep114.md
├── summary_1.md ~ summary_6.md   (中间层)
└── 总笔记.md                      (最终)
```

### 运行命令

```bash
export OPENAI_API_KEY="sk-..."
nohup uv run python scripts/batch_process.py > batch.log 2>&1 &
tail -f batch.log
```
