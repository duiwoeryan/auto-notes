"""高代 114 集批量处理 + 分层合并总笔记（带进度条）。"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from auto_notes.config import Config
from auto_notes.llm import get_llm
from auto_notes.pipeline import Pipeline

BASE_URL = "https://www.bilibili.com/video/BV1mJ411r7ZB"
TOTAL = int(os.getenv("BATCH_TOTAL", "114"))
GROUP_SIZE = int(os.getenv("BATCH_GROUP_SIZE", "20"))
OUTPUT_DIR = Path("notes") / "BV1mJ411r7ZB"
WORKSPACE_DIR = Path("workspace") / "BV1mJ411r7ZB"

LLM_PROVIDER = os.getenv("AUTO_NOTES_LLM_PROVIDER") or "openai"
LLM_MODEL = os.getenv("AUTO_NOTES_LLM_MODEL") or "deepseek-chat"
LLM_BASE_URL = os.getenv("AUTO_NOTES_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")

console = Console()


def get_playlist_urls(limit: int = TOTAL) -> list[str]:
    with console.status("获取分 P 列表..."):
        result = subprocess.run(
            ["yt-dlp", "--cookies-from-browser", "chrome",
             "--flat-playlist", "--dump-json", "--no-playlist",
             f"{BASE_URL}?p=1"],
            capture_output=True, text=True,
        )
        info = json.loads(result.stdout)
        playlist_count = info.get("playlist_count", 0)
        count = min(limit, playlist_count) if playlist_count else limit
    return [f"{BASE_URL}?p={i}" for i in range(1, count + 1)]


def process_episode(index: int) -> Path | None:
    tag = f"ep{index:02d}"
    ep_workspace = WORKSPACE_DIR / tag
    ep_output = OUTPUT_DIR / f"{tag}.md"

    if ep_output.exists():
        return ep_output

    cfg = Config()
    cfg.working_dir = ep_workspace
    cfg.output_dir = ep_workspace
    cfg.keep_intermediates = True

    try:
        pipeline = Pipeline(cfg)
        generated = pipeline.run(f"{BASE_URL}?p={index}")
        if generated and generated.exists():
            generated.rename(ep_output)
            return ep_output
        return None
    except Exception:
        return None


def hierarchical_merge(md_files: list[Path]):
    summaries: list[Path] = []
    sorted_files = sorted(md_files, key=lambda f: int(re.search(r"\d+", f.stem).group()))

    console.print("\n[bold]第二阶段：分层合并[/bold]")

    for batch_num in range(0, len(sorted_files), GROUP_SIZE):
        batch = sorted_files[batch_num: batch_num + GROUP_SIZE]
        start_ep = int(re.search(r"\d+", batch[0].stem).group())
        end_ep = int(re.search(r"\d+", batch[-1].stem).group())
        summary_file = WORKSPACE_DIR / f"summary_{start_ep:02d}-{end_ep:02d}.md"

        if summary_file.exists():
            summaries.append(summary_file)
            continue

        console.print(f"  合并 {start_ep}~{end_ep}（{len(batch)} 篇）...")
        chunks = []
        for f in batch:
            m = re.search(r"(\d+)", f.stem)
            ep_num = m.group(1) if m else "??"
            chunks.append(f"## 第{ep_num}集\n\n{f.read_text(encoding='utf-8')}")

        combined = "\n\n---\n\n".join(chunks)
        sys_prompt = (
            "你是一个数学笔记整理助手。"
            f"将以下高等代数课程第{start_ep}~{end_ep}集的笔记合并为结构清晰的中层摘要。"
            "保留核心公式、定理和逻辑脉络。使用 Markdown 格式。"
        )
        llm = get_llm(LLM_PROVIDER, base_url=LLM_BASE_URL)
        result = llm.generate(sys_prompt, f"请整理以下笔记：\n\n{combined}", LLM_MODEL)
        summary_file.write_text(result, encoding="utf-8")
        console.print(f"    → {summary_file.name}")
        summaries.append(summary_file)

    total_path = OUTPUT_DIR / "总笔记.md"
    if total_path.exists():
        console.print("总笔记已存在，跳过")
        return

    console.print("生成总笔记...")
    chunks = []
    for f in sorted(summaries):
        text = f.read_text(encoding="utf-8")
        chunks.append(f"## {f.stem.replace('_', ' ')}\n\n{text}")

    combined = "\n\n---\n\n".join(chunks)
    sys_prompt = (
        "你是一个数学笔记整理助手。"
        "将以下高等代数课程各阶段摘要合并为一篇完整的课程总笔记。"
        "按章节组织，去除重复，保留核心内容。使用 Markdown 格式。"
    )
    llm = get_llm(LLM_PROVIDER, base_url=LLM_BASE_URL)
    result = llm.generate(sys_prompt, f"请整理为总笔记：\n\n{combined[:100000]}", LLM_MODEL)
    total_path.write_text(result, encoding="utf-8")
    console.print(f"[bold green]总笔记 → {total_path}[/bold green]")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    urls = get_playlist_urls()
    total = len(urls)
    already_done = sum(1 for i in range(1, total + 1) if (OUTPUT_DIR / f"ep{i:02d}.md").exists())
    console.print(f"[bold]共 {total} 集[/bold]（已有 {already_done} 集缓存）")

    progress_bar = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    )

    completed: list[Path] = []
    with progress_bar:
        task = progress_bar.add_task("", total=total)

        # 标记已完成的
        for i in range(1, total + 1):
            p = OUTPUT_DIR / f"ep{i:02d}.md"
            if p.exists():
                completed.append(p)
                progress_bar.update(task, advance=1)
                progress_bar.update(task, description=f"ep{i:02d} ✅ cached")

        # 逐集处理
        for i in range(1, total + 1):
            if (OUTPUT_DIR / f"ep{i:02d}.md").exists():
                continue

            t0 = time.time()
            result = process_episode(i)
            elapsed = time.time() - t0

            if result:
                completed.append(result)
                progress_bar.update(task, advance=1,
                    description=f"ep{i:02d} ✅ {elapsed:.0f}s")
            else:
                progress_bar.update(task, advance=1,
                    description=f"ep{i:02d} ❌")

    ok = len(completed)
    console.print(f"\n[bold]处理完成: {ok}/{total}[/bold]")

    if completed:
        hierarchical_merge(completed)


if __name__ == "__main__":
    main()
