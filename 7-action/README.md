# 7-action: シンプルな Python Action 例

このディレクトリは、ConfD の `tailf:action` を Python で実装する「最小構成の例」です。

- YANG モジュール: `yang/example.yang`
- Python デーモン: `bin/action_daemon.py`
- ConfD 設定: `confd.conf`
- ビルド/起動: `Makefile`

## 1. どんな動きをするか

YANG モジュールで、次のような action を定義しています。

- `container tools` の下に `tailf:action hello`
  - `tailf:actionpoint hello-python`
  - input:  `leaf name` (string, 必須)
  - output: `leaf greeting` (string)

Python 側 (`bin/action_daemon.py`) では、この actionpoint `hello-python` に対して
コールバックを登録し、以下の処理を行います。

1. ConfD から渡された `name` を受け取る
2. `"Hello, <name>! (from Python action)"` という文字列を作る
3. output leaf `greeting` として CLI に返す

CLI から見ると、単純に「名前を渡すと挨拶文が返ってくるアクション」です。

## 2. 準備とビルド

まず ConfD がインストールされており、`confd`, `confdc` などが PATH に通っている前提です。

このリポジトリ直下で:

```bash
cd 7-action
make init   # 必要なディレクトリ、鍵、confd.conf などの初期化
make all    # YANGコンパイル (example.fxs) と example_ns.py の生成
```

`make all` では、`Makefile` のルールに従って次が実行されます。

- `yang/example.yang` → `loadpath/example.fxs` を生成 (`confdc -c`)
- `loadpath/example.fxs` → `bin/example_ns.py` を生成 (`confdc --emit-python`)
- CLI 定義ファイル `cli/commands-*.cli` → `loadpath/commands-*.ccl` を生成

Python デーモン `bin/action_daemon.py` は、この `bin/example_ns.py` を `from example_ns import ns` で利用します。

## 3. 起動と CLI からの試し方

ConfD と Python アクションデーモンをまとめて起動するには:

```bash
cd 7-action
make start
```

内部的には:

- `make all` で YANG/FXS/Python モジュールをビルド
- `confd -c confd.conf ...` で ConfD を起動
- `python bin/action_daemon.py --start` ではなく、単に `python bin/action_daemon.py` を `Makefile` から起動
  (終了はシグナル SIGINT/SIGTERM で止める想定)

ConfD CLI(Jスタイル) を開きます。

```bash
make cli     # Jスタイル CLI
# または
make cli-c   # Cスタイル CLI
```

CLI での操作例 (Jスタイル):

```text
# コンフィグモードへ
confd# config

# action を実行
confd(config)# tools hello name Taro

# 完了すると、出力 leaf greeting が表示されるイメージ

Taro に対する挨拶文が表示されます。
```

## 4. Python コード側のポイント

`bin/action_daemon.py` の中で重要なのは次の部分です。

- デーモン初期化とソケット接続
  - `dctx = dp.init_daemon("simple_python_action_daemon")`
  - `dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, ...)`
  - `dp.connect(dctx, workersock, dp.WORKER_SOCKET, ...)`
- アクションコールバック登録
  - `dp.register_action_cbs(dctx, "hello-python", acb)`
  - `dp.register_done(dctx)`
- コールバッククラス `HelloActionCallbacks`
  - `cb_init`: `dp.action_set_fd(uinfo, self._worker_sock)` を呼んでソケットを関連付け
  - `cb_action`: 入力パラメータ `params[0].v` を読み、`TagValue` のリストを `dp.action_reply_values()` で返す

ConfD から見ると、「YANG の tailf:action に対して、Python でコールバックを 1 クラス書いた」だけ、というイメージになります。

## 5. トラブルシュートのヒント

- `example_ns` が import できない
  - `make all` で `bin/example_ns.py` が生成されているか確認
  - カレントディレクトリが `7-action` であることを確認
- action が CLI から見えない
  - `confd.conf` の `<loadPath>` に `./loadpath` が含まれているか
  - `loadpath/example.fxs` が存在するか
- action 実行時にエラーになる
  - `log/devel.log` や `log/confderr.log` を確認
  - `action_daemon.py` の標準出力/エラーも確認
