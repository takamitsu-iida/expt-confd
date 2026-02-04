# 3-ping: ConfD アクション (ping) 実行サンプル

このディレクトリは、YANG モジュール `example`（[yang/example.yang](yang/example.yang)）で定義した
**アクション (tailf:actionpoint)** を、Python アクションハンドラーで実装し、
ConfD CLI から `ping` コマンドとして実行するサンプルです。

- ConfD のアクションフレームワーク (dp) を利用
- `ping destination <host>` という CLI コマンドを定義
- Python 側で OS の `ping` コマンドを実行し、その結果を YANG の出力パラメータとして返却

1-config: 設定データ (config true) と CDB ↔ テキストファイル同期
2-state: 状態データ (config false) をデータプロバイダで提供
3-ping: コマンド (アクション) を実行し、結果を出力

---

## 全体像

### コンポーネント関係図

```text
             +---------------------------+
             |    YANG モジュール       |
             |   example.yang            |
             |   (container ping         |
             |    tailf:actionpoint)     |
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
                           | actionpoint "ping_action"
                           v
+------------+    アクション呼び出し    +-----------------------------+
|  ConfD CLI |  ----------------------> | ping_action.py (Action DP) |
|  (ping ...) |  <---------------------- |  - OS ping 実行            |
+------------+       結果の応答         |  - 結果解析 & 応答        |
                                         +-----------------------------+
```

- YANG で `container ping` と `tailf:actionpoint ping_action` を定義
- `confdc` でコンパイルした FXS から [bin/example_ns.py](bin/example_ns.py) を生成
- [bin/ping_action.py](bin/ping_action.py) がアクションポイント `ping_action` に登録され、
  CLI からの `ping` 実行要求を受けて、OS の `ping` コマンドを呼び出します。

### 処理フロー図（CLI から ping を実行したとき）

```text
1. 管理者が ConfD CLI で ping 実行

   admin@confd> ping destination 8.8.8.8
   admin@confd> ping destination 8.8.8.8 count 5

2. ConfD が YANG モデルを参照
   - container ping
   - tailf:action destination
   - tailf:actionpoint ping_action
   → 対応するアクションハンドラー (ping_action.py) に処理を委譲

3. ping_action.py 側の流れ

   (1) cb_init()
       - uinfo にワーカーソケットを関連付け

   (2) cb_action()
       - 入力パラメータ destination, count を取得
       - 別スレッドで execute_ping() を起動
       - _confd.DELAYED_RESPONSE を返し、ConfD に「後で応答する」と宣言

   (3) 別スレッド execute_ping()
       - OS の ping コマンドを実行
       - 出力をすべて読み取り、成功/失敗を判定
       - result: ping 出力全文
       - success: True / False
       - dp.action_reply_values() で結果を ConfD に返却

4. ConfD CLI に結果表示

   result  : ping の出力テキスト
   success : 少なくとも1パケット成功なら true、すべて失敗なら false

5. 実行中に Ctrl-C を押すと
   - cb_abort() が呼ばれ、子プロセス (ping) に SIGTERM/SIGKILL を送信
   - ConfD 側はクライアント接続を切断し、CLI には「Aborted: by user」と表示
```

---

## YANG モデルの解説

### アクション定義: container ping

- ファイル: [yang/example.yang](yang/example.yang)
- 関連箇所（抜粋）:

```yang
container ping {
  tailf:info "Send echo messages";
  tailf:action destination {
    tailf:actionpoint ping_action;

    input {
      leaf destination {
        type string;
        mandatory true;
        tailf:cli-drop-node-name;
      }

      leaf count {
        type uint8 {
          range "1..10";
        }
        default "1";
      }
    }

    output {
      leaf result {
        type string;
      }

      leaf success {
        type boolean;
      }
    }
  }
}
```

- `container ping`
  - CLI では `ping` コマンドのルート階層に相当
- `tailf:action destination`
  - サブコマンド `destination` を定義（`ping destination ...`）
- `tailf:actionpoint ping_action`
  - Python 側のアクションハンドラーと紐付ける名前
- `input`
  - `destination`: 宛先（必須）
  - `count`: 送信パケット数 (1〜10、デフォルト1)
- `output`
  - `result`: ping の出力テキスト
  - `success`: ping が成功したかどうか (boolean)

### YANG データツリー構造（サマリ図）

```text
module: example

  +--rw server-config             (設定データ: config true)
  |   +--rw ip-address  inet:ip-address
  |
  +--ro server-status             (運用状態データ: config false)
  |   +--ro uptime           string
  |   +--ro last-checked-at  string
  |
  +--rw ping                      (アクション用コンテナ)
      +---x destination           (tailf:action)
          +---w input
          |    +---w destination  string
          |    +---w count        uint8 (1..10, default 1)
          +--ro output
               +--ro result       string
               +--ro success      boolean
```

- `server-config` / `server-status` は 1-config / 2-state と共通
- `ping` コンテナが 3-ping の主役で、CLI コマンドとしてアクションを実行するための定義です。

---

## Python アクションハンドラー ping_action.py

### 役割

- ファイル: [bin/ping_action.py](bin/ping_action.py)
- アクションポイント名: `ping_action`
- 役割
  - ConfD にアクションハンドラーとして登録
  - CLI からの `ping` 実行要求を受け取り、OS の `ping` コマンドを実行
  - 実行結果を YANG の出力パラメータ `result` / `success` にマッピングして返却
  - Ctrl-C による中断 (cb_abort) もサポート

### 主な構成要素

#### 1. ping コマンド構築

```python
def build_ping_command(destination: str, count: int) -> List[str]:
    system = platform.system()
    if system == "Windows":
        return ["ping", "-n", str(count), destination]
    return ["ping", "-c", str(count), destination]
```

- OS に応じて `ping` のオプションを切り替え
- Linux/macOS では `-c <count>`、Windows では `-n <count>` を使用

#### 2. アクション応答生成

```python
def build_result_values(result_message: str, success: bool) -> List[Any]:
    return [
        _confd.TagValue(
            _confd.XmlTag(ns.ns.hash, ns.ns.ex_result),
            _confd.Value(result_message, _confd.C_BUF),
        ),
        _confd.TagValue(
            _confd.XmlTag(ns.ns.hash, ns.ns.ex_success),
            _confd.Value(success, _confd.C_BOOL),
        ),
    ]
```

- YANG の leaf `result` / `success` に対応する TagValue を作成
- `dp.action_reply_values()` にそのまま渡して応答

#### 3. execute_ping(): バックグラウンドでの ping 実行

- `cb_action()` から別スレッドで呼び出される
- 処理の要点:
  - `subprocess.Popen()` で ping を起動
  - `communicate()` で出力をすべて取得し、行ごとに保存
  - `returncode` によって成功/失敗/シグナル中断を判定
  - `dp.action_reply_values()` で遅延応答を返す
  - 実行中プロセスは `active_pings` 辞書で管理し、`cb_abort()` から参照可能

#### 4. PingActionHandler: ConfD に登録されるコールバッククラス

- `cb_init()`
  - `dp.action_set_fd(uinfo, work_sock_global)` でユーザごとにワーカーソケットを関連付け
- `cb_action()`
  - 入力パラメータ `destination` / `count` を取得
  - 別スレッドで `execute_ping()` を起動
  - `_confd.DELAYED_RESPONSE` を返し、後から遅延応答することを宣言
- `cb_abort()`
  - Ctrl-C による中断時に呼ばれ、`active_pings` から該当プロセスを取得して終了させる
  - `dp.action_delayed_reply_error(uinfo, "Action aborted by user")` で中断応答を送信

#### 5. デーモン起動・停止

```bash
python bin/ping_action.py --start      # デーモン起動
python bin/ping_action.py --stop       # デーモン停止
python bin/ping_action.py --status     # 状態確認
python bin/ping_action.py --foreground # フォアグラウンド実行
```

- 二重 fork + PID ファイルでデーモン化
- `run_daemon()` 内で ConfD への接続・アクション登録・イベントループを実行

---

## ビルドと起動方法

### 前提

- ConfD が `${HOME}/confd` などにインストールされている
- ConfD の Python モジュール `_confd` が `PYTHONPATH` から参照可能
- Python 3 が利用可能

必要に応じて `CONFD_DIR` を上書きしてください（デフォルト: `${HOME}/confd`）。

### 1. 初期化

```bash
cd 3-ping
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

### 3. ConfD + アクションハンドラーの起動

```bash
make start
```

- `make start` の中で以下を実行
  - ConfD 本体: `confd -c confd.conf ...` （`make start_confd`）
  - アクションハンドラー: `python bin/ping_action.py --start`

### 4. ConfD CLI から ping 実行

J スタイル CLI の例:

```bash
make cli

# CLI 内で
ping destination 8.8.8.8
ping destination 8.8.8.8 count 5
ping destination google.com
```

- 実行後、YANG の output に対応した `result` / `success` が表示されます
- 実行中に Ctrl-C を押すと、ping プロセスが中断され、CLI は "Aborted: by user" を表示します
- 進捗を見たい場合は、別ターミナルでログを tail します:

```bash
tail -f log/ping_action.log
```

### 5. 停止

```bash
make stop
```

- ConfD 本体と ping_action デーモンの両方を停止します

ping_action だけを個別に制御したい場合は、直接スクリプトを呼び出します。

```bash
python bin/ping_action.py --start
python bin/ping_action.py --stop
python bin/ping_action.py --status
python bin/ping_action.py --foreground
```

---

## 拡張のヒント

### 1. 他のネットワークツールへの展開

- `traceroute`, `mtr`, `dig` などを、同様に YANG のアクションとして定義可能です。
- 手順のイメージ:
  1. YANG に `container traceroute { tailf:action ... }` を追加
  2. `confdc --emit-python` で example_ns.py を再生成
  3. ping_action.py をベースに新しいアクションハンドラー（例: traceroute_action.py）を実装
  4. Makefile にアクションハンドラーを追加

### 2. server-config / server-status と連携したテスト

- 1-config, 2-state, 3-ping の example.yang は共通なので、
  - `server-config/ip-address` に設定された宛先に対して ping する
  - `server-status` に ping の結果を反映する
  といった連携も可能です。

このサンプルをベースに、ConfD を使った「設定」「状態」「アクション」の3要素を組み合わせた
ネットワーク運用ツールを構築していくことができます。
