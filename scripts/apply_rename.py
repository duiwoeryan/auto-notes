"""根据生成的映射文件重命名笔记文件。"""
import re
from pathlib import Path

MAPPINGS = [
    ("/tmp/rename_ad.txt", "notes/BV1mJ411r7ZB"),
    ("/tmp/rename_aa.txt", "notes/BV1qG4y1B74U"),
]

for map_file, notes_dir in MAPPINGS:
    notes_path = Path(notes_dir)
    if not notes_path.exists():
        print(f"目录不存在: {notes_path}")
        continue

    lines = Path(map_file).read_text().strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue

        # 解析 "p01 1.1标题 -> 新文件名.md"
        old_part, new_name = line.split("->")
        old_part = old_part.strip()
        new_name = new_name.strip()

        # 从 "p01 1.1二阶行列式" 中提取 p01
        m = re.match(r"p(\d+)", old_part)
        if not m:
            continue
        ep_num = int(m.group(1))
        old_filename = f"ep{ep_num:02d}.md"
        old_path = notes_path / old_filename

        if not old_path.exists():
            print(f"  文件不存在: {old_path}")
            continue

        new_path = notes_path / new_name
        if old_path == new_path:
            continue
        if new_path.exists():
            print(f"  目标已存在: {new_path}")
            continue

        old_path.rename(new_path)
        print(f"  {old_filename} -> {new_name}")

    print(f"完成: {notes_path}")
