"""在文件名中加入集号，保持可排序。"""
import re
from pathlib import Path

MAPPINGS = [
    ("/tmp/rename_ad.txt", "notes/BV1mJ411r7ZB"),
    ("/tmp/rename_aa.txt", "notes/BV1qG4y1B74U"),
]

for map_file, notes_dir in MAPPINGS:
    notes_path = Path(notes_dir)
    if not notes_path.exists():
        continue

    lines = Path(map_file).read_text().strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line or "->" not in line:
            continue

        old_part, new_name = line.split("->")
        old_part = old_part.strip()
        new_name = new_name.strip()

        m = re.match(r"p(\d+)", old_part)
        if not m:
            continue
        ep_num = int(m.group(1))

        current_path = notes_path / new_name
        if not current_path.exists():
            continue

        # 生成带集号的新名: 大类_pXX_内容.md
        new_name_with_num = re.sub(
            r"^(\w+)_",
            rf"\1_p{ep_num:02d}_",
            new_name
        )

        new_path = notes_path / new_name_with_num
        if current_path == new_path:
            continue
        if new_path.exists():
            print(f"  跳过(已存在): {new_name_with_num}")
            continue

        current_path.rename(new_path)
        print(f"  {new_name} -> {new_name_with_num}")

    print(f"完成: {notes_path}")
