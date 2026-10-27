"""collect.py が書いた CSV を MotherDuck（またはローカル DuckDB）の raw テーブルにまとめて読み込む。

使い方:
    uv run python scripts/load.py                     # data/*.csv を md:pc_metrics へ
    uv run python scripts/load.py --db dbt/dev.duckdb --data data_dev   # ローカルファイルへ

読み込んだ CSV は data/loaded/ に移す（二重読み込みの防止）。
collect.py が書いている途中の .csv.part は読まないので、collect.py と同時に動かしてよい。
ただし load.py 同士を同時に動かすと同じファイルを二重に読むので、load.py は 1 つずつ動かす。
md: の場合、ローカルの CSV は MotherDuck のハイブリッド実行で読まれ、1 本の INSERT で送られる。
"""
import argparse
import os
import pathlib
import time

import duckdb

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.process_metrics (
    collected_at    TIMESTAMPTZ,   -- UTC（dbt の freshness が UTC 前提のため）
    hostname        VARCHAR,
    pid             INTEGER,
    name            VARCHAR,
    status          VARCHAR,
    username        VARCHAR,
    create_time     TIMESTAMPTZ,
    memory_rss      BIGINT,
    memory_percent  DOUBLE,
    cpu_percent     DOUBLE,
    num_threads     INTEGER
);
CREATE TABLE IF NOT EXISTS raw.system_metrics (
    collected_at    TIMESTAMPTZ,
    hostname        VARCHAR,
    mem_total       BIGINT,
    mem_available   BIGINT,
    mem_used        BIGINT,
    mem_percent     DOUBLE,
    swap_used       BIGINT,
    cpu_percent     DOUBLE,
    boot_time       TIMESTAMPTZ
);
"""

# CSV の列の型。自動判定に任せると空列や数値だけの列で型がぶれるので明示する
COLUMNS = {
    "process_metrics": {
        "collected_at": "TIMESTAMPTZ", "hostname": "VARCHAR", "pid": "INTEGER", "name": "VARCHAR",
        "status": "VARCHAR", "username": "VARCHAR", "create_time": "TIMESTAMPTZ",
        "memory_rss": "BIGINT", "memory_percent": "DOUBLE", "cpu_percent": "DOUBLE",
        "num_threads": "INTEGER",
    },
    "system_metrics": {
        "collected_at": "TIMESTAMPTZ", "hostname": "VARCHAR", "mem_total": "BIGINT",
        "mem_available": "BIGINT", "mem_used": "BIGINT", "mem_percent": "DOUBLE",
        "swap_used": "BIGINT", "cpu_percent": "DOUBLE", "boot_time": "TIMESTAMPTZ",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="md:pc_metrics", help="読み込み先（ローカルなら dev.duckdb）")
    ap.add_argument("--data", default="data", help="CSV のあるディレクトリ")
    args = ap.parse_args()

    data = pathlib.Path(args.data)
    loaded_dir = data / "loaded"
    loaded_dir.mkdir(parents=True, exist_ok=True)

    db = args.db
    if db.startswith("md:"):
        db = f"{db}?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}"
    t0 = time.time()
    con = duckdb.connect(db)
    con.execute(DDL)
    print(f"[ready] {args.db} connected in {time.time() - t0:.1f}s", flush=True)

    for table, columns in COLUMNS.items():
        files = sorted(data.glob(f"{table}_*.csv"))
        if not files:
            print(f"[skip]  raw.{table}: CSV がありません", flush=True)
            continue
        t1 = time.time()
        paths = [str(f) for f in files]
        col_list = ", ".join(columns)
        rows = con.execute(
            f"INSERT INTO raw.{table} ({col_list}) "
            f"SELECT {col_list} FROM read_csv(?, header = true, columns = ?)",
            [paths, columns],
        ).fetchone()[0]
        for f in files:
            f.rename(loaded_dir / f.name)
        print(f"[load]  raw.{table}: {len(files)} files, {rows} rows in {time.time() - t1:.1f}s "
              f"-> moved to {loaded_dir}/", flush=True)

    print(f"[done] elapsed={time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
