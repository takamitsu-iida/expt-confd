# 2-state: ConfD オペレーショナルデータ提供サンプル

このディレクトリは、YANG モジュール `example`（[yang/example.yang](yang/example.yang)）で定義した
**運用状態データ (operational state data / config false)** を、
Python データプロバイダーで動的に生成して ConfD に提供するサンプルです。

1-config が「設定データ (config true) を CDB からテキストファイルに同期」する例であったのに対し、
2-state は「状態データ (config false) を callpoint 経由でリアルタイムに返す」例になっています。

- ConfD のデータプロバイダーAPI (dp) を利用
- `server-status` コンテナ配下の leaf を Python で動的生成
- ConfD CLI から `show server-status` を実行すると、Python 側で計算した値が表示される

---

## 全体像

### コンポーネント関係図

```text
             +---------------------------+
             |    YANG モジュール       |
             |   example.yang            |
             |   (server-status,         |
             |    tailf:callpoint)       |
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
                           | callpoint "server_status_cp"
                           v
+------------+    データ要求    +-----------------------------+
|  ConfD     | --------------> | status_provider.py (DP)     |
|  CLI/CDB   | <-------------- |  - uptime 生成              |
|            |    データ応答    |  - last-checked-at 生成    |
+------------+                 +-----------------------------+
```

- YANG で `server-status` コンテナ (config false) と `tailf:callpoint server_status_cp` を定義
- `confdc` でコンパイルした FXS から [bin/example_ns.py](bin/example_ns.py) を生成
- [bin/status_provider.py](bin/status_provider.py) が
  - callpoint `server_status_cp` にデータプロバイダとして登録
  - ConfD からのデータ要求に応じて `uptime`, `last-checked-at` を返却

### 処理フロー図（`show server-status` を実行したとき）

```text
1. 管理者が ConfD CLI で状態確認

   ConfD CLI
   ----------------------------------------------
   show server-status

2. ConfD が YANG モデルを参照
   - container server-status は config false
   - tailf:callpoint server_status_cp が設定されている
   → 対応するデータプロバイダ (status_provider.py) に問い合わせ

3. status_provider.py 側のフロー

   (1) TransCallbacks.cb_init()
       - トランザクション開始（ソケットの準備）

   (2) DataCallbacks.cb_get_elem()
       - uptime を要求されたら、起動時刻との差分から
         "Up and running! (Uptime: 0h 3m)" のようなメッセージを生成
       - last-checked-at を要求されたら、現在時刻を HH:MM:SS 形式で生成

   (3) TransCallbacks.cb_finish()
       - トランザクション終了（後始末）

4. ConfD CLI に結果表示

   server-status {
     uptime          "Up and running! (Uptime: 0h 3m)";
     last-checked-at "14:30:45";
   }
```

---

## YANG モデルの解説

2-state の YANG モジュールは、1-config と同じ [yang/example.yang](yang/example.yang) を使用します。
ここでは、**server-status (config false)** 側にフォーカスして解説します。

### モジュール概要

- ファイル: [yang/example.yang](yang/example.yang)
- module 名: `example`
- namespace: `http://example.com/ns/config`
- 主な import
  - `tailf-common` : ConfD 拡張 (tailf:callpoint など)
  - `ietf-inet-types` : `inet:ip-address` などの汎用 IP 型

### YANG データツリー構造（サマリ図）

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

- `server-config` 以下は **CDB に保存される設定値**（2-state では主役ではない）
- `server-status` 以下は **読み取り専用のオペレーショナルデータ** であり、
  [bin/status_provider.py](bin/status_provider.py) が動的に生成して返す部分です。

### server-status コンテナ (config false + callpoint)

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

- `config false` により、「読み取り専用の状態データ」として扱われる
- `tailf:callpoint server_status_cp;` により、Python データプロバイダと紐付け
- ConfD は `server-status` の値を読むとき、CDB ではなく callpoint 先（status_provider.py）に問い合わせる

---

## Python データプロバイダ status_provider.py

### 役割

- ファイル: [bin/status_provider.py](bin/status_provider.py)
- callpoint 名: `server_status_cp`
- 役割
  - ConfD データプロバイダAPI (dp) を使って callpoint に登録
  - `uptime` および `last-checked-at` の値を動的に生成
  - デーモンプロセスとして動作し、ConfD からの要求を待ち受ける

### 構成要素

#### 1. ハッシュ定数

```python
UPTIME_HASH = str(ns.ns.ex_uptime)
LAST_CHECKED_HASH = str(ns.ns.ex_last_checked_at)
```

- [bin/example_ns.py](bin/example_ns.py) から、YANG ノードに対応するハッシュ値を取得
- `cb_get_elem()` 内で「どの leaf が要求されたか」を判定するのに使用

#### 2. DataCallbacks: 実データ生成

```python
class DataCallbacks:
    def cb_get_elem(self, tctx, kp) -> int:
        path = str(kp)
        if UPTIME_HASH in path:
            uptime_msg = self._get_uptime_message()
            val = _confd.Value(uptime_msg, _confd.C_STR)
            dp.data_reply_value(tctx, val)
        elif LAST_CHECKED_HASH in path:
            current_time = self._get_current_time()
            val = _confd.Value(current_time, _confd.C_STR)
            dp.data_reply_value(tctx, val)
        else:
            return 2  # NOT_FOUND
```

- ConfD からのデータ要求ごとに `cb_get_elem()` が呼ばれる
- キーパス `kp` に含まれるハッシュ値を見て、どのノードか判定
- 該当するヘルパー関数で値を生成し、`dp.data_reply_value()` で ConfD に返却

値の生成ロジックは、ヘルパーメソッドに分割されています。

```python
@staticmethod
def _get_uptime_message() -> str:
    elapsed = datetime.now() - START_TIME
    hours = int(elapsed.total_seconds() // 3600)
    minutes = int((elapsed.total_seconds() % 3600) // 60)
    return f"Up and running! (Uptime: {hours}h {minutes}m)"

@staticmethod
def _get_current_time() -> str:
    return datetime.now().strftime("%H:%M:%S")
```

- `START_TIME` はデーモン起動時刻
- そこからの経過時間を使って `uptime` メッセージを生成
- `last-checked-at` は「問い合わせを受けた時点の現在時刻」を返す

#### 3. TransCallbacks: トランザクション管理

```python
class TransCallbacks:
    def cb_init(self, tctx) -> int:
        dp.trans_set_fd(tctx, wrksock_global)
        return _confd.OK

    def cb_finish(self, tctx) -> int:
        return _confd.OK
```

- ConfD が状態データを読み取り始める前後で呼ばれる
- `cb_init` では、トランザクションコンテキストにワーカーソケットを関連付け
- `cb_finish` は終了時の後始末（このサンプルでは特別な処理はしていない）

#### 4. run(): メインループ

```python
def run() -> None:
    dctx = dp.init_daemon(DAEMON_NAME)
    ctlsock = socket.socket()
    wrksock_global = socket.socket()

    dp.connect(dctx, ctlsock,      dp.CONTROL_SOCKET, CONFD_HOST, CONFD_PORT, None)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET,  CONFD_HOST, CONFD_PORT, None)

    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, CALLPOINT_NAME, DataCallbacks())
    dp.register_done(dctx)

    while not stop_flag['stop']:
        readable, _, _ = select.select([ctlsock, wrksock_global], [], [], 1.0)
        for sock in readable:
            dp.fd_ready(dctx, sock)
```

- ConfD に接続し、コールバックを登録
- `select.select()` でソケットを監視し、要求が来たら `dp.fd_ready()` を呼び出す
- これにより、ConfD 側が適切なコールバック (`cb_init`, `cb_get_elem`, `cb_finish`) を順番に実行

#### 5. デーモン制御

```bash
python bin/status_provider.py --start      # デーモン起動
python bin/status_provider.py --stop       # デーモン停止
python bin/status_provider.py --status     # 状態確認
python bin/status_provider.py --foreground # フォアグラウンド実行
```

内部的には 1-config の config_monitor.py と同様に、二重 fork + PID ファイルでデーモン化しています。

---

## ビルドと起動方法

### 前提

- ConfD が `${HOME}/confd` などにインストールされている
- ConfD の Python モジュール `_confd` が `PYTHONPATH` から参照可能
- Python 3 が利用可能

必要に応じて `CONFD_DIR` を上書きしてください（デフォルト: `${HOME}/confd`）。

### 1. 初期化

```bash
cd 2-state
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

### 3. ConfD + ステータスプロバイダの起動

```bash
make start
```

- `make start` の中で以下を実行
  - ConfD 本体: `confd -c confd.conf ...` （`make start_confd`）
  - ステータスプロバイダ: `python bin/status_provider.py --start`

### 4. ConfD CLI から状態確認

J スタイル CLI の例:

```bash
make cli

# CLI 内で
show server-status
```

出力例（イメージ）:

```text
server-status {
  uptime          "Up and running! (Uptime: 0h 3m)";
  last-checked-at "14:30:45";
}
```

- CLI でコマンドを実行するたびに `uptime` と `last-checked-at` が更新される
- YANG 側では `config false` で定義されているため、CDB ではなくデータプロバイダから値が返っていることを確認できます

### 5. 停止

```bash
make stop
```

- ConfD 本体と status_provider デーモンの両方を停止します

status_provider だけを個別に制御したい場合は、直接スクリプトを呼び出します。

```bash
python bin/status_provider.py --start
python bin/status_provider.py --stop
python bin/status_provider.py --status
python bin/status_provider.py --foreground
```

---

## 拡張のヒント

### 1. 監視・表示する状態情報を増やす

1. YANG モデルの `server-status` コンテナに leaf を追加
2. `confdc --emit-python` で [bin/example_ns.py](bin/example_ns.py) を再生成
3. [bin/status_provider.py](bin/status_provider.py) の
   - ハッシュ定数定義
   - `DataCallbacks.cb_get_elem()`
   に対応する if/elif ブロックとヘルパーメソッドを追加

例: CPU 使用率を表示する `cpu-usage` を追加したい場合

```yang
leaf cpu-usage {
  type decimal64 {
    fraction-digits 2;
    range "0.00..100.00";
  }
  units "percent";
  description "CPU使用率（パーセント）";
}
```

- `example_ns.py` から新しいハッシュ `ex_cpu_usage` を参照
- status_provider.py 側で `_get_cpu_usage()` を実装し、`cb_get_elem()` に判定ロジックを追加

### 2. server-config との連携

- `server-config`（設定データ）で有効/無効のフラグや閾値を持たせ、
  その値を見ながら `server-status` の内容を変化させる、といった連携も可能です。
- その場合は CDB 読み取りAPI（cdb）を併用し、
  - 設定値は CDB から取得
  - 状態値は本スクリプトで動的生成
 という構成になります。

このサンプルをベースに、より実際の装置に近い状態監視ロジックを追加していくことができます。
