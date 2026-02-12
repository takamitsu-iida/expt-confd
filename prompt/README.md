# prompt ディレクトリの簡易 YANG CLI

このディレクトリには、ConfD 本体やその Python バインディングに依存せず、
**YANG モデル + Python だけで動作する簡易 CLI** 実装が入っています。

- YANG: `yang/example-cli.yang`
- エントリポイント: `cli.py`
- CLI ロジック本体: `cli_core.py`
- YANG パーサとメタデータ: `yang_model.py`

小さな YANG モデルから、以下を自動的に CLI として提供します。

- YANG の `rpc` を CLI コマンドにマッピング
- `container state` (config false) 配下の leaf を `show <leaf>` で参照
- YANG で指定した Python ハンドラを動的に import・実行
- prompt_toolkit による補完 (`show` や `hello` の引数など)

---

## 必要な環境

- Python 3.8 以降
- 追加ライブラリ
  - `prompt_toolkit`
  - `pyang`


---

## 起動方法

```bash
cd /home/iida/git/expt-confd/prompt
./cli.py             # 実行フラグが付いている場合
# もしくは
python3 cli.py
```

起動すると次のようなプロンプトが出ます。

```text
Example YANG CLI. Type 'help' or '?' for help.
ex>
```

---

## 基本的な使い方

### 組み込みコマンド

- `help` / `?`
  - 利用可能なコマンド一覧と、YANG から生成された RPC のヘルプを表示します。
- `exit` / `quit`
  - CLI を終了します。
- `bash`
  - `/usr/bin/bash` をそのまま起動し、終了すると CLI に戻ります。

### RPC コマンド

YANG の `rpc` は、そのまま 1 語目のコマンドとして利用できます。

例 (`yang/example-cli.yang` に定義されたもの):

- `hello name=<name>`
  - 例: `hello name=world`
- `add x=<int> y=<int>`
  - 例: `add x=1 y=2`
- `set-hostname hostname=<name>`
  - 例: `set-hostname hostname=router1`
- `ping <dest> [count]`
  - 例: `ping 8.8.8.8 3`

`hello` などの **kv スタイルの RPC** では:

- `hello ` と入力して Tab を押すと、YANG から取得した引数名に基づき `name=` が補完候補として出ます。
- 一度 `name=foo` と指定すると、同じ行では `name=` は補完候補から消えます。

`ping` のように `ex:rpc-arg-style "positional"` が付いた RPC では、
引数は位置引数として扱われ、補完は行いません。

### show コマンド (state の参照)

YANG の `container state { config false; ... }` 配下の leaf は、
`show <leaf>` で参照できます。

例:

- `show` だけを打つ
  - `state` コンテナ配下の全 leaf と現在値を一覧表示
- `show hostname`
- `show mgmt-ip`
- `show last-hello`
- `show last-add-result`
- `show last-ping-target`
- `show last-ping-success`
- `show route [ipv4|ipv6]`

`show route` のみ特別で、`show route` / `show route ipv4` / `show route ipv6`
の 3 パターンを受け付けます。
補完では、YANG の `ex:cli-completion "<CR> ipv4 ipv6"` に基づき、

- `show route ` + Tab → `<CR> ipv4 ipv6` の候補

を表示します（`<CR>` は「そのまま Enter で実行できる」という意味の
特別な表示専用トークンです）。

---

## コード構成と役割

### cli.py

- このディレクトリの **エントリポイント**。
- やっていることはシンプルです:
  1. 自身と同階層の `yang/` ディレクトリから YANG を読み込む
     (`load_example_yang()` を呼ぶ)
  2. `ExampleCli` インスタンスを作成
  3. `cli.run()` で対話 CLI を開始

### yang_model.py

- `YangModel` データクラスと、YANG を解析して `YangModel` を構築する
  `load_example_yang()` を提供します。
- `pyang` を使って `.yang` ファイルをパースし、構文木をたどりながら
  必要な情報だけを収集しています。

`YangModel` に含まれる主な情報:

- `rpc_names`: すべての `rpc` 名一覧
- `rpc_descriptions`: rpc ごとの `description` 文字列
- `rpc_handlers`: `ex:python-handler "module:function"` の値
- `rpc_usages`: `ex:cli-usage` による CLI 用 usage 文字列
- `rpc_arg_styles`: `ex:rpc-arg-style` の値 (`"kv"` / `"positional"` など)
- `rpc_input_params`: `rpc` の `input` セクション配下の `leaf` 名一覧
- `state_leaf_names`: `container state` 配下の leaf 名一覧
- `state_leaf_descriptions`: 各 state leaf の `description`
- `state_leaf_completions`: `ex:cli-completion` による補完候補リスト
- `state_leaf_handlers`: `ex:state-python-handler` による handler シンボル

これらはすべて、`cli_core.py` 側でヘルプ表示・補完・ハンドラ呼び出しなどに
利用されます。

### cli_core.py

このモジュールが CLI ロジックの本体です。

- `ExampleCli` クラス
  - プロンプト表示と入力ループ (`run()`)
  - 行ごとのパースとコマンド分岐 (`_handle_line()`)
  - `show` 実装 (`do_show()`)
  - 組み込み rpc 実装 (`_rpc_hello`, `_rpc_add`, `_rpc_set_hostname`, `_rpc_ping`)
  - `show route` の表示 (`_show_route_state()`)
  - 補助関数 (`_parse_key_value_args`, `_dispatch_handler` など)
- `CliCompleter` クラス
  - `prompt_toolkit` 用補完クラス
  - 以下のような補完ロジックを実装:
    - 1語目: 組み込みコマンド + YANG からの `rpc_names`
    - `show <leaf>`: YANG からの `state_leaf_names` と
      `state_leaf_completions` を利用
    - `hello` 等の kv スタイル RPC の引数部分: `rpc_input_params` を
      `name=` のような形式で補完候補にする
- YANG から参照されるハンドラ群
  - `rpc_hello`, `rpc_add`, `rpc_set_hostname`, `rpc_ping`
  - `state_hostname`, `state_mgmt_ip`, `state_last_hello`,
    `state_last_add_result`, `state_last_ping_target`,
    `state_last_ping_success`, `state_route`

YANG モデル側では、例えば次のようにハンドラを指定します。

```yang
rpc hello {
  ex:python-handler "cli_core:rpc_hello";
  ...
}

container state {
  leaf hostname {
    ...
    ex:state-python-handler "cli_core:state_hostname";
  }
}
```

`ExampleCli._dispatch_handler()` は、この `"cli_core:rpc_hello"` のような
`module:function` 文字列をもとに `importlib` でモジュールを import し、
`func(self, payload)` という形で呼び出します。

---

## 補完の仕組み (概要)

`CliCompleter` は、入力行を `shlex.split()` でトークンに分割し、

- トップレベル: `show`, `bash`, `exit`, `help`, `?`, そして全 `rpc_names`
- `show` 2語目: `state_leaf_names`
- `show <leaf> ...`: `state_leaf_completions[leaf]`
- kv スタイル RPC の 2語目以降: `rpc_input_params[rpc_name]` を
  `key=` 形式にして、未使用のもののみ候補に

というルールで候補を決定しています。

特別なトークン `<CR>` は、実際には文字を挿入せず、「このまま Enter を
押せばよい」という意味で表示専用に扱っています。

---

## YANG / ハンドラの追加方法

新しい RPC や state leaf を追加したい場合は、基本的に

1. `yang/example-cli.yang` を編集
2. 必要であれば `cli_core.py` にハンドラ関数を追加

の 2 ステップだけです（`cli.py` はそのままで OK）。

### 新しい RPC の追加

1. YANG に `rpc` を追加し、少なくとも以下を記述します。

   - `ex:python-handler "cli_core:rpc_new";`
   - `ex:cli-usage "new-rpc arg1=<...>";`
   - （kv スタイルなら）`input { leaf arg1 { ... } ... }`

2. `cli_core.py` に次の形の handler を追加します。

   ```python
   def rpc_new(cli: ExampleCli, args: Dict[str, str]) -> None:
       # args["arg1"] などを使って処理を書き、必要であれば
       # cli.state[...] を更新する
       ...
   ```

`load_example_yang()` が自動的に新しい rpc を拾い、CLI に反映します。

### 新しい state leaf の追加

1. YANG の `container state` の中に `leaf new-leaf { ... }` を追加します。
2. その leaf を特別な表示ロジックで扱いたい場合は、

   - `ex:state-python-handler "cli_core:state_new_leaf";`
   - `cli_core.py` に `state_new_leaf(cli: ExampleCli, args: Sequence[str])` を追加

とすることで、`show new-leaf` 実行時にその関数が呼ばれます。

---

## 参考

- YANG モデル本体: `yang/example-cli.yang`
- ConfD や YANG についての全体的な説明は、上位ディレクトリの
  `README.md` も参照してください。
