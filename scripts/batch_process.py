import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from auto_notes.config import Config
from auto_notes.pipeline import Pipeline
from auto_notes.llm import get_llm

BASE_URL = "https://www.bilibili.com/video/BV1mJ411r7ZB"
COOKIES = "chrome"
LLM_PROVIDER = "openai"
LLM_MODEL = "deepseek-chat"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LANG = "zh"
TOTAL = 30
OUTPUT_DIR = Path("notes") / "BV1mJ411r7ZB"
WORKSPACE_DIR = Path("workspace") / "BV1mJ411r7ZB"


def get_playlist_urls(limit: int = TOTAL) -> list[str]:
    result = subprocess.run(
        [
            "yt-dlp",
            "--cookies-from-browser", COOKIES,
            "--flat-playlist",
            "--dump-json",
            "--no-playlist",
            f"{BASE_URL}?p=1",
        ],
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    playlist_count = info.get("playlist_count", 0)
    count = min(limit, playlist_count) if playlist_count else limit
    return [f"{BASE_URL}?p={i}" for i in range(1, count + 1)]


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\s-]", "", text).strip()[:80]


def process_episode(url: str, index: int) -> Path | None:
    safe_index = f"ep{index:02d}"
    label = f"[{safe_index}]"

    ep_workspace = WORKSPACE_DIR / safe_index
    ep_output = OUTPUT_DIR / f"{safe_index}.md"

    if ep_output.exists():
        print(f"{label} 已存在，跳过")
        return ep_output

    print(f"{label} 开始处理...", flush=True)

    cfg = Config()
    cfg.lang = LANG
    cfg.llm_provider = LLM_PROVIDER
    cfg.llm_model = LLM_MODEL
    cfg.llm_base_url = LLM_BASE_URL
    cfg.cookies_from_browser = COOKIES
    cfg.audio_only = True
    cfg.working_dir = ep_workspace
    cfg.output_dir = ep_workspace
    cfg.keep_intermediates = True

    try:
        pipeline = Pipeline(cfg)
        generated = pipeline.run(url)

        if generated and generated.exists():
            generated.rename(ep_output)
            print(f"{label} 完成 → {ep_output}", flush=True)
            return ep_output
        else:
            print(f"{label} 未生成笔记文件", flush=True)
            return None
    except Exception as e:
        print(f"{label} 失败: {e}", flush=True)
        return None


def combine_notes(md_files: list[Path]) -> Path | None:
    if not md_files:
        print("没有可合并的笔记")
        return None

    chunks = []
    for f in sorted(md_files):
        m = re.match(r"ep(\d+)", f.stem)
        ep_num = m.group(1) if m else "??"
        text = f.read_text(encoding="utf-8")
        content = f"## 第{ep_num}集\n\n{text}"
        chunks.append(content)

    combined = "\n\n---\n\n".join(chunks)
    temp_path = WORKSPACE_DIR / "_combined.txt"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(combined, encoding="utf-8")
    print(f"合并文本长度: {len(combined)} 字符")

    system_prompt = """你是一个专业的数学笔记整理助手。你的任务是将高等代数课程30节课的笔记按章节整理成一篇完整的总笔记。

要求：
1. 按课程章节组织内容（第1章行列式、第2章矩阵、第3章线性方程组等）
2. 每章内按知识点划分小节
3. 保留每节笔记中的核心公式和定理
4. 使用Markdown格式，公式用 $$ 渲染
5. 在每节开头标注来自第几集，格式为 `（来自第X集）`
6. 去除重复内容，保留最完整的解释"""

    user_prompt = f"以下是高等代数课程30集的笔记内容，请按章节整理成一篇完整的总笔记：\n\n{combined[:80000]}"

    llm = get_llm(LLM_PROVIDER, base_url=LLM_BASE_URL)
    print("生成总笔记中...", flush=True)
    result = llm.generate(
        system_prompt,
        user_prompt,
        LLM_MODEL,
    )

    total_path = OUTPUT_DIR / "总笔记.md"
    total_path.write_text(result, encoding="utf-8")
    print(f"总笔记 → {total_path}", flush=True)
    return total_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("获取分P列表...")
    urls = get_playlist_urls()
    print(f"共 {len(urls)} 集")

    completed: list[Path] = []
    for i, url in enumerate(urls, 1):
        result = process_episode(url, i)
        if result and result.exists():
            completed.append(result)

    ok = len(completed)
    total = len(urls)
    print(f"\n处理完成: {ok}/{total}")

    if completed:
        print("合并总笔记...")
        combine_notes(completed)
    else:
        print("没有成功处理的笔记，跳过合并")


if __name__ == "__main__":
    main()
