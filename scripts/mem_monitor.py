"""监控 batch 运行时内存和 GPU 使用。"""
import os, sys, time, psutil, threading
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

LOG = Path("mem_monitor.log")
LOG.write_text("")

def monitor(interval=3):
    p = psutil.Process()
    while True:
        mem = p.memory_info().rss / 1024 / 1024
        children = p.children(recursive=True)
        child_mem = sum(c.memory_info().rss for c in children) / 1024 / 1024
        child_total = len(children)

        # System memory
        sys_mem = psutil.virtual_memory()
        line = (f"{time.strftime('%H:%M:%S')}  "
                f"主进程RSS:{mem:.0f}MB  "
                f"子进程RSS:{child_mem:.0f}MB({child_total}个)  "
                f"系统已用:{sys_mem.used/1024/1024/1024:.1f}GB/{sys_mem.total/1024/1024/1024:.1f}GB")
        print(line, flush=True)
        with LOG.open("a") as f:
            f.write(line + "\n")
        time.sleep(interval)

if __name__ == "__main__":
    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    import subprocess
    env = os.environ.copy()
    env["BATCH_WORKERS"] = "2"
    subprocess.run(["uv", "run", "python", "scripts/batch_114.py"], env=env)
