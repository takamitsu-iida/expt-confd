# 5-openconfig: OpenConfig YANG モデル実験環境

このディレクトリは、OpenConfig が公開している多数の YANG モジュールを ConfD 上で扱うための**実験用サンドボックス**です。

- `yang/` 配下に OpenConfig の各種 YANG モデルをまとめて配置
- `make all` で **トップレベル・モジュールを中心に一括コンパイル**
- `openconfig-system` モジュールを代表例として Python 名前空間を生成し、ConfD 上での挙動を確認
- 個々の YANG モジュールごとの詳細な解説は行わず、「全体構造の俯瞰」と「使い方」にフォーカスします

OpenConfig system モジュールの詳細な解説は、この README の後半にまとめてあります。

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
この README の後半 [YANG / OpenConfig の基礎](#yang--openconfig-の基礎) および
[openconfig-system モジュールの読み方](#openconfig-system-モジュールの読み方) を参照してください。

---

## YANG / OpenConfig の基礎

### YANG とは

YANG (Yet Another Next Generation) は、ネットワーク設定とステートデータをモデル化するための
データモデリング言語です。RFC 6020 / RFC 7950 で標準化されており、NETCONF、RESTCONF、gNMI
などのプロトコルと組み合わせて使用されます。

主な特徴:

- **階層的なデータ構造**: ツリー構造でデータを表現
- **設定と状態の分離**: `config true/false` で明確に区別
- **型の厳密性**: 強力な型システムによるデータ検証
- **再利用性**: `grouping`、`typedef`、`identity` などで再利用可能な定義を作成
- **拡張性**: `augment` や `deviation` で既存モデルを拡張・変更可能

### モジュールの基本構造

典型的な YANG モジュールは次のような形をしています。

```yang
module <モジュール名> {
  yang-version "1";
  namespace "<名前空間URI>";
  prefix "<プレフィックス>";

  organization "組織名";
  contact "連絡先";
  description "モジュールの説明";

  import <他のモジュール> { prefix <プレフィックス>; }

  revision "YYYY-MM-DD" {
    description "変更内容";
  }

  // データ定義
}
```

`openconfig-system.yang` もこの基本パターンに従います。

```yang
module openconfig-system {
  yang-version "1";
  namespace "http://openconfig.net/yang/system";
  prefix "oc-sys";

  import openconfig-inet-types { prefix oc-inet; }
  import openconfig-yang-types { prefix oc-yang; }
  import openconfig-types { prefix oc-types; }

  organization "OpenConfig working group";
  contact "OpenConfig working group netopenconfig@googlegroups.com";

  description
    "Model for managing system-wide services and functions on
    network devices.";
}
```

### pyang によるツリー表示

YANG モジュールの構造を可視化するには `pyang -f tree` が便利です。

```bash
pyang -f tree openconfig-system.yang
```

ツリー表記の主な記号:

- `+--rw` : 読み書き可能なノード（config true）
- `+--ro` : 読み取り専用ノード（config false）
- `?`     : オプショナル（存在しなくてもよい）
- `*`     : 0 個以上の要素を持つリストまたは leaf-list
- `[key]` : リストのキー
- `->`    : `leafref` による参照

`openconfig-system` のトップレベル部は概ね次のようになります（抜粋）。

```
module: openconfig-system
  +--rw system
     +--rw config
     |  +--rw hostname?       oc-inet:domain-name
     |  +--rw domain-name?    oc-inet:domain-name
     |  +--rw login-banner?   string
     |  +--rw motd-banner?    string
     +--ro state
     |  +--ro hostname?           oc-inet:domain-name
     |  +--ro domain-name?        oc-inet:domain-name
     |  +--ro current-datetime?   oc-yang:date-and-time
     |  +--ro boot-time?          oc-types:timeticks64
     +--rw clock
     +--rw dns
     +--rw ntp
     +--rw aaa
     +--ro cpus
     +--ro processes
     +--ro alarms
```

---

## openconfig-system モジュールの読み方

### モジュールの目的と機能領域

`openconfig-system.yang` は、ネットワークデバイスのシステム全体に関わるサービスや機能を
管理するためのモデルです。主な機能領域は次の通りです。

1. **システムグローバル設定**: ホスト名 / ドメイン名 / ログインバナー / MOTD バナー
2. **クロック (clock)**: タイムゾーン、現在時刻、ブート時刻
3. **DNS (dns)**: 検索ドメイン、DNS サーバーリスト、静的ホストエントリ
4. **NTP (ntp)**: NTP サーバー設定、認証、同期状態
5. **AAA (aaa)**: ローカルユーザーやサーバーグループ
6. **監視系**: CPU 使用率、プロセス情報、アラーム

### OpenConfig の代表的なパターン

#### 1. `config` / `state` 分離

設定データと状態データを必ず分離するのが OpenConfig 流です。

```yang
container <name> {
  container config {
    // 設定可能なパラメータ
    uses <name>-config;
  }

  container state {
    config false;  // 読み取り専用の状態データ
    uses <name>-config;
    uses <name>-state;
  }
}
```

- API 上も「設定を書く場所」と「状態を読む場所」が明確
- gNMI などで状態だけをサブスクライブする場合にも分かりやすい構造になります。

#### 2. `grouping` / `uses` による再利用

設定や状態の共通部分は `grouping` としてまとめ、`uses` で展開します。

```yang
grouping system-global-config {
  description "system-wide configuration parameters";

  leaf hostname {
    type oc-inet:domain-name;
  }

  leaf domain-name {
    type oc-inet:domain-name;
  }
}

container system {
  container config {
    uses system-global-config;
  }
}
```

#### 3. `leafref` を使ったキー参照

OpenConfig では、リストのキーを `leafref` で実体の leaf に紐付けるパターンが多用されます。

```yang
list server {
  key "address";  // キーの宣言

  leaf address {
    type leafref {
      path "../config/address";  // config/address を参照
    }
  }

  container config {
    leaf address {
      type oc-inet:ip-address;    // 実体の型定義
    }
    leaf port {
      type oc-inet:port-number;
      default 53;
    }
  }
}
```

- ユーザは `config/address` に値を書くだけでよい
- キー (`server/address`) と実体 (`config/address`) の整合性が自動的に保たれる

#### 4. DNS 設定モデルの例

`openconfig-system` の DNS 部分は概ね次のような構造です。

```yang
grouping system-dns-config {
  leaf-list search {
    type oc-inet:domain-name;
    ordered-by user;
  }
}

grouping system-dns-servers-config {
  leaf address {
    type oc-inet:ip-address;
  }
  leaf port {
    type oc-inet:port-number;
    default 53;
  }
}

container dns {
  container config {
    uses system-dns-config;
  }

  container servers {
    list server {
      key "address";

      leaf address {
        type leafref {
          path "../config/address";
        }
      }

      container config {
        uses system-dns-servers-config;
      }
    }
  }
}
```

このモデルからは、次のような XML / JSON データが想定されます。

```xml
<dns>
  <config>
    <search>example.com</search>
  </config>
  <servers>
    <server>
      <address>8.8.8.8</address>
      <config>
        <address>8.8.8.8</address>
        <port>53</port>
      </config>
    </server>
  </servers>
</dns>
```

```json
{
  "dns": {
    "config": {
      "search": ["example.com"]
    },
    "servers": {
      "server": [
        {
          "address": "8.8.8.8",
          "config": {
            "address": "8.8.8.8",
            "port": 53
          }
        }
      ]
    }
  }
}
```

「YANG モデル → 実際のデータ表現」のイメージをつかむのに便利な例です。

### リビジョン管理

OpenConfig モジュールは `revision` でバージョン管理されます。

```yang
oc-ext:openconfig-version "0.8.0";

revision "2019-03-15" {
  description "Update boot time to be nanoseconds since epoch.";
  reference "0.8.0";
}

revision "2019-01-29" {
  description "Add messages module to the system model";
  reference "0.7.0";
}
```

どの revision がどの OpenConfig バージョンに対応するかが明示されており、
機能追加や非互換変更の履歴を追いやすくなっています。

---

## まとめと参考情報

この README 一つで、

- 実験環境としての使い方
- YANG / OpenConfig の基礎
- `openconfig-system` モジュールの読み方

までを一通り追えるように構成しています。さらに深掘りしたい場合は、

- `yang/openconfig-*.yang` を直接読む
- `pyang -f tree` でツリーを眺める
- OpenConfig 公式リポジトリ (https://github.com/openconfig/public) を参照する

といった形で進めると理解が進みます。
