---
name: pc-metrics-modeling
description: Use when adding or changing a model, test, seed or dashboard query in the pc_metrics dbt project, so that it follows this project's layer rules, naming, keys, time zones and MotherDuck setup.
---
# pc_metrics のモデリングの決まり

PC のプロセスとメモリを集めて MotherDuck に入れ、dbt v2 で整えるプロジェクトの決まり。

## 層ごとの責務
- `models/staging/`（`stg_`）: source と 1 対 1。名前の変更、型と単位の変換、`qualify row_number()` による重複排除まで。JOIN はしない
- `models/intermediate/`（`int_`）: 複数の marts で使い回す前処理だけを置く。1 か所でしか使わない処理はファクトの CTE に書く
- `models/marts/`: ファクト（`fct_`）とディメンション（`dim_`）。問いごとの集計表は作らず、ダッシュボードの SQL でファクトとディメンションを結合する

## 書き方
- CTE は dbt 公式の形にする。先頭に `ref` と `source` だけの import CTE、次に処理の CTE、最後は `select * from final`（または最後の CTE）
- 代理キーは `dbt_utils.generate_surrogate_key` で作る。時刻は `epoch_us(collected_at)` にしてからキーに入れる
- ファクトの粒度は `_marts.yml` の description の先頭に「〜で 1 行」と書き、代理キーに `unique` と `not_null` を付ける
- ファクトからディメンションへのキーには `relationships` テストを付ける
- generic test の引数は v2 の形で `arguments:` の下に書く
- `accepted_values` は `dbt show` で実際の値を確かめてから書く。欠損が想定内の列に `not_null` を付けない

## 時刻
- `collected_at` は UTC の TIMESTAMPTZ。freshness と差分処理はこれで判定する
- 表示と集計の時刻は `collected_at_jst`（`at time zone 'Asia/Tokyo'`）。分や日で切るときは JST で切る

## 名寄せ
- ホスト名はそのままキーにしない。`int_hosts_resolved` で `seeds/host_aliases.csv` の PC 名（`device_name`）に寄せてから使う

## 実行
- コマンドは作業フォルダで `uv run dbt ...`。トークンは環境変数 `MOTHERDUCK_TOKEN`（direnv の `.env`）
- `dbt debug` は接続文字列にトークンを展開して表示するので、出力を共有しない
- ファクトだけを `--select` で作り直さない。ディメンションと一緒に `dbt build` する
- `dbt deps` のあとは、Dive 公開用に `dbt_packages/dbt_charts_dive/macros/flight_program.sql` の `dbt-charts>=0.8.0` を `==0.8.0` に直す
- 変更したら `uv run dbt check` と `uv run dbt lint` も流す
