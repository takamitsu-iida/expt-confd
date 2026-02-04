# 1-config: ConfD CDB とテキストファイルの同期サンプル

このディレクトリは、YANG モジュール `example`（[yang/example.yang](yang/example.yang)）で定義した設定データと、ConfD の CDB を介してテキストファイルを自動同期する最小構成のサンプルです。

- ConfD の CDB（RUNNING データストア）での設定変更を監視
- 変更された設定値をテキストファイル [confd-cdb/config_monitor.conf](confd-cdb/config_monitor.conf) に書き出し
- YANG モデルで定義した「設定データ」と「運用状態データ」の違いを確認

---

## 全体像

### コンポーネント関係図

```text
         +---------------------------+
         |    YANG モジュール       |
         |   example.yang            |
         +-------------+-------------+
                  |
                  | confdc -c
                  v
         +---------------------------+
         |   FXS ファイル           |
         |   loadpath/example.fxs    |
         +-------------+-------------+
                  |
                  | confdc --emit-python
                  v
         +---------------------------+
         | Python NS モジュール     |
         |   bin/example_ns.py       |
         +-------------+-------------+
                  |
                  | CDB Subscription API
                  v
+------------+    変更通知     +-----------------------------+
| ConfD CDB  | --------------> | config_monitor.py (Subscriber)|
| (RUNNING)  |                 +---------------+-------------+
+------------+                                 |
                                | テキスト出力
                                v
                        +-----------------------------+
                        | confd-cdb/config_monitor.conf|
                        +-----------------------------+
```

### 処理フロー図（CLI で設定変更したとき）

```text
1. 管理者が CLI で設定変更

  ConfD CLI
  ----------------------------------------------
  config
    server-config
     ip-address 192.168.1.100
    commit

2. ConfD が CDB (RUNNING) に設定反映

  +---------------------+
  |   ConfD CDB         |
  |   /server-config    |
  |   ip-address=...    |
  +----------+----------+
          |
          | CDB Subscription 通知
          v

3. config_monitor.py が通知を受信
  - Subscriber.loop() が変更検知
  - CDB から /server-config/ip-address を再読み取り

4. 一時ファイルに書き出し → 本ファイルへリネーム

  config_monitor.conf.tmp
    ↓ (rename)
  confd-cdb/config_monitor.conf

5. 外部ツールやスクリプトは
  confd-cdb/config_monitor.conf を読むだけで
  ConfD の設定内容を参照可能
```

### 手順の要約

1. YANG モデル [yang/example.yang](yang/example.yang) を `confdc` でコンパイルして FXS を生成
2. FXS から Python ネームスペースモジュール [bin/example_ns.py](bin/example_ns.py) を生成
3. Python サブスクライバー [bin/config_monitor.py](bin/config_monitor.py) が CDB Subscription API で設定変更を監視
4. 監視対象パス `/server-config/...` の値をテキストファイル [confd-cdb/config_monitor.conf](confd-cdb/config_monitor.conf) に出力

<br>

補足: このサンプルでは、`example_ns.py` 自体の中身を直接使うコードは少なく、
主に「モジュールのネームスペース情報（例: `example_ns.ns.hash`）」を
ConfD API に渡すために利用しています。

---

## YANG モデルの解説

### モジュール概要

- ファイル: [yang/example.yang](yang/example.yang)
- module 名: `example`
- namespace: `http://example.com/ns/config`
- 主な import
  - `tailf-common` : ConfD 拡張 (tailf:callpoint など)
  - `ietf-inet-types` : `inet:ip-address` などの汎用 IP 型

このモジュールは、

- 設定データ: `server-config` コンテナ
- 運用状態データ: `server-status` コンテナ（config false）

を定義し、「config true/false の違い」と「Python データプロバイダとの連携」の両方を学習できる構成になっています。

### YANG データツリー構造（サマリ図）

`example.yang` で定義されるデータツリーは、概ね次のようになります。

```text
module: example

  +--rw server-config             (設定データ: config true)
  |   +--rw ip-address  inet:ip-address
  |           (例: 127.0.0.1, 192.168.1.100, ::1 など)
  |
  +--ro server-status             (運用状態データ: config false)
      +--ro uptime           string
      |       (稼働時間メッセージ: "Up and running! (Uptime: 2h 15m)" など)
      +--ro last-checked-at  string
              (このステータスが最後に確認された時刻: "14:30:45" など)
```

- `server-config` 以下は **CDB に保存される設定値** であり、netconf / restconf / CLI から編集可能です。
- `server-status` 以下は **読み取り専用のオペレーショナルデータ** であり、CDB には保存されず、
  データプロバイダ（Python など）が動的に生成して返す想定になっています。

### 設定データ: container server-config

```yang
container server-config {
  leaf ip-address {
    type inet:ip-address;
    default "127.0.0.1";
  }
}
```

- パス: `/server-config/ip-address`
- 型: `inet:ip-address`（IPv4/IPv6 両対応）
- デフォルト値: `127.0.0.1`
- 特徴
  - `config` データ（明示的に `config false` を指定していないためデフォルトは `true`）
  - CDB に永続保存され、再起動後も値が残る
  - NETCONF / RESTCONF / ConfD CLI から変更可能

この leaf が、本サンプルで **CDB とテキストファイルを同期する対象** になっています。

### 運用状態データ: container server-status (config false)

```yang
container server-status {
  config false;

  tailf:callpoint server_status_cp;

  leaf uptime {
    type string;
  }

  leaf last-checked-at {
    type string;
  }
}
```

- パス: `/server-status/...`
- `config false` により「読み取り専用のオペレーショナルデータ」を表現
- CDB には保存されず、Python などのデータプロバイダから動的に提供される想定
- `tailf:callpoint server_status_cp;` で ConfD とデータプロバイダ（アプリケーション）を紐付け

このディレクトリのサンプルでは、主役は `server-config` 側ですが、同一モジュール内で

- 設定データ（config true）
- 状態データ（config false + tailf:callpoint）

の両方がどのように定義されるかを確認できます。

---

## Python サブスクライバーによる CDB → テキストファイル同期

### 監視スクリプト: bin/config_monitor.py

- ファイル: [bin/config_monitor.py](bin/config_monitor.py)
- 役割
  - ConfD CDB Subscription API を利用して設定変更を監視
  - 監視対象パスの値を [confd-cdb/config_monitor.conf](confd-cdb/config_monitor.conf) に書き出し
  - デーモン起動 / 停止 / ステータス確認を CLI オプションで制御

#### 監視対象パス

```python
WATCHED_PATHS = [
    "/server-config/ip-address",
]
```

- `WATCHED_PATHS` に定義した XPath をすべて監視
- ここにパスを追加するだけで、新しい設定項目をテキストファイル出力の対象にできます
  - 例: `"/server-config/port"` を追加してポート番号も同期、など

#### 出力ファイル

- パス: [confd-cdb/config_monitor.conf](confd-cdb/config_monitor.conf)
- 出力形式（例）:

```text
# Server Configuration
# Generated by config_monitor.py
# Do not edit manually - changes will be overwritten

ip-address = 192.168.1.100
```

- `WATCHED_PATHS` の各パスに対して
  - パス末尾のノード名: `config_name`（例: `ip-address`）
  - 取得した値: `value`
  - `config_name = value` という形式で 1 行ずつ出力

### 動作の流れ

1. `Subscriber` クラスが CDB サブスクリプションソケットに接続
2. `/server-config` をルートとする変更通知を購読
3. 起動直後に CDB から現在の設定値を読み取り、一時ファイル `config_monitor.conf.tmp` に書き出し
4. 一時ファイルを `config_monitor.conf` にリネーム（原子的に反映）
5. 以降、設定変更が発生するたびに
   - 通知受信 → CDB から該当パスの値を再読み取り
   - 一時ファイルに書き出し → 本ファイルにリネーム

これにより、ConfD の CDB とテキストファイルの内容が常に同期された状態になります。

---

## ビルドと起動方法

### 前提

- ConfD が以下のようなディレクトリにインストールされている
  - 例: `${HOME}/confd`
- ConfD の Python モジュール `_confd` が `PYTHONPATH` から参照できる状態
- Python 3 が利用可能

必要に応じて環境変数 `CONFD_DIR` を上書きしてください（デフォルト: `${HOME}/confd`）。

### 1. 初期化

```bash
cd 1-config
make init
```

- `../bin/init.sh` を呼び出し、ssh-keydir や基本設定ファイルを準備します

### 2. ビルド

```bash
make all
```

- 主な処理
  - [yang/example.yang](yang/example.yang) → [loadpath/example.fxs](loadpath/example.fxs) を生成
  - [loadpath/example.fxs](loadpath/example.fxs) から [bin/example_ns.py](bin/example_ns.py) を生成

### 3. ConfD + サブスクライバーの起動

```bash
make start
```

- `make start` の中で以下が実行されます
  - ConfD 本体: `confd -c confd.conf ...`
  - サブスクライバー: `python bin/config_monitor.py --start`

バックグラウンドデーモンとして config_monitor.py が動作し、CDB を監視してテキストファイルを更新します。

### 4. ConfD CLI から設定変更して動作確認

J スタイル CLI の例:

```bash
make cli

# CLI 内での操作例
config
  server-config
    ip-address 192.168.1.100
  commit
exit
```

設定を変更した後、テキストファイルを確認します。

```bash
cat confd-cdb/config_monitor.conf

# 出力例
# Server Configuration
# Generated by config_monitor.py
# Do not edit manually - changes will be overwritten

ip-address = 192.168.1.100
```

IP アドレスを別の値に変更すると、ファイルの内容も追従して更新されることが確認できます。

### 5. 停止

```bash
make stop
```

- ConfD 本体と Python サブスクライバーの両方を停止します。

サブスクライバーだけを個別に制御したい場合は、直接スクリプトを呼び出します。

```bash
python bin/config_monitor.py --start      # デーモン起動
python bin/config_monitor.py --stop       # デーモン停止
python bin/config_monitor.py --status     # 状態確認
python bin/config_monitor.py --foreground # フォアグラウンド実行（デバッグ用）
```

---

## 拡張のヒント

### 1. 同期対象となる設定項目を増やす

1. YANG モデルを拡張（例: `port` などを追加）
2. `confdc` を再実行（`make all`）して FXS / example_ns.py を更新
3. [bin/config_monitor.py](bin/config_monitor.py) の `WATCHED_PATHS` に新しいパスを追加

例: example.yang に以下を追加した場合

```yang
leaf port {
  type inet:port-number;
  default "8080";
}
```

`WATCHED_PATHS` を次のように変更

```python
WATCHED_PATHS = [
    "/server-config/ip-address",
    "/server-config/port",
]
```

これだけで、`port` の値も自動的に [confd-cdb/config_monitor.conf](confd-cdb/config_monitor.conf) に出力されるようになります。

### 2. 運用状態データ server-status の実装

- example.yang の `server-status` コンテナには `tailf:callpoint server_status_cp` が定義されています
- 別途 Python データプロバイダを実装することで、
  - `uptime` : サーバー稼働時間のメッセージ
  - `last-checked-at` : 最終アクセス時刻

などを動的に返すことができます。

このサンプルディレクトリでは具体的な実装は含めていませんが、

- 設定データ: `server-config` （CDB に保存、config_monitor.py が監視）
- 状態データ: `server-status` （将来的に callpoint で提供）

という役割分担を理解することで、ConfD を使った設定・状態管理の全体像をつかむことができます。
