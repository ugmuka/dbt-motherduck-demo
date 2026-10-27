"""psutil で自分の PC から何が取れるかを眺めるだけのスクリプト。何も書き込まない。

使い方:
    uv run python scripts/peek_psutil.py
"""
import datetime as dt
import platform

import psutil

GB = 1024 ** 3
MB = 1024 ** 2

print(f"== PC: {platform.system()} {platform.release()} / psutil {psutil.__version__}")
print(f"   起動時刻: {dt.datetime.fromtimestamp(psutil.boot_time()):%Y-%m-%d %H:%M}")

vm = psutil.virtual_memory()
print("\n== メモリ全体 (virtual_memory)")
print(f"   total={vm.total / GB:.1f}GB  used={vm.used / GB:.1f}GB  "
      f"available={vm.available / GB:.1f}GB  percent={vm.percent}%")

print("\n== CPU (cpu_percent, 1 秒計測)")
print(f"   全体={psutil.cpu_percent(interval=1)}%  コア別={psutil.cpu_percent(percpu=True)}")

print("\n== プロセス (process_iter) メモリ上位 10")
attrs = ["pid", "name", "status", "username", "memory_info", "num_threads"]
procs = [p.info for p in psutil.process_iter(attrs=attrs, ad_value=None)]
print(f"   プロセス数: {len(procs)}  "
      f"権限がなく読めないもの: {sum(1 for p in procs if p['memory_info'] is None)}")
print(f"   {'pid':>6}  {'memory':>9}  {'thr':>4}  {'status':<9} {'user':<12} name")
for p in sorted(procs, key=lambda p: p["memory_info"].rss if p["memory_info"] else 0, reverse=True)[:10]:
    rss = p["memory_info"].rss / MB if p["memory_info"] else 0
    print(f"   {p['pid']:>6}  {rss:7.0f}MB  {p['num_threads'] or 0:>4}  "
          f"{(p['status'] or '-'):<9} {(p['username'] or '-')[:12]:<12} {p['name']}")

print("\n== 同じ名前のプロセスが何個あるか 上位 5")
from collections import Counter
for name, n in Counter(p["name"] for p in procs).most_common(5):
    print(f"   {n:>3} x {name}")
