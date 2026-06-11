"""PaddleOCR 画面文字识别引擎。"""

import json
from pathlib import Path
from typing import Optional

from rich.progress import Progress, TaskID


class OCREngine:
    """封装 PaddleOCR，对视频帧进行中文文字检测和识别，带文字去重。"""

    def __init__(self) -> None:
        self._ocr = None

    def _load_ocr(self):
        """首次使用时惰性加载 PaddleOCR（中文模型）。"""
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(lang="ch")

    def extract(
        self,
        frames: list[tuple[float, Path]],
        progress: Optional[Progress] = None,
    ) -> list[dict]:
        """
        对帧列表逐帧 OCR，返回识别结果：
            [{"timestamp": float, "texts": [str, ...]}, ...]
        同一文字在不同帧中仅出现一次（去重）。
        """
        self._load_ocr()

        results = []
        seen_texts: set[str] = set()

        task_id: Optional[TaskID] = None
        if progress:
            task_id = progress.add_task("OCR processing frames...", total=len(frames))

        for timestamp, frame_path in frames:
            ocr_result = self._ocr.ocr(str(frame_path))
            texts = []
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    text = line[1][0]
                    if text and text not in seen_texts:
                        texts.append(text)
                        seen_texts.add(text)

            if texts:
                results.append(
                    {
                        "timestamp": round(timestamp, 2),
                        "texts": texts,
                    }
                )

            if task_id is not None and progress:
                progress.update(task_id, advance=1)

        if task_id is not None and progress:
            progress.remove_task(task_id)

        return results

    def save_result(self, results: list[dict], path: Path) -> None:
        path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    def load_result(self, path: Path) -> list[dict]:
        return json.loads(path.read_text())
