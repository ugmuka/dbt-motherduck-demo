"""PC のプロセスとメモリの使用状況を集めて、ローカルの CSV に書き出す。

使い方:
    uv run python scripts/collect.py                      # 5 秒おきに 180 秒間
    uv run python scripts/collect.py --interval 2 --seconds 60

出力:
    data/process_metrics_<UTC時刻>.csv
    data/system_metrics_<UTC時刻>.csv
    （MotherDuck への読み込みは load.py が行う）

書き込み中のファイルは .csv.part という名前で、--rotate 秒ごと（と終了時）に .csv に改名する。
load.py は .csv だけを読むので、collect.py と load.py は同時に動かしてよい。
"""
import argparse
import csv
import datetime as dt
import pathlib
import socket
import time

import psutil

UTC = dt.timezone.utc

PROCESS_COLUMNS = ["collected_at", "hostname", "pid", "name", "status", "username",
                   "create_time", "memory_rss", "memory_percent", "cpu_percent", "num_threads"]
SYSTEM_COLUMNS = ["collected_at", "hostname", "mem_total", "mem_available", "mem_used",
                  "mem_percent", "swap_used", "cpu_percent", "boot_time"]
PROC_ATTRS = ["pid", "name", "status", "username", "create_time",
              "memory_info", "memory_percent", "cpu_percent", "num_threads"]


def snapshot(hostname):
    now = dt.datetime.now(UTC)
    procs = []
    # ad_value=None: 権限がなく読めない項目は None にする（Mac のシステムプロセスなど）
    for p in psutil.process_iter(attrs=PROC_ATTRS, ad_value=None):
        i = p.info
        procs.append([
            now, hostname, i["pid"], i["name"], i["status"], i["username"],
            dt.datetime.fromtimestamp(i["create_time"], UTC) if i["create_time"] else None,
            i["memory_info"].rss if i["memory_info"] else None,
            i["memory_percent"], i["cpu_percent"], i["num_threads"],
        ])
    vm = psutil.virtual_memory()
    system = [
        now, hostname, vm.total, vm.available, vm.used, vm.percent,
        psutil.swap_memory().used, psutil.cpu_percent(),
        dt.datetime.fromtimestamp(psutil.boot_time(), UTC),
    ]
    return procs, system


class Rotator:
    """2 つの CSV（process / system）を .part 名で書き、rotate() で .csv に確定する"""

    def __init__(self, out):
        self.out = out
        self.files = None

    def open(self):
        stamp = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.paths = [self.out / f"process_metrics_{stamp}.csv", self.out / f"system_metrics_{stamp}.csv"]
        self.files = [open(p.with_suffix(".csv.part"), "w", newline="", encoding="utf-8") for p in self.paths]
        self.writers = [csv.writer(f) for f in self.files]
        self.writers[0].writerow(PROCESS_COLUMNS)
        self.writers[1].writerow(SYSTEM_COLUMNS)
        self.opened_at = time.time()

    def write(self, procs, system):
        self.writers[0].writerows(procs)
        self.writers[1].writerow(system)
        for f in self.files:
            f.flush()

    def rotate(self):
        """閉じてから改名する。改名は一瞬なので load.py が途中のファイルを拾うことはない"""
        for f, p in zip(self.files, self.paths):
            f.close()
            pathlib.Path(f.name).rename(p)
        size = self.paths[0].stat().st_size / 2**20
        print(f"[file] {self.paths[0].name} ({size:.1f}MB) を確定", flush=True)
        self.files = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=5, help="収集間隔（秒）")
    ap.add_argument("--seconds", type=int, default=180, help="収集を続ける時間（秒）")
    ap.add_argument("--rotate", type=int, default=60, help="この秒数ごとに CSV を確定して次のファイルに切り替える")
    ap.add_argument("--out", default="data", help="CSV の出力先ディレクトリ")
    args = ap.parse_args()

    hostname = socket.gethostname()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[start] host={hostname} interval={args.interval}s seconds={args.seconds}s "
          f"rotate={args.rotate}s (約 {max(1, args.seconds // args.interval)} 回) -> {out}/", flush=True)

    # cpu_percent は前回呼び出しからの差分なので、1 回空振りさせる
    psutil.cpu_percent()
    for p in psutil.process_iter(attrs=["cpu_percent"], ad_value=None):
        pass

    t0 = time.time()
    deadline = t0 + args.seconds
    total = ticks = 0
    rot = Rotator(out)
    rot.open()
    try:
        while time.time() < deadline:
            tick_start = time.time()
            procs, system = snapshot(hostname)
            rot.write(procs, system)
            total += len(procs)
            ticks += 1
            print(f"[{system[0].astimezone():%H:%M:%S}] tick={ticks} processes={len(procs)} "
                  f"mem_used={system[4] / 2**30:.1f}GB cpu={system[7]:.1f}%", flush=True)
            if time.time() - rot.opened_at >= args.rotate and time.time() + args.interval < deadline:
                rot.rotate()
                rot.open()
            time.sleep(max(0, args.interval - (time.time() - tick_start)))
    except KeyboardInterrupt:
        print("[stop] Ctrl+C", flush=True)
    finally:
        if rot.files:
            rot.rotate()

    print(f"[done] ticks={ticks} rows={total} elapsed={time.time() - t0:.0f}s -> {out}/", flush=True)


if __name__ == "__main__":
    main()
