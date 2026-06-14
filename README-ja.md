# BOINC Exporter

[![Test](https://github.com/surface0/boinc-exporter/actions/workflows/test.yml/badge.svg)](https://github.com/surface0/boinc-exporter/actions/workflows/test.yml)

BOINC クライアントのタスク状況・功績・プロジェクト情報を取得し、Prometheus / VictoriaMetrics に公開する Exporter です。

## 機能

- BOINC GUI RPC (TCP/31416) 経由でメトリクスを収集
- Prometheus 互換の `/metrics` エンドポイントを公開
- Grafana ダッシュボード付属
- Docker / docker-compose 対応
- マルチホスト対応（複数の BOINC クライアントを個別にスクレイプ可能）

## 公開メトリクス

| メトリクス | 種別 | 説明 |
|---|---|---|
| `boinc_up` | Gauge | BOINC クライアントへの接続状態（1=接続中、0=切断） |
| `boinc_tasks_total{state}` | Gauge | 状態別タスク数 |
| `boinc_task_fraction_done{name,project_url}` | Gauge | 実行中タスクの進捗率（0〜1） |
| `boinc_project_total_credit{project,url}` | Gauge | プロジェクトの累積クレジット |
| `boinc_project_avg_credit{project,url}` | Gauge | 直近の1日平均クレジット |
| `boinc_host_total_credit{project,url}` | Gauge | このホストが貢献した累積クレジット |
| `boinc_host_avg_credit{project,url}` | Gauge | このホストが貢献した直近の1日平均クレジット |
| `boinc_project_jobs_success_total{project,url}` | Gauge | 成功ジョブ数 |
| `boinc_project_jobs_error_total{project,url}` | Gauge | 失敗ジョブ数 |

## クイックスタート（docker-compose）

Exporter・VictoriaMetrics・Grafana をまとめて起動します。

```bash
git clone https://github.com/surface0/boinc-exporter.git
cd boinc-exporter

# BOINC GUI RPC パスワードを設定（gui_rpc_auth.cfg の内容）
export BOINC_PASSWORD=your_password

docker compose up -d
```

| サービス | URL |
|---|---|
| Grafana | http://localhost:3000 |
| VictoriaMetrics | http://localhost:8428 |
| Exporter `/metrics` | http://localhost:9101/metrics |

> **Linux ホストの場合**: BOINC クライアントがホスト上で動作している場合、`extra_hosts` の設定により `host.docker.internal` でホストに接続されます。

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `BOINC_HOST` | `host.docker.internal` | BOINC クライアントのホスト名または IP |
| `BOINC_PORT` | `31416` | BOINC GUI RPC のポート番号 |
| `BOINC_PASSWORD` | （空） | GUI RPC パスワード（空の場合は認証なし） |
| `EXPORTER_PORT` | `9101` | Exporter の待受ポート |

## BOINC クライアントの設定

BOINC クライアントがリモート接続を受け付けるように設定します。

`cc_config.xml` に以下を追加してください：

```xml
<cc_config>
  <options>
    <allow_remote_gui_rpc>1</allow_remote_gui_rpc>
  </options>
</cc_config>
```

GUI RPC パスワードは `gui_rpc_auth.cfg` に記載されています（通常は `/var/lib/boinc/gui_rpc_auth.cfg`）。

## 手動インストール

```bash
pip install -r requirements.txt
pip install -e .

export BOINC_HOST=localhost
export BOINC_PASSWORD=your_password

boinc-exporter
# または
python -m boinc_exporter
```

## Grafana ダッシュボード

`grafana/dashboards/boinc.json` を Grafana にインポートするか、docker-compose 起動時に自動でプロビジョニングされます。

### パネル構成

| パネル | 内容 |
|---|---|
| BOINC Status | 接続状態（ホスト別） |
| Total Credits | 全プロジェクト合計クレジット |
| Avg Daily Credits | 全プロジェクト合計の1日平均クレジット |
| Executing Tasks | 実行中タスク数（ホスト別） |
| Tasks by State | 状態別タスク数（全ホスト統合） |
| Active Task Progress | 実行中タスクの進捗一覧（全ホスト・全タスク） |
| Total Credits by Project | プロジェクト別累積クレジットの推移 |
| Avg Daily Credits by Project | プロジェクト別1日平均クレジットの推移 |
| Jobs Success by Project | プロジェクト別成功ジョブ数 |
| Jobs Error by Project | プロジェクト別失敗ジョブ数 |

## DockerHub

```bash
docker pull seizu/boinc-exporter
```

バージョンタグ付きリリース：

```bash
git tag v1.0.0
git push --tags
# → GitHub Actions が自動でビルドし DockerHub に push します
```

## 開発

```bash
# 依存関係のインストール
pip install -r requirements-dev.txt
pip install -e .

# テスト実行
python -m pytest -v

# カバレッジ付きテスト
python -m pytest --cov=boinc_exporter --cov-report=term-missing
```

## ライセンス

MIT
