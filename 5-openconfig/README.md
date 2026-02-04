# 5-openconfig: OpenConfig YANG モデル実験環境

このディレクトリは、OpenConfig が公開している多数の YANG モジュールを ConfD 上で扱うための**実験用サンドボックス**です。

- `yang/` 配下に OpenConfig の各種 YANG モデルをまとめて配置
- `make all` で **トップレベル・モジュールを中心に一括コンパイル**
- `openconfig-system` モジュールを代表例として Python 名前空間を生成し、ConfD 上での挙動を確認
- 個々の YANG モジュールごとの詳細な解説は行わず、「全体構造の俯瞰」と「使い方」にフォーカスします

OpenConfig system モジュールの詳細な解説は、リポジトリ直下のドキュメントを参照してください。

- [README.openconfig-system.md](../README.openconfig-system.md)

---

## ディレクトリ構成

- `confd.conf` : ConfD の設定ファイル
- `Makefile`   : OpenConfig YANG のビルド／ConfD 起動を行うための Makefile
- `bin/`
  - `openconfig-system_ns.py` : `openconfig-system.yang` から自動生成された Python 名前空間
- `yang/` : OpenConfig YANG モジュール一式
  - `openconfig-system.yang` : システム全体の設定・状態を表す代表的なトップレベルモジュール
  - `openconfig-interfaces.yang`, `openconfig-network-instance.yang`, ほか多数
- `loadpath/` : `*.fxs` を出力するディレクトリ（`make all` 実行後に生成）
- `log/` : ConfD のログ出力
- `tmp/` : 一時ファイル

YANG モデルは数が多いため、**個々のファイルの詳細な説明はここでは行いません**。
必要に応じて、`pyang` などのツールでツリー表示を確認しながら読み進めてください。

---

## ビルドと起動方法

### 前提

- ConfD が `${HOME}/confd` などにインストールされている
- ConfD の YANG ソース (`$CONFD_DIR/src/confd/yang`) と Python モジュール `_confd` が参照可能
- Python 3 が利用可能

必要に応じて環境変数 `CONFD_DIR` を上書きしてください（デフォルト: `${HOME}/confd`）。

### 1. 初期化

```bash
cd 5-openconfig
make init
```

- 上位ディレクトリの `bin/init.sh` を呼び出し、ssh-keydir や基本設定ファイルを準備します。

### 2. すべての OpenConfig YANG をコンパイル

```bash
make all
```

`Makefile` では、次のような流れでビルドを行います。

1. `yang/` 配下の `*.yang` のうち、`module` 宣言を持つ **トップレベルモジュール**を列挙
2. 各モジュールごとに `confdc -c` で `loadpath/XXX.fxs` を生成
3. 代表モジュール `openconfig-system` から Python 名前空間
   `bin/openconfig_system_ns.py` を生成

これにより、OpenConfig の主要モジュールを ConfD で読み込める状態になります。

### 3. ConfD の起動

```bash
make start
```

- 内部的に `make all` を実行したあと、`confd -c confd.conf` で ConfD を起動します。
- ConfD のログは `log/` 配下に出力されます。

### 4. ConfD CLI からモデルを確認

J スタイル CLI の例:

```bash
make cli

# CLI 内での操作例
show configuration system
show configuration ntp
show configuration aaa
```

- `openconfig-system.yang` をはじめとする OpenConfig モデルに対応した階層構造が
  CLI に反映されていることを確認できます。
- モジュールの構造を詳しく読みたい場合は、別途 `pyang` を利用してツリーを表示するのがおすすめです。

```bash
cd yang
pyang -f tree openconfig-system.yang
pyang -f tree openconfig-interfaces.yang
```

### 5. 停止

```bash
make stop
```

- 起動中の ConfD プロセスを停止します。

---

## OpenConfig モデルの読み方

各 YANG ファイルは、OpenConfig プロジェクトが定義する**論理的な機能単位**ごとに分割されています。
例:

- `openconfig-system*.yang` : システム全体（ホスト名・クロック・DNS・AAA など）
- `openconfig-interfaces*.yang` : 物理／論理インタフェース
- `openconfig-network-instance*.yang` : VRF・L2/L3 ネットワークインスタンス
- `openconfig-bgp*.yang` : BGP
- `openconfig-mpls*.yang` : MPLS
- `openconfig-telemetry*.yang` : Telemetry / gNMI

本ディレクトリの目的は、

- これらのモジュールをまとめて ConfD でコンパイル・ロードしてみる
- 実際の CLI 階層やデータツリーを触りながら、OpenConfig モデルの雰囲気をつかむ

ことであり、**個々のモジュールの仕様をすべて解説することではありません**。

詳細な概念解説や `openconfig-system` モジュールの読み解き方については、
先述の [README.openconfig-system.md](../README.openconfig-system.md) を参照してください。
