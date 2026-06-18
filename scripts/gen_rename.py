"""为高等代数/抽象代数笔记批量生成重命名映射。"""
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from auto_notes.llm import get_llm
import os

SERIES = [
    ("高等代数", "/tmp/titles_ad.txt", "notes/BV1mJ411r7ZB"),
    ("抽象代数", "/tmp/titles_aa.txt", "notes/BV1qG4y1B74U"),
]

for name, titles_file, notes_dir in SERIES:
    with open(titles_file) as f:
        titles = f.read().strip()

    llm = get_llm("openai", base_url=os.getenv("OPENAI_BASE_URL"))

    if name == "高等代数":
        categories = "行列式、矩阵、线性空间、线性映射、多项式、特征值、二次型、欧氏空间、线性变换、Jordan标准型"
    else:
        categories = "集合论、群论、环论、域论、模论、伽罗瓦理论"

    system_prompt = (
        "你是一个文件命名助手。下面是一系列" + name + "课程的各集标题。"
        "每行格式如 'p01 1.1二阶行列式'。\n\n"
        "要求：为每集生成一个文件名，格式为 '大类_具体内容.md'，例如：\n"
        "- p01 1.1二阶行列式 → 行列式_二阶行列式.md\n"
        "- p14 2.2 矩阵的运算 → 矩阵_矩阵的运算.md\n"
        "- p27 3.4向量的线性关系（上） → 线性空间_向量的线性关系.md\n\n"
        "大类参考：" + categories + "\n\n"
        "输出格式：每行一个 '旧标题 -> 新文件名'，不要其他内容。"
    )

    result = llm.generate(system_prompt, "为以下每集生成文件名：\n\n" + titles, "deepseek-v4-flash")
    out_path = f"/tmp/rename_{'ad' if name == '高等代数' else 'aa'}.txt"
    Path(out_path).write_text(result)
    print(f"{name}: {len(result)} chars -> {out_path}")
