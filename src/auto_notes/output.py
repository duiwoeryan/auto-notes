"""文本合并 + Markdown 笔记生成的提示词和输出逻辑。"""
from datetime import timedelta


def _format_ts(seconds: float) -> str:
    return str(timedelta(seconds=int(seconds)))


def _ts_link(seconds: float, label: str = "▶") -> str:
    """生成带时间戳的 Markdown 跳转链接 [▶](→t=MM:SS)。"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        ts = f"{h}:{m:02d}:{s:02d}"
    else:
        ts = f"{m}:{s:02d}"
    return f"[{label}](→t={ts})"


def build_merged_text(segments: list[dict], ocr_results: list[dict]) -> str:
    """
    将 ASR 转录和 OCR 文字按时间轴合并，输出 LLM 可消费的文本块。
    每条 ASR 片段附带时间戳，匹配时间范围内的 OCR 结果内联插入。
    """
    lines = []

    ocr_idx = 0
    for seg in segments:
        ts = seg["start"]
        line = f"[{_format_ts(ts)}] {seg['text']}"

        while ocr_idx < len(ocr_results) and ocr_results[ocr_idx]["timestamp"] <= seg["end"]:
            ocr = ocr_results[ocr_idx]
            for t in ocr["texts"]:
                line += f"\n  [slide {_format_ts(ocr['timestamp'])}] {t}"
            ocr_idx += 1

        lines.append(line)

    if ocr_idx < len(ocr_results):
        lines.append("\n--- 未匹配的时间戳 ---")
        for ocr in ocr_results[ocr_idx:]:
            for t in ocr["texts"]:
                lines.append(f"[{_format_ts(ocr['timestamp'])}] {t}")

    return "\n".join(lines)


SYSTEM_PROMPT = """你是一个专业的笔记整理助手。你的任务是将视频转录文本和画面文字整理成结构清晰的 Markdown 笔记。

要求：
1. 使用多级标题组织内容，反映视频的逻辑结构
2. 每个要点保留原文中的时间戳链接，格式为 [▶](→t=MM:SS) 或 [▶](→t=HH:MM:SS)
3. 提炼关键信息，去除口语化冗余，但保留重要细节
4. 如果原文有编号列表、步骤、分类等信息，用 Markdown 列表呈现
5. 整体使用中文，专业术语保留原文
6. 不要添加原文没有的信息"""


def build_output(
    merged_text: str,
    llm_provider: str,
    llm_model: str | None,
    video_title: str,
    llm_base_url: str | None = None,
) -> str:
    """
    将合并文本送 LLM 整理，返回带标题的 Markdown 笔记。
    """
    from .llm import get_llm

    llm = get_llm(llm_provider, base_url=llm_base_url)

    user_prompt = f"视频标题：{video_title}\n\n以下是视频内容：\n\n{merged_text}"
    notes = llm.generate(SYSTEM_PROMPT, user_prompt, llm_model)

    header = f"# {video_title}\n\n"
    return header + notes
