# 8-maapi: シンプルな Python MAAPI 例

このディレクトリは、ConfD の MAAPI を Python から直接呼び出して
コンフィグデータを読み書きする「最小構成の例」です。

- YANG モジュール: `yang/example.yang`
- MAAPI デモスクリプト: `bin/maapi_demo.py`
- ConfD 設定: `confd.conf`
- ビルド/起動: `Makefile`

## 1. どんな動きをするか

YANG モジュール `yang/example.yang` では、次のようなデータモデルを定義しています。

- `container demo`
  - `leaf message` (string)
  - `leaf last-updated` (string)

Python スクリプト `bin/maapi_demo.py` は、MAAPI を使って running データストア上の
`/demo` 以下を直接操作します。

処理の流れは次の通りです。

1. MAAPI ソケットで ConfD に接続 (`maapi.connect`, `maapi.load_schemas`)
2. `start_user_session` / `start_trans` で running データストアに対する
   READ_WRITE トランザクションを開始
3. `/demo` が存在しなければ作成し、`message` / `last-updated` を初期化
4. 現在の `message` / `last-updated` を読み出して標準出力に表示
5. `last-updated` を現在時刻で更新
6. `apply_trans` / `finish_trans` でトランザクションを適用・終了

実行のたびに `last-updated` だけが新しい時刻に更新されていく、という動きになります。

## 2. 準備とビルド

ConfD がインストール済みであり、`confd`, `confdc` などが PATH にある前提です。

このリポジトリ直下で:

```bash
cd 8-maapi
make init   # 必要なディレクトリ、鍵、confd.conf などの初期化
make all    # YANGコンパイル (example.fxs) と example_ns.py の生成
```

`make all` では、`Makefile` のルールに従って次が実行されます。

- `yang/example.yang` → `loadpath/example.fxs` を生成 (`confdc -c`)
- `loadpath/example.fxs` → `bin/example_ns.py` を生成 (`confdc --emit-python`)
  - この例では MAAPI での操作にパス文字列 (`"/demo/..."`) を使っているため、
    `example_ns.py` の利用は必須ではありませんが、他の例と揃えるために生成しています。
- CLI 定義ファイル `cli/commands-*.cli` → `loadpath/commands-*.ccl` を生成

## 3. ConfD の起動と MAAPI スクリプトの実行

まず ConfD だけを起動します。

```bash
cd 8-maapi
make start   # ConfD を起動 (Python スクリプトはまだ動かさない)
```

別のシェルから、MAAPI デモスクリプトを実行します。

```bash
cd 8-maapi
python bin/maapi_demo.py
```

実行例のイメージ:

```text
[before]
  message      : Hello from MAAPI!
  last-updated : 2026-02-06T12:34:56
[after]
  message      : Hello from MAAPI!
  last-updated : 2026-02-06T12:35:10
```

※ 初回は `/demo` が存在しないため、`message` / `last-updated` が自動的に作成されます。

ConfD CLI からも値を確認できます。

```bash
make cli
```

CLI 例 (Jスタイル):

```text
confd# show running-config demo
```

## 4. Python コード側のポイント

`bin/maapi_demo.py` の中で重要なのは次の部分です。

- 接続とスキーマ読み込み
  - `maapi.connect(sock, ip=..., port=...)`
  - `maapi.load_schemas(sock)`
- ユーザセッションとトランザクション
  - `maapi.start_user_session(sock, user, context, groups, ip, _confd.PROTO_TCP)`
  - `maapi.start_trans(sock, _confd.RUNNING, _confd.READ_WRITE)` → トランザクションハンドル `th`
- データの存在確認と作成
  - `maapi.exists(sock, th, "/demo")`
  - 無ければ `maapi.create(sock, th, "/demo")`
- leaf の読み書き
  - 読み出し: `maapi.get_elem(sock, th, "/demo/message")`
  - 書き込み: `maapi.set_elem(sock, th, value, "/demo/last-updated")`
- コミットと終了
  - `maapi.apply_trans(sock, th, False)`
  - `maapi.finish_trans(sock, th)`

MAAPI の「基本 5 手順」(接続 → セッション → トランザクション → get/set → apply/finish) に
だけ集中できるよう、あえて最小限の処理に絞っています。

## 5. トラブルシュートのヒント

- `Could not import ConfD Python modules` と出る
  - ConfD の Python モジュール (`_confd`, `_confd.maapi`) が PYTHONPATH に入っているか確認
  - `~/confd/confdrc` を shell で `source` できているか確認
- `maapi.connect` で接続できない
  - ConfD が起動しているか (`make start` 済みか) を確認
  - `confd.conf` の `<ip>` / `<port>` 設定と `CONFD_HOST` / `CONFD_PORT` が合っているか
- 値が更新されない
  - `apply_trans` / `finish_trans` を呼び忘れていないか
  - `RUNNING` ではなく別のデータストアを使っていないかを確認
