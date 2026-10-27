{% docs __overview__ %}
# pc_metrics

自分の PC のプロセスとメモリを 5 秒おきに集め、MotherDuck に載せて dbt v2 で整えたプロジェクトです。

- **raw**: `collect.py` が CSV に書き、`load.py` が MotherDuck に読み込んだ生データ
- **staging**（`stg_`）: 名前と単位をそろえ、二重読み込みの重複を除いたもの
- **marts**: ファクト（`fct_`）とディメンション（`dim_`）。ダッシュボードはこれを結合して作る

時刻は UTC で記録し、集計と表示は日本時間です。プロセスのメモリ（RSS）は共有メモリを重複して数えるので、合計は PC 全体の使用量を超えます。
{% enddocs %}
