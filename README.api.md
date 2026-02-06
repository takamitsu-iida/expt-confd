# ConfD Python API メモ

このリポジトリで使っている ConfD の Python API について、よく出てくるパターンと考え方を整理します。

---

## 1. Python バインディングの全体像

ConfD の Python からの利用は、C ライブラリ libconfd の薄いラッパーになっています。

- 核となるモジュール
  - `_confd` : 共通の定数・型 (`CONFD_OK`, `CONFD_ERR`, `Value`, `TagValue`, `XmlTag` など)
  - `_confd.dp` : Data Provider / Action / デーモン系 API
  - `_confd.cdb` : CDB Subscription / CDB リード用 API
  - `_confd.maapi` : 管理用 API (MAAPI)
  - `_confd.error` : ConfD から返ってくるエラーの例外クラス
- YANG モジュールから自動生成される Python
  - `confdc --emit-python` で生成される `example_ns.py` など
  - `ns.hash` や `ns.<leaf 名>` などのハッシュ値を持っていて、Python API では "パス文字列" の代わりにこれを使うことが多い

このリポジトリだと、以下のように利用されています。

- Data Provider / Action (シンプルな例)
  - [2-state/bin/status_provider.py](2-state/bin/status_provider.py)
  - [7-action/bin/action_daemon.py](7-action/bin/action_daemon.py)
- CDB Subscription
  - [1-config/bin/config_monitor.py](1-config/bin/config_monitor.py)
- MAAPI
  - [8-maapi/bin/maapi_demo.py](8-maapi/bin/maapi_demo.py)

---

## 2. Data Provider API (dp) の基本パターン

代表例: [2-state/bin/status_provider.py](2-state/bin/status_provider.py)

### 2.1 基本構成

1. デーモンコンテキストを初期化
   - `dctx = dp.init_daemon("daemon_name")`
2. 2個のソケットを ConfD に接続
   - 制御用 `CONTROL_SOCKET`
   - 実データ用 `WORKER_SOCKET`
   - `dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, host, port, None)`
3. コールバックを登録
   - トランザクション管理: `dp.register_trans_cb(dctx, TransCallbacks())`
   - データ取得: `dp.register_data_cb(dctx, CALLPOINT_NAME, DataCallbacks())`
   - 登録完了: `dp.register_done(dctx)`
4. `select.select()` でソケットを監視し、読み取り可能なら `dp.fd_ready(dctx, sock)` を呼ぶ
   - ConfD が内部で適切なコールバック (`cb_init`, `cb_get_elem` など) を呼び出す

### 2.2 トランザクションコールバック

`TransCallbacks` クラス (status_provider.py より):

- 役割
  - 1 回の "show" や API リクエストの間のライフサイクル管理
  - BEGIN TRANSACTION / COMMIT のようなイメージ
- 代表的メソッド
  - `cb_init(self, tctx)`
    - 最初に 1 回呼ばれる
    - `dp.trans_set_fd(tctx, wrksock_global)` で、どのソケット経由で後続のデータ要求を受けるかを紐付ける
  - `cb_finish(self, tctx)`
    - 最後に 1 回呼ばれる
    - 多くの場合、後処理が無ければ `return _confd.OK` だけで十分

### 2.3 データコールバック

`DataCallbacks` クラス (status_provider.py より):

- 役割
  - 実際の値を返す "本体" 部分
- 代表的メソッド
  - `cb_get_elem(self, tctx, kp)`
    - `kp` (keypath) でどのノードの値かを判定
    - 例: status_provider.py では、パス文字列中に `UPTIME_HASH` / `LAST_CHECKED_HASH` が含まれるかで分岐
    - 値は `_confd.Value(value, _confd.C_STR)` などでラップして `dp.data_reply_value(tctx, val)` で返す

```python
# イメージ
if UPTIME_HASH in path:
    msg = self._get_uptime_message()
    val = _confd.Value(msg, _confd.C_STR)
    dp.data_reply_value(tctx, val)
    return _confd.OK
```

- 拡張の仕方
  1. YANG に leaf を追加
  2. `confdc --emit-python` で `example_ns.py` を再生成
  3. `cb_get_elem()` に `elif` を追加し、新しいハッシュ値を見て値を返す

---

## 3. Action コールバック (dp)

代表例: [7-action/bin/action_daemon.py](7-action/bin/action_daemon.py)

Action は Data Provider と同じ `_confd.dp` を使いますが、専用の登録 API / コールバックを持ちます。

### 3.1 登録の流れ

1. デーモンコンテキストとソケットの準備
   - Data Provider と同様に `dp.init_daemon()` / `dp.connect()` で CONTROL / WORKER を作る
2. Action コールバックオブジェクトを作成
   - 例: `acb = ActionCallbacks(worker_sock=worker_sock)`
3. callpoint 名とコールバックを登録
   - `dp.register_action_cbs(dctx, 'reboot-point', acb)`
4. `dp.register_done(dctx)` で登録完了
5. `select.select()` ループで `dp.fd_ready()` を呼び続ける

### 3.2 ActionCallbacks の中身

- `cb_init(self, uinfo)`
  - `dp.action_set_fd(uinfo, self.wsock)` でこのユーザアクションとワーカーソケットを紐付け
- `cb_action(self, uinfo, name, keypath, params)`
  - ユーザーが CLI などから action を実行したときに呼ばれる
  - `params` に CLI で指定された引数が入る (`_confd.TagValue` の配列)
  - 結果は `_confd.TagValue` の配列を作り、`dp.action_reply_values(uinfo, result)` で返す
- `cb_abort(self, uinfo)`
  - 長時間動く action を途中キャンセルするときに呼ばれる
  - `dp.action_delayed_reply_error()` などで応答

```python
# 結果を返すイメージ
result = [
    _confd.TagValue(
        _confd.XmlTag(ns.hash, ns.config_time),
        _confd.Value("ok", _confd.C_STR),
    )
]
dp.action_reply_values(uinfo, result)
```

---

## 4. CDB Subscription API (cdb)

代表例: [1-config/bin/config_monitor.py](1-config/bin/config_monitor.py)

ConfD の CDB で設定変更を監視し、変更があればアプリ側に通知するための API です。

### 4.1 サブスクライバの基本パターン

1. サブスクリプション用ソケットを作成し接続
   - `cdb.connect(sock, cdb.SUBSCRIPTION_SOCKET, host, _confd.CONFD_PORT, '/')`
2. 監視したい名前空間 / パスを subscribe
   - `cdb.subscribe(sock, prio, example_ns.ns.hash, '/server-config')`
3. `cdb.subscribe_done(sock)` で登録完了
4. メインループ
   - `cdb.read_subscription_socket(sock)` で変更通知を待つ
   - 変更を読み出す処理を自前で実装
   - 終わったら `cdb.sync_subscription_socket(sock, cdb.DONE_PRIORITY)` で ACK

config_monitor.py では、`Subscriber` クラスの `loop()` メソッドが

1. `wait()` → `cdb.read_subscription_socket()`
2. `read_confd()` → CDB から値を読み、ファイル出力
3. `ack()` → `cdb.sync_subscription_socket()`

という流れになっています。

### 4.2 CDB 読み取り (READ_SOCKET)

設定値を実際に読むときは別ソケットを使います。

1. `cdb.connect(rsock, cdb.READ_SOCKET, host, _confd.CONFD_PORT, '/')`
2. `cdb.start_session(rsock, cdb.RUNNING)`
3. 必要なら `cdb.set_namespace(rsock, example_ns.ns.hash)`
4. `cdb.get(rsock, "/server-config/ip-address")` のようにパスで読み取る
5. 終わったら `cdb.end_session(rsock)`

config_monitor.py では WATCHED_PATHS のリストを回して `cdb.get()` し、
`*.conf` ファイルに書き出すようになっています。

---

## 5. MAAPI (管理 API)

代表例: [8-maapi/bin/maapi_demo.py](8-maapi/bin/maapi_demo.py)

MAAPI は、ConfD のコンフィグデータベース (candidate/running など) を
アプリケーションから操作するための API 群です。

### 5.1 attach / detach

トランザクションコンテキストや CLI セッションと紐付けるときに使います。

- `maapi.attach(maapisock, ns.hash, tctx)`
  - validation/data コールバックから、そのトランザクションのビューでデータを読む
- `maapi.attach2(maapisock, ns.hash, uinfo.usid, uinfo.actx_thandle)`
  - Action から、CLI セッションとアクション・トランザクションに紐付ける
- 終わったら `maapi.detach()` / `maapi.detach2()` を必ず呼ぶ

### 5.2 カーソルとループ

YANG の list を走査するときにカーソル (`maapi.init_cursor`) を使います。

- `mc = maapi.init_cursor(sock, thandle, "/config/items")`
- `keys = maapi.get_next(mc)` でキー取得、`while keys:` でループ
- 必要に応じて `maapi.exists()`, `maapi.get_elem()` で leaf を読む
- 最後に `maapi.destroy_cursor(mc)`

maapi_example.py の `ValCbs` / `DataCbs` / `Act*` クラスが典型的な使い方になっています。

### 5.3 XPath / Query

より柔軟な検索をしたい場合は、XPath やクエリ API を使います。

- `maapi.xpath_eval(sock, th, "<xpath 表現>", callback, None, "")`
  - ヒットした各ノードに対して callback が呼ばれる
- `maapi.query_start()` / `maapi.query_result()` / `maapi.query_stop()`
  - SQL 的に結果セットを取得し、ループで読む

maapi_example.py の `ActShowItemsCbs` / `ActShowItemsSmallerCbs` が
CLI からの action をトリガにして XPath / Query を実行する例です。

---

## 6. 型と値表現 (_confd.Value / TagValue)

ConfD と Python 間では、C 側の型を `_confd.Value` でラップしてやり取りします。

- 代表的な型
  - `_confd.C_STR` : 文字列
  - `_confd.C_INT64` : 整数
  - その他、IP アドレスやブールなど、YANG に対応した型が多数
- データ Provider / Action の戻り値
  - 単一の leaf: `_confd.Value` を `dp.data_reply_value()` で返す
  - Action の複数出力: `_confd.TagValue` の配列を `dp.action_reply_values()` で返す

```python
val = _confd.Value("hello", _confd.C_STR)
dp.data_reply_value(tctx, val)
```

---

## 7. このリポジトリ内サンプルの読み方ガイド

ConfD Python API の理解を深めるには、以下の順にソースを追いかけるのがおすすめです。

1. CDB Subscription / 設定連携
  - [1-config/bin/config_monitor.py](1-config/bin/config_monitor.py)
  - CDB Subscription で ConfD のコンフィグをローカルファイルに同期する
2. Data Provider / ステータス取得
  - [2-state/bin/status_provider.py](2-state/bin/status_provider.py)
  - Data Provider の典型パターン (TransCallbacks + DataCallbacks)
3. Action
  - [7-action/bin/action_daemon.py](7-action/bin/action_daemon.py)
  - YANG の tailf:action を Python だけで最小構成で実装した例
4. MAAPI
  - [8-maapi/bin/maapi_demo.py](8-maapi/bin/maapi_demo.py)
  - スタンドアロンの Python スクリプトから MAAPI を叩く最小例

それぞれのファイルには十分にコメントを入れてあるので、
この README.api.md を横に置きつつ、"どの API をどの役割で使っているか" を
対応付けながら読むと理解が早いと思います。

---

## 8. 開発時の tips

- まず YANG と `example_ns.py` を眺めて、どのノードにどのハッシュ値が割り当てられているかを把握する
- Data Provider / Action / MAAPI / CDB はそれぞれ
  - ソケットの種類
  - attach/ detach のタイミング
  - コールバックの責務
  が違うので、「どのレイヤーの API を使っているのか」を意識する
- 実装を壊したくないときは
  - ConfD の examples ディレクトリにあるオリジナルサンプルと diff を取りながら読む
  - このリポジトリの "コメント部分" だけを参考にして、自分のサンプルを別フォルダに作る

もし特定の API (例: `maapi.query_*` だけ詳しく、など) をもっと掘り下げたい場合は、その部分をピンポイントで追記することもできます。