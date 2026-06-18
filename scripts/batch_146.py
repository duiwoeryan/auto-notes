"""抽象代数 146 集批量处理 + 分层合并总笔记（并行 + 详细日志）。"""

import json
import os
import re
import signal
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
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

BASE_URL = "https://www.bilibili.com/video/BV1qG4y1B74U"
TOTAL = int(os.getenv("BATCH_TOTAL", "146"))
GROUP_SIZE = int(os.getenv("BATCH_GROUP_SIZE", "20"))
MAX_WORKERS = int(os.getenv("BATCH_WORKERS", "1"))
OUTPUT_DIR = Path("notes") / "BV1qG4y1B74U"
WORKSPACE_DIR = Path("workspace") / "BV1qG4y1B74U"

LLM_PROVIDER = os.getenv("AUTO_NOTES_LLM_PROVIDER") or "openai"
LLM_MODEL = os.getenv("AUTO_NOTES_LLM_MODEL") or "deepseek-chat"
LLM_BASE_URL = os.getenv("AUTO_NOTES_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")

PID = os.getpid()
console = Console()

# 中断标志
_interrupted = False


def _log(msg: str, *args):
    """带时间戳和 PID 的日志输出。"""
    ts = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{ts}[/dim] [PID {PID}] {msg}", *args)


# ── 信号处理 ──────────────────────────────────


def _handle_signal(sig, frame):
    global _interrupted
    sig_name = signal.Signals(sig).name
    _log(f"[yellow]收到信号 {sig_name}，正在停止...（等待当前批次完成）[/yellow]")
    _interrupted = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── 工具函数 ──────────────────────────────────


def _extract_ep_num(path: Path) -> int:
    m = re.search(r"(\d+)", path.stem)
    return int(m.group(1)) if m else 0


# ── 获取分 P 列表 ──────────────────────────


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


# ── 处理单集（并行安全） ──────────────────


def _capture_pipeline(cfg: Config) -> tuple[Pipeline, StringIO]:
    """创建 Pipeline，捕获其 console 输出到字符串。"""
    buf = StringIO()
    p = Pipeline(cfg)
    p.console = Console(file=buf, force_terminal=False)
    return p, buf


def _extract_timing(output: str) -> str:
    """从 pipeline 输出中提取耗时行。"""
    for line in output.split("\n"):
        if "下载:" in line and ("总计:" in line or "ASR:" in line):
            return line.strip()
    return ""


def process_episode(index: int) -> tuple[int, bool, str]:
    """返回 (集号, 成功, 耗时简述)。"""
    tag = f"ep{index:02d}"
    ep_workspace = WORKSPACE_DIR / tag
    ep_output = OUTPUT_DIR / f"{tag}.md"

    if ep_output.exists():
        return index, True, "cached"

    cfg = Config()
    cfg.working_dir = ep_workspace
    cfg.output_dir = ep_workspace
    cfg.keep_intermediates = True

    t_start = time.time()
    try:
        pipeline, buf = _capture_pipeline(cfg)
        generated = pipeline.run(f"{BASE_URL}?p={index}")
        elapsed = time.time() - t_start
        captured = buf.getvalue()
        timing = _extract_timing(captured)

        if generated and generated.exists():
            generated.rename(ep_output)
            return index, True, timing or f"{elapsed:.0f}s"

        return index, False, f"未生成笔记文件 ({elapsed:.0f}s)"
    except Exception:
        elapsed = time.time() - t_start
        tb = traceback.format_exc().strip()
        return index, False, f"异常 ({elapsed:.0f}s): {tb[:200]}"


# ── 分层合并总笔记 ────────────────────────


def _merge_batch(batch: list[Path], start: int, end: int) -> Path:
    summary_file = WORKSPACE_DIR / f"summary_{start:02d}-{end:02d}.md"
    if summary_file.exists():
        return summary_file

    _log(f"  合并 [bold]{start}~{end}[/bold]（{len(batch)} 篇）...")
    chunks = [
        f"## 第{_extract_ep_num(f)}集\n\n{f.read_text(encoding='utf-8')}"
        for f in batch
    ]
    combined = "\n\n---\n\n".join(chunks)
    sys_prompt = (
        "你是一个数学笔记整理助手。"
        f"将以下高等代数课程第{start}~{end}集的笔记合并为结构清晰的中层摘要。"
        "保留核心公式、定理和逻辑脉络。使用 Markdown 格式。"
    )
    llm = get_llm(LLM_PROVIDER, base_url=LLM_BASE_URL)
    result = llm.generate(sys_prompt, f"请整理以下笔记：\n\n{combined}", LLM_MODEL)
    summary_file.write_text(result, encoding="utf-8")
    _log(f"    → {summary_file.name}")
    return summary_file


def hierarchical_merge(md_files: list[Path]):
    if not md_files:
        _log("没有可合并的笔记")
        return

    files = sorted(md_files, key=_extract_ep_num)
    _log("")
    _log("[bold]=== 第二阶段：分层合并 ===[/bold]")

    summaries: list[Path] = []
    for offset in range(0, len(files), GROUP_SIZE):
        batch = files[offset:offset + GROUP_SIZE]
        start = _extract_ep_num(batch[0])
        end = _extract_ep_num(batch[-1])
        if _interrupted:
            _log("[yellow]收到中断，跳过后续合并[/yellow]")
            return
        summaries.append(_merge_batch(batch, start, end))

    total_path = OUTPUT_DIR / "总笔记.md"
    if total_path.exists():
        _log("总笔记已存在，跳过")
        return

    if _interrupted:
        _log("[yellow]收到中断，跳过总笔记生成[/yellow]")
        return

    _log("生成总笔记...")
    chunks = [
        f"## {s.stem.replace('_', ' ')}\n\n{s.read_text(encoding='utf-8')}"
        for s in sorted(summaries)
    ]
    combined = "\n\n---\n\n".join(chunks)
    sys_prompt = (
        "你是一个数学笔记整理助手。"
        "将以下高等代数课程各阶段摘要合并为一篇完整的课程总笔记。"
        "按章节组织，去除重复，保留核心内容。使用 Markdown 格式。"
    )
    llm = get_llm(LLM_PROVIDER, base_url=LLM_BASE_URL)
    result = llm.generate(sys_prompt, f"请整理为总笔记：\n\n{combined[:100000]}", LLM_MODEL)
    total_path.write_text(result, encoding="utf-8")
    _log(f"[bold green]总笔记 → {total_path}[/bold green]")


# ── 主流程 ──────────────────────────────────


def main():
    global _interrupted
    t_program = time.time()

    _log("[bold]auto-notes 批量处理 启动[/bold]")
    _log(f"  视频: {BASE_URL}")
    _log(f"  总集数: {TOTAL}")
    _log(f"  并行: {MAX_WORKERS} workers")
    _log(f"  PID: {PID}")
    _log(f"  日志: batch_146.log")
    _log("")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 获取分 P 列表 ──
    urls = get_playlist_urls()
    total = len(urls)
    _log(f"获取到 [bold]{total}[/bold] 集")

    # ── 统计缓存 ──
    cached = sum(1 for i in range(1, total + 1) if (OUTPUT_DIR / f"ep{i:02d}.md").exists())
    completed: list[Path] = []
    for i in range(1, total + 1):
        p = OUTPUT_DIR / f"ep{i:02d}.md"
        if p.exists():
            completed.append(p)

    remaining = [i for i in range(1, total + 1) if i not in {_extract_ep_num(p) for p in completed}]
    _log(f"缓存: {cached} 集，剩余: {len(remaining)} 集")
    _log("")

    # ── 进度条 ──
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

    ok_count = cached
    fail_count = 0

    with progress_bar:
        task = progress_bar.add_task("", total=total)

        for p in completed:
            progress_bar.update(task, advance=1,
                description=f"{p.stem} ✅ cached")

        # ── 并行处理 ──
        if remaining:
            _log(f"[bold]开始并行处理 {len(remaining)} 集[/bold]")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {pool.submit(process_episode, i): i for i in remaining}
                try:
                    for future in as_completed(futures):
                        if _interrupted:
                            pool.shutdown(wait=False, cancel_futures=True)
                            break
                        i, ok, detail = future.result()
                        ep_tag = f"ep{i:02d}"
                        if ok:
                            ok_count += 1
                            completed.append(OUTPUT_DIR / f"ep{i:02d}.md")
                            _log(f"{ep_tag} ✅ {detail}")
                            progress_bar.update(task, advance=1,
                                description=f"{ep_tag} ✅")
                        else:
                            fail_count += 1
                            _log(f"{ep_tag} ❌ {detail}")
                            progress_bar.update(task, advance=1,
                                description=f"{ep_tag} ❌")
                except KeyboardInterrupt:
                    _interrupted = True
                    _log("[yellow]键盘中断, 等待当前任务完成...[/yellow]")
                    pool.shutdown(wait=False, cancel_futures=True)

    # ── 汇总 ──
    elapsed = time.time() - t_program
    _log("")
    _log("[bold]══════════════════════════[/bold]")
    _log(f"[bold]处理完成[/bold]")
    _log(f"  总计: {ok_count}/{total} 成功, {fail_count} 失败")
    _log(f"  耗时: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    if _interrupted:
        _log("[yellow]  状态: 被用户中断[/yellow]")

    if completed and not _interrupted:
        hierarchical_merge(completed)
    elif completed and _interrupted:
        _log("[yellow]因中断跳过合并，重新运行时自动继续[/yellow]")

    _log("[bold]batch_146.py 退出[/bold]")


if __name__ == "__main__":
    main()
