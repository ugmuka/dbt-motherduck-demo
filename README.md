# pc_metrics

自分の PC のプロセスとメモリを集めて MotherDuck に載せ、dbt v2 で整えて、dbt Charts のダッシュボードとして公開するプロジェクトです。
技術書典 21「MotherDuckとdbt v2で作る、自分だけのクラウドデータ基盤」の章のサンプルです。

```
collect.py ─▶ data/*.csv ─▶ load.py ─▶ MotherDuck（raw）─▶ dbt（staging → marts）─▶ dbt Charts（Dive）
```

## 必要なもの

- macOS 13 以降、または Windows 10 / 11
- [uv](https://docs.astral.sh/uv/)（Python も uv が入れます）
- [MotherDuck](https://motherduck.com/) のアカウントとアクセストークン（無料の Lite プランで動きます）
- dbt Charts（`uv tool install dbt-charts`）。ダッシュボードを使うときだけ

## 構成

```
.
├── scripts/
│   ├── check_env.py      # 準備ができたかを確かめる
│   ├── peek_psutil.py    # psutil で何が取れるかを眺める（書き込みなし）
│   ├── collect.py        # プロセスとメモリを数秒おきに CSV へ書く（E）
│   └── load.py           # CSV をまとめて raw テーブルに読み込む（L）
└── dbt/              # dbt プロジェクト（T）。プロジェクト名は pc_metrics
    ├── models/
    │   ├── staging/      # stg_: 名前と単位をそろえ、重複を除く（incremental）
    │   ├── intermediate/ # int_: ホスト名を PC 名に寄せる
    │   └── marts/        # fct_ / dim_: ファクトとディメンション
    ├── seeds/            # プロセスの分類、ホスト名の対応表
    ├── tests/            # singular test
    ├── checks/           # dbt check の決まり
    ├── charts/           # dbt Charts のボード
    └── skills/           # エージェント向けスキル（dbt deps で .claude/skills に入る）
```

## 使い方

コマンドはリポジトリのルート（`pyproject.toml` がある場所）で実行します。

### 1. 準備

```sh
uv sync
```

トークンを環境変数 `MOTHERDUCK_TOKEN` に入れます。

```sh
# Mac（direnv を使う場合）
echo 'MOTHERDUCK_TOKEN=ここに貼り付け' > .env
printf 'dotenv\nPATH_add .venv/bin\n' > .envrc
direnv allow
```

```powershell
# Windows（PowerShell）
setx MOTHERDUCK_TOKEN "ここに貼り付け"
$env:MOTHERDUCK_TOKEN = "ここに貼り付け"
```

```sh
uv run python scripts/check_env.py   # すべて [OK] になれば準備完了
```

`.env` は `.gitignore` に入っています。トークンをコミットしないでください。

### 2. データを集めて読み込む

```sh
uv run python scripts/collect.py --seconds 180   # 5 秒おきに 3 分間
uv run python scripts/load.py                    # MotherDuck の pc_metrics.raw に読み込む
```

### 3. dbt で変換する

```sh
cd dbt
uv run dbt deps
uv run dbt run --target prod --select "stg_*" --empty   # 初回だけ。空の staging を先に作る
uv run dbt build --target prod --full-refresh   # 初回だけ --full-refresh
uv run dbt build --target prod                  # 2 回目以降は差分だけ
```

ターゲットは 2 つあります。

| ターゲット | 接続先 | 使いどころ |
|---|---|---|
| `dev`（既定） | 手元の `dev.duckdb` | 試行錯誤。MotherDuck のコンピュートを使わない |
| `prod` | MotherDuck の `pc_metrics` | 本番。Dive の公開もこちらだけ |

dev 用のデータは別のフォルダに集めて読み込みます。

```sh
uv run python scripts/collect.py --seconds 60 --out data_dev
uv run python scripts/load.py --db dbt/dev.duckdb --data data_dev
cd dbt
uv run dbt run --select "stg_*" --empty   # 初回だけ。空の staging を先に作る
uv run dbt build --full-refresh
```

### 4. ダッシュボードを見る

```sh
cd dbt
dct serve --port 8080   # http://localhost:8080/pc_metrics/
```

`dbt build --target prod` を実行すると、最後に MotherDuck の Dive としても公開されます。ログに出た Dive の URL を `models/exposures.yml` の `url` に書いてください。

## 自分の環境に合わせるところ

- `seeds/process_category.csv`: プロセス名とカテゴリの対応表。ダッシュボードの「分類されていないプロセス」を見ながら育てます
- `seeds/host_aliases.csv`: ホスト名と PC 名の対応表。Mac はネットワークによってホスト名が変わるので、同じ PC の名前をここで 1 つに寄せます
- `models/exposures.yml`: Dive の URL と owner

## 注意

- MotherDuck の dbt-charts-dives パッケージは実験的なものです。2026 年 10 月時点では、`dbt deps` のあとに dbt Charts の版を 0.8.0 に固定する必要がありました（詳しくは本書の dbt Charts の節を参照）
- 空のデータベースに初めて `dbt build` すると、incremental の staging に付けた unit test が「Remote database error while fetching schema for incremental unit test」で失敗します。unit test はモデルのテーブルから列の型を読むためです。最初の 1 回だけ `dbt run --select "stg_*" --empty` で空のテーブルを作ってから `dbt build` してください
- staging を view から incremental に切り替えた直後の初回の `--full-refresh` で、`Catalog write-write conflict` のエラーが出ることがあります。もう一度実行するか、`--threads 1` を付けてください
