"""準備手順が通ったかを確認するスクリプト。

使い方:
    uv run python scripts/check_env.py

確認すること:
    1. Python 3.9 以上
    2. psutil と duckdb が import できる
    3. 環境変数 MOTHERDUCK_TOKEN がある
    4. MotherDuck に接続できて、pc_metrics データベースを作れる（トークンは接続文字列で明示的に渡す）
    5. dbt コマンドが 2.x
"""
import os
import shutil
import subprocess
import sys


def ok(msg):
    print(f"[OK]   {msg}")


def ng(msg):
    print(f"[NG]   {msg}")
    sys.exit(1)


def main():
    if sys.version_info < (3, 9):
        ng(f"Python 3.9 以上が必要です（現在 {sys.version.split()[0]}）")
    ok(f"Python {sys.version.split()[0]}")

    try:
        import duckdb
        import psutil
    except ImportError as e:
        ng(f"ライブラリが足りません: {e}。uv sync を実行してください")
    ok(f"psutil {psutil.__version__} / duckdb {duckdb.__version__}")

    if not os.environ.get("MOTHERDUCK_TOKEN"):
        ng("環境変数 MOTHERDUCK_TOKEN がありません。README の手順 2 を確認してください")
    ok("MOTHERDUCK_TOKEN が設定されています")

    try:
        con = duckdb.connect(f"md:?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")
        con.sql("CREATE DATABASE IF NOT EXISTS pc_metrics")
        who = con.sql("SELECT current_user()").fetchone()[0]
    except Exception as e:
        ng(f"MotherDuck に接続できません: {e}")
    ok(f"MotherDuck に接続しました（user: {who}）。データベース pc_metrics があります")

    dbt = shutil.which("dbt")
    if not dbt:
        ng("dbt コマンドが見つかりません。仮想環境を有効にしているか確認してください")
    out = subprocess.run([dbt, "--version"], capture_output=True, text=True).stdout.strip()
    version = out.split()[-1] if out else ""
    if not version.startswith("2."):
        ng(f"dbt が 2.x ではありません: {out!r}")
    ok(f"dbt {version}")

    print("\n準備完了です。次は collect.py でデータを集めます。")


if __name__ == "__main__":
    main()
