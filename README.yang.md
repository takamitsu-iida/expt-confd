# YANG入門ガイド

## 目次

1. [YANGとは](#yangとは)
2. [YANGの基本構造](#yangの基本構造)
3. [実践例: ネットワークデバイス設定モデル](#実践例-ネットワークデバイス設定モデル)
4. [YANGの使い方](#yangの使い方)
5. [よくあるパターン](#よくあるパターン)

---

## YANGとは

**YANG (Yet Another Next Generation)** は、ネットワーク機器の設定データや運用データをモデル化するためのデータモデリング言語です。

### 主な特徴

- **標準化**: IETF RFC 6020/7950で標準化
- **プロトコル非依存**: NETCONF、RESTCONF、gNMI等で使用可能
- **階層構造**: XMLのような木構造でデータを表現
- **型安全**: データ型、制約、検証ルールを定義可能
- **ツール対応**: 自動コード生成、ドキュメント生成が可能

### YANGが解決する課題

1. **設定の標準化**: ベンダー固有のCLIから標準APIへ
2. **自動化**: プログラムから設定を制御
3. **検証**: 設定ミスを事前に検出
4. **ドキュメント**: モデル自体がドキュメントとして機能

---

## YANGの基本構造

### モジュール定義

```yang
module network-device {
  namespace "http://example.com/ns/network-device";
  prefix nd;

  organization "Example Corp";
  revision 2026-01-26 {
    description "初版リリース。";
  }
}
```

- **namespace**: 一意の名前空間URI
- **prefix**: 他モジュールから参照する際の短縮名
- **revision**: バージョン管理

### 主要な構文要素

#### 1. container - 設定のグループ化

```yang
container system {
  description "システム全体の設定";

  leaf hostname {
    type string;
    default "Router";
  }
}
```

**使用例（XML）**:
```xml
<system>
  <hostname>MyRouter</hostname>
</system>
```

#### 2. leaf - 単一の値

```yang
leaf hostname {
  type string {
    length "1..63";
    pattern '[a-zA-Z0-9][a-zA-Z0-9-]*';
  }
  default "Router";
  description "デバイスのホスト名";
}
```

**制約**:
- **type**: データ型（string, int32, boolean等）
- **length/range**: 値の範囲制限
- **pattern**: 正規表現による形式制約
- **default**: デフォルト値

#### 3. leaf-list - 同じ型の複数の値

```yang
leaf-list name-server {
  type inet:ip-address;
  max-elements 8;
  description "DNSサーバのリスト";
}
```

**使用例（XML）**:
```xml
<system>
  <name-server>8.8.8.8</name-server>
  <name-server>8.8.4.4</name-server>
</system>
```

#### 4. list - 複数のエントリ（最重要）

```yang
list interface {
  key "name";  // 各エントリを識別する一意のキー

  leaf name {
    type string;
  }

  leaf description {
    type string;
  }

  leaf enabled {
    type boolean;
    default "true";
  }
}
```

**使用例（XML）**:
```xml
<interfaces>
  <interface>
    <name>GigabitEthernet0/0</name>
    <description>Uplink</description>
    <enabled>true</enabled>
  </interface>
  <interface>
    <name>FastEthernet1/0</name>
    <description>Server</description>
    <enabled>true</enabled>
  </interface>
</interfaces>
```

**keyの役割**:
- リスト内の各エントリを一意に識別
- REST APIでのパス指定: `/interfaces/interface=GigabitEthernet0%2F0`
- データベースの主キーと同じ概念

#### 5. choice - 排他的な選択肢

```yang
choice address-config {
  case static {
    container ipv4 {
      leaf address {
        type inet:ipv4-address;
      }
      leaf netmask {
        type inet:ipv4-address;
      }
    }
  }

  case dhcp {
    leaf dhcp-client {
      type boolean;
    }
  }
}
```

**意味**: スタティックIPとDHCPは同時に設定できない

#### 6. typedef - カスタム型定義

```yang
typedef interface-name {
  type string {
    pattern 'GigabitEthernet[0-9]+(/[0-9]+)*|'
          + 'FastEthernet[0-9]+(/[0-9]+)*|'
          + 'Loopback[0-9]+';
  }
  description "インタフェース名の形式";
}

// 使用
leaf name {
  type interface-name;  // 再利用
}
```

### 条件付き設定

#### when - 条件によって設定可能かを制御

```yang
container switchport {
  when "starts-with(../name, 'GigabitEthernet') or
        starts-with(../name, 'FastEthernet')";
  description "物理ポートの場合のみ設定可能";

  leaf mode {
    type enumeration {
      enum access;
      enum trunk;
    }
  }

  leaf access-vlan {
    when "../mode = 'access'";  // accessモード時のみ
    type uint16;
  }
}
```

#### must - バリデーションルール

```yang
leaf secondary-address {
  type inet:ipv4-address;
  must "../address" {
    error-message "プライマリアドレスを先に設定してください";
  }
}
```

#### mandatory - 必須設定

```yang
leaf router-id {
  type yang:dotted-quad;
  mandatory true;  // 必ず設定が必要
}
```

---

## 実践例: ネットワークデバイス設定モデル

`network-device.yang`を例に、実際のYANGモデルを見ていきます。

### 例1: システム設定

```yang
container system {
  leaf hostname {
    type string {
      length "1..63";
      pattern '[a-zA-Z0-9][a-zA-Z0-9-]*';
    }
    default "Router";
  }

  leaf domain-name {
    type inet:domain-name;
  }

  leaf-list name-server {
    type inet:ip-address;
    max-elements 8;
  }
}
```

**設定データ例（JSON）**:
```json
{
  "system": {
    "hostname": "CoreRouter01",
    "domain-name": "example.com",
    "name-server": [
      "8.8.8.8",
      "8.8.4.4"
    ]
  }
}
```

### 例2: インタフェース設定（listの使用）

```yang
container interfaces {
  list interface {
    key "name";

    leaf name {
      type interface-name;
    }

    leaf description {
      type string;
    }

    leaf enabled {
      type boolean;
      default "true";
    }

    leaf mtu {
      type uint16 {
        range "64..9216";
      }
      default "1500";
    }
  }
}
```

**設定データ例（JSON）**:
```json
{
  "interfaces": {
    "interface": [
      {
        "name": "GigabitEthernet0/0",
        "description": "Uplink to Core Switch",
        "enabled": true,
        "mtu": 1500
      },
      {
        "name": "GigabitEthernet0/1",
        "description": "Server Connection",
        "enabled": true,
        "mtu": 9000
      }
    ]
  }
}
```

### 例3: IPアドレス設定（choiceの使用）

```yang
choice address-config {
  case static {
    container ipv4 {
      leaf address {
        type inet:ipv4-address;
      }
      leaf netmask {
        type inet:ipv4-address;
      }
    }
  }

  case dhcp {
    leaf dhcp-client {
      type boolean;
    }
  }
}
```

**スタティックIP設定例**:
```json
{
  "interface": {
    "name": "GigabitEthernet0/0",
    "ipv4": {
      "address": "192.168.1.1",
      "netmask": "255.255.255.0"
    }
  }
}
```

**DHCP設定例**:
```json
{
  "interface": {
    "name": "GigabitEthernet0/1",
    "dhcp-client": true
  }
}
```

**注意**: `ipv4`と`dhcp-client`は同時に設定できない（choiceにより排他的）

### 例4: スイッチポート設定（whenの使用）

```yang
container switchport {
  when "starts-with(../name, 'GigabitEthernet') or
        starts-with(../name, 'FastEthernet')";

  leaf mode {
    type enumeration {
      enum access;
      enum trunk;
    }
  }

  leaf access-vlan {
    when "../mode = 'access'";
    type uint16;
    default "1";
  }

  leaf-list trunk-allowed-vlans {
    when "../mode = 'trunk'";
    type uint16;
  }
}
```

**アクセスポート設定例**:
```json
{
  "interface": {
    "name": "GigabitEthernet0/1",
    "switchport": {
      "mode": "access",
      "access-vlan": 10
    }
  }
}
```

**制約**:
- `switchport`はGigabitEthernet/FastEthernetのみ設定可能（when条件）
- `access-vlan`はmode=accessの時のみ設定可能
- `trunk-allowed-vlans`はmode=trunkの時のみ設定可能

### 例5: ルーティング設定

```yang
container routing {
  container static {
    list route {
      key "destination";

      leaf destination {
        type inet:ip-prefix;
      }

      choice next-hop-type {
        mandatory true;

        case next-hop-address {
          leaf next-hop {
            type inet:ip-address;
          }
        }

        case outgoing-interface {
          leaf interface {
            type interface-name;
          }
        }
      }

      leaf distance {
        type uint8 {
          range "1..255";
        }
        default "1";
      }
    }
  }
}
```

**スタティックルート設定例**:
```json
{
  "routing": {
    "static": {
      "route": [
        {
          "destination": "10.0.0.0/8",
          "next-hop": "192.168.1.254",
          "distance": 1
        },
        {
          "destination": "0.0.0.0/0",
          "interface": "GigabitEthernet0/0"
        }
      ]
    }
  }
}
```

---

## YANGの使い方

### 1. 開発フロー

```
┌─────────────────┐
│ YANGモデル作成  │  network-device.yang
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ コンパイル      │  pyang, ydk-gen等
│ (検証・生成)    │
└────────┬────────┘
         │
         ├──→ サーバーコード生成 (ConfD, Netopeer2等)
         ├──→ クライアントコード生成 (Python, Go等)
         └──→ ドキュメント生成 (HTML, PDF等)
```

### 2. ツール

#### pyang - YANGコンパイラ/バリデーター

```bash
# 構文チェック
pyang network-device.yang

# ツリー形式で表示
pyang -f tree network-device.yang

# HTML ドキュメント生成
pyang -f jstree network-device.yang -o network-device.html
```

#### ConfD - YANG実装プラットフォーム

- YANGモデルからNETCONF/RESTCONFサーバーを自動生成
- トランザクション管理、検証、ロールバック機能

```bash
# YANGコンパイル
confdc -c network-device.yang

# サーバー起動
confd
```

#### YDK (YANG Development Kit)

- YANGモデルからクライアントコード（Python, C++, Go）を生成

```python
from ydk.models.network_device import network_device

# オブジェクトベースで設定
config = network_device.System()
config.hostname = "Router01"
config.domain_name = "example.com"

# NETCONF/RESTCONFで送信
provider.create(config)
```

### 3. プロトコルとの関係

#### NETCONF (XML)

```xml
<rpc message-id="1" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <edit-config>
    <target><candidate/></target>
    <config>
      <system xmlns="http://example.com/ns/network-device">
        <hostname>Router01</hostname>
        <domain-name>example.com</domain-name>
      </system>
    </config>
  </edit-config>
</rpc>
```

#### RESTCONF (JSON)

```bash
# GET - 設定取得
curl -X GET \
  https://router/restconf/data/network-device:system \
  -H "Accept: application/yang-data+json"

# PUT - 設定変更
curl -X PUT \
  https://router/restconf/data/network-device:system/hostname \
  -H "Content-Type: application/yang-data+json" \
  -d '{"hostname": "Router01"}'

# POST - リストエントリ追加
curl -X POST \
  https://router/restconf/data/network-device:interfaces/interface \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "interface": {
      "name": "GigabitEthernet0/0",
      "description": "Uplink",
      "enabled": true
    }
  }'
```

### 4. Pythonクライアント例

```python
import requests
from requests.auth import HTTPBasicAuth

# RESTCONFエンドポイント
base_url = "https://router/restconf/data/network-device:"
auth = HTTPBasicAuth("admin", "password")
headers = {"Content-Type": "application/yang-data+json"}

# インタフェース追加
interface_config = {
    "interface": {
        "name": "GigabitEthernet0/0",
        "description": "Uplink to Core",
        "enabled": True,
        "ipv4": {
            "address": "192.168.1.1",
            "netmask": "255.255.255.0"
        }
    }
}

response = requests.post(
    f"{base_url}interfaces/interface",
    json=interface_config,
    auth=auth,
    headers=headers,
    verify=False
)

# 設定取得
response = requests.get(
    f"{base_url}interfaces/interface=GigabitEthernet0%2F0",
    auth=auth,
    verify=False
)
config = response.json()
print(config["interface"]["description"])
```

---

## よくあるパターン

### パターン1: 状態管理（config vs state）

```yang
container interface-state {
  config false;  // 読み取り専用（運用データ）

  list interface {
    key "name";

    leaf name {
      type string;
    }

    leaf oper-status {
      type enumeration {
        enum up;
        enum down;
      }
    }

    leaf speed {
      type uint64;
      units "bits/second";
    }

    container statistics {
      leaf in-octets {
        type yang:counter64;
      }
      leaf out-octets {
        type yang:counter64;
      }
    }
  }
}
```

### パターン2: augment（既存モデルの拡張）

```yang
// 別モジュールで定義されたインタフェースを拡張
augment "/if:interfaces/if:interface" {
  container custom-settings {
    leaf custom-param {
      type string;
    }
  }
}
```

### パターン3: grouping（再利用可能な定義）

```yang
grouping ip-address-config {
  leaf address {
    type inet:ip-address;
  }
  leaf netmask {
    type inet:ip-address;
  }
}

container ipv4 {
  uses ip-address-config;
  leaf secondary-address {
    type inet:ip-address;
  }
}
```

### パターン4: RPC（操作定義）

```yang
rpc restart-interface {
  description "インタフェースの再起動";

  input {
    leaf interface-name {
      type interface-name;
      mandatory true;
    }
  }

  output {
    leaf status {
      type enumeration {
        enum success;
        enum failed;
      }
    }
    leaf message {
      type string;
    }
  }
}
```

**使用例**:
```bash
curl -X POST \
  https://router/restconf/operations/network-device:restart-interface \
  -d '{"input": {"interface-name": "GigabitEthernet0/0"}}'
```

### パターン5: notification（イベント通知）

```yang
notification interface-state-change {
  description "インタフェース状態変更通知";

  leaf interface-name {
    type interface-name;
  }

  leaf new-state {
    type enumeration {
      enum up;
      enum down;
    }
  }

  leaf timestamp {
    type yang:date-and-time;
  }
}
```

---

## まとめ

### YANGを使うメリット

1. **標準化**: ベンダー非依存の設定インターフェース
2. **自動化**: プログラムから機器を制御可能
3. **検証**: 設定ミスを事前に防止
4. **ドキュメント**: モデルがそのまま仕様書
5. **ツール**: コード生成、自動テスト等のエコシステム

### ベストプラクティス

1. **明確な命名**: 意味のわかりやすい名前を使用
2. **詳細なdescription**: 各要素に説明を記載
3. **適切な制約**: range, pattern, when, must等を活用
4. **モジュール分割**: 機能ごとにモジュールを分ける
5. **バージョン管理**: revisionで変更履歴を記録

### 次のステップ

1. `pyang`をインストールして実際にYANGモデルを検証
2. ConfDやNetopeer2でYANGベースのサーバーを構築
3. RESTCONFクライアントを実装して設定を自動化
4. 既存の標準YANGモデル（IETF, OpenConfig等）を参照

### 参考リソース

- **RFC 7950**: YANG 1.1仕様
- **RFC 8040**: RESTCONF仕様
- **RFC 6241**: NETCONF仕様
- **pyang**: https://github.com/mbj4668/pyang
- **YANG Catalog**: https://yangcatalog.org/
- **OpenConfig**: http://openconfig.net/

---

*このドキュメントは `network-device.yang` を例として作成されました。*
