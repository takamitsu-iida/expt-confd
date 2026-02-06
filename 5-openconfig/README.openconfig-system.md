# YANG (Yet Another Next Generation) 解説

## 目次
1. [YANGとは](#yangとは)
2. [YANGの基本構造](#yangの基本構造)
3. [主要な文(Statement)](#主要な文statement)
4. [データモデリングの例](#データモデリングの例)
5. [OpenConfig systemモジュールの解説](#openconfig-systemモジュールの解説)

---

## YANGとは

YANG (Yet Another Next Generation) は、ネットワーク設定とステートデータをモデル化するためのデータモデリング言語です。RFC 6020で標準化されており、NETCONF、RESTCONF、gNMIなどのプロトコルと組み合わせて使用されます。

### YANGの特徴
- **階層的なデータ構造**: ツリー構造でデータを表現
- **設定と状態の分離**: config true/falseで明確に区別
- **型の厳密性**: 強力な型システムによるデータ検証
- **再利用性**: grouping、typedef、identityなどで再利用可能な定義を作成
- **拡張性**: augmentやdeviationで既存モデルを拡張・変更可能

---

## YANGの基本構造

### モジュールの基本構成

```yang
module <モジュール名> {
  yang-version "1";           // YANGのバージョン
  namespace "<名前空間URI>";   // グローバルに一意な識別子
  prefix "<プレフィックス>";   // モジュール内で使用する短縮名

  // メタデータ
  organization "組織名";
  contact "連絡先";
  description "モジュールの説明";

  // インポート
  import <他のモジュール> { prefix <プレフィックス>; }

  // リビジョン履歴
  revision "YYYY-MM-DD" {
    description "変更内容";
  }

  // データ定義
  // ...
}
```

### openconfig-system.yangの例

```yang
module openconfig-system {
  yang-version "1";
  namespace "http://openconfig.net/yang/system";
  prefix "oc-sys";

  // 他のモジュールのインポート
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

### pyangによるツリー表示

YANGモジュールの構造を可視化するために、`pyang -f tree`コマンドを使用できます。これにより、データモデルの階層構造が分かりやすく表示されます。

```bash
pyang -f tree openconfig-system.yang
```

#### ツリー表記の見方

- `+--rw`: 読み書き可能なノード（config true）
- `+--ro`: 読み取り専用のノード（config false）
- `?`: オプショナル（存在しなくてもよい）
- `*`: 0個以上の要素を持つリストまたはleaf-list
- `[key]`: リストのキー
- `->`: leafrefによる参照

#### openconfig-system.yangのツリー構造（抜粋）

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
     |  +--ro login-banner?       string
     |  +--ro motd-banner?        string
     |  +--ro current-datetime?   oc-yang:date-and-time
     |  +--ro boot-time?          oc-types:timeticks64
     +--rw clock
     |  +--rw config
     |  |  +--rw timezone-name?   timezone-name-type
     |  +--ro state
     |     +--ro timezone-name?   timezone-name-type
     +--rw dns
     |  +--rw config
     |  |  +--rw search*   oc-inet:domain-name
     |  +--ro state
     |  |  +--ro search*   oc-inet:domain-name
     |  +--rw servers
     |  |  +--rw server* [address]
     |  |     +--rw address    -> ../config/address
     |  |     +--rw config
     |  |     |  +--rw address?   oc-inet:ip-address
     |  |     |  +--rw port?      oc-inet:port-number
     |  |     +--ro state
     |  |        +--ro address?   oc-inet:ip-address
     |  |        +--ro port?      oc-inet:port-number
     |  +--rw host-entries
     |     +--rw host-entry* [hostname]
     |        +--rw hostname    -> ../config/hostname
     |        +--rw config
     |        |  +--rw hostname?       string
     |        |  +--rw alias*          string
     |        |  +--rw ipv4-address*   oc-inet:ipv4-address
     |        |  +--rw ipv6-address*   oc-inet:ipv6-address
     |        +--ro state
     |           +--ro hostname?       string
     |           +--ro alias*          string
     |           +--ro ipv4-address*   oc-inet:ipv4-address
     |           +--ro ipv6-address*   oc-inet:ipv6-address
     +--rw ntp
     |  +--rw config
     |  |  +--rw enabled?              boolean
     |  |  +--rw ntp-source-address?   oc-inet:ip-address
     |  |  +--rw enable-ntp-auth?      boolean
     |  +--ro state
     |  |  +--ro enabled?              boolean
     |  |  +--ro ntp-source-address?   oc-inet:ip-address
     |  |  +--ro enable-ntp-auth?      boolean
     |  |  +--ro auth-mismatch?        oc-yang:counter64
     |  +--rw ntp-keys
     |  |  +--rw ntp-key* [key-id]
     |  |     +--rw key-id    -> ../config/key-id
     |  |     +--rw config
     |  |     |  +--rw key-id?      uint16
     |  |     |  +--rw key-type?    identityref
     |  |     |  +--rw key-value?   string
     |  |     +--ro state
     |  |        +--ro key-id?      uint16
     |  |        +--ro key-type?    identityref
     |  |        +--ro key-value?   string
     |  +--rw servers
     |     +--rw server* [address]
     |        +--rw address    -> ../config/address
     |        +--rw config
     |        |  +--rw address?            oc-inet:host
     |        |  +--rw port?               oc-inet:port-number
     |        |  +--rw version?            uint8
     |        |  +--rw association-type?   enumeration
     |        |  +--rw iburst?             boolean
     |        |  +--rw prefer?             boolean
     |        +--ro state
     |           +--ro address?            oc-inet:host
     |           +--ro port?               oc-inet:port-number
     |           +--ro version?            uint8
     |           +--ro association-type?   enumeration
     |           +--ro iburst?             boolean
     |           +--ro prefer?             boolean
     |           +--ro stratum?            uint8
     |           +--ro root-delay?         uint32
     |           +--ro root-dispersion?    uint64
     |           +--ro offset?             uint64
     |           +--ro poll-interval?      uint32
     +--rw aaa
     |  +--rw authentication
     |  |  +--rw config
     |  |  |  +--rw authentication-method*   union
     |  |  +--ro state
     |  |  |  +--ro authentication-method*   union
     |  |  +--rw admin-user
     |  |  |  +--rw config
     |  |  |  |  +--rw admin-password?          string
     |  |  |  |  +--rw admin-password-hashed?   oc-aaa-types:crypt-password-type
     |  |  |  +--ro state
     |  |  |     +--ro admin-password?          string
     |  |  |     +--ro admin-password-hashed?   oc-aaa-types:crypt-password-type
     |  |  |     +--ro admin-username?          string
     |  |  +--rw users
     |  |     +--rw user* [username]
     |  |        +--rw username    -> ../config/username
     |  |        +--rw config
     |  |        |  +--rw username?          string
     |  |        |  +--rw password?          string
     |  |        |  +--rw password-hashed?   oc-aaa-types:crypt-password-type
     |  |        |  +--rw ssh-key?           string
     |  |        |  +--rw role?              union
     |  |        +--ro state
     |  |           +--ro username?          string
     |  |           +--ro password?          string
     |  |           +--ro password-hashed?   oc-aaa-types:crypt-password-type
     |  |           +--ro ssh-key?           string
     |  |           +--ro role?              union
     |  +--rw server-groups
     |     +--rw server-group* [name]
     |        +--rw name       -> ../config/name
     |        +--rw servers
     |           +--rw server* [address]
     |              +--rw address    -> ../config/address
     |              +--rw config
     |              |  +--rw address?   oc-inet:ip-address
     |              +--ro state
     |              |  +--ro address?               oc-inet:ip-address
     |              |  +--ro connection-opens?      oc-yang:counter64
     |              |  +--ro connection-closes?     oc-yang:counter64
     |              |  +--ro messages-sent?         oc-yang:counter64
     |              |  +--ro messages-received?     oc-yang:counter64
     |              +--rw tacacs
     |              |  +--rw config
     |              |  |  +--rw port?             oc-inet:port-number
     |              |  |  +--rw secret-key?       oc-types:routing-password
     |              |  +--ro state
     |              |     +--ro port?             oc-inet:port-number
     |              +--rw radius
     |                 +--rw config
     |                 |  +--rw auth-port?             oc-inet:port-number
     |                 |  +--rw secret-key?            oc-types:routing-password
     |                 +--ro state
     |                    +--ro auth-port?             oc-inet:port-number
     |                    +--ro counters
     |                       +--ro access-accepts?            oc-yang:counter64
     |                       +--ro access-rejects?            oc-yang:counter64
     +--ro cpus
     |  +--ro cpu* [index]
     |     +--ro index    -> ../state/index
     |     +--ro state
     |        +--ro index?    union
     |        +--ro total
     |        |  +--ro instant?    oc-types:percentage
     |        |  +--ro avg?        oc-types:percentage
     |        |  +--ro min?        oc-types:percentage
     |        |  +--ro max?        oc-types:percentage
     |        +--ro user
     |        |  +--ro instant?    oc-types:percentage
     |        |  +--ro avg?        oc-types:percentage
     |        +--ro kernel
     |        |  +--ro instant?    oc-types:percentage
     |        +--ro idle
     |           +--ro instant?    oc-types:percentage
     +--ro processes
     |  +--ro process* [pid]
     |     +--ro pid      -> ../state/pid
     |     +--ro state
     |        +--ro pid?                  uint64
     |        +--ro name?                 string
     |        +--ro cpu-utilization?      oc-types:percentage
     |        +--ro memory-usage?         uint64
     +--ro alarms
        +--ro alarm* [id]
           +--ro id        -> ../state/id
           +--ro state
              +--ro id?             string
              +--ro resource?       string
              +--ro text?           string
              +--ro severity?       identityref
```

#### ツリーから読み取れる重要なポイント

1. **階層構造**: すべてのデータは`system`コンテナの下に配置
2. **config/stateパターン**: 各セクションで一貫して使用
3. **leafref参照**: リストのキーは`->`記号で表示（例: `address -> ../config/address`）
4. **データ型**: 各leafの後に型が表示（例: `oc-inet:ip-address`）
5. **リスト**: `*`印とキー `[key-name]` で識別
6. **読み取り専用データ**: `+--ro`で始まるノード（状態データ、統計情報など）

この可視化により、YANGモデルの全体像を素早く把握でき、APIのパス設計やデータ構造の理解に役立ちます。

---

## 主要な文(Statement)

### 1. データノードの定義

#### container
関連するデータをグループ化するためのノード

```yang
container clock {
  description "Top-level container for clock configuration data";

  container config {
    description "Configuration data for system clock";
    uses system-clock-config;
  }

  container state {
    config false;
    description "Operational state data for system clock";
    uses system-clock-config;
    uses system-clock-state;
  }
}
```

#### leaf
単一の値を持つデータノード

```yang
leaf hostname {
  type oc-inet:domain-name;
  description
    "The hostname of the device -- should be a single domain
    label, without the domain.";
}

leaf port {
  type oc-inet:port-number;
  default 53;
  description "The port number of the DNS server.";
}
```

#### leaf-list
同じ型の値のリスト

```yang
leaf-list search {
  type oc-inet:domain-name;
  ordered-by user;
  description
    "An ordered list of domains to search when resolving
    a host name.";
}
```

#### list
複数のエントリを持つリスト（キーで識別）

```yang
list server {
  key "address";
  ordered-by user;
  description "List of the DNS servers that the resolver should query.";

  leaf address {
    type leafref {
      path "../config/address";
    }
    description "References the configured address of the DNS server";
  }

  container config {
    uses system-dns-servers-config;
  }

  container state {
    config false;
    uses system-dns-servers-config;
    uses system-dns-servers-state;
  }
}
```

### 2. 型の定義

#### typedef
カスタム型の定義

```yang
typedef timezone-name-type {
  type string;
  description
    "A time zone name as used by the Time Zone Database,
     sometimes referred to as the 'Olson Database'.";
  reference
    "BCP 175: Procedures for Maintaining the Time Zone Database";
}
```

#### identity
アイデンティティの定義（列挙型の拡張可能な形式）

```yang
identity NTP_AUTH_TYPE {
  description
    "Base identity for encryption schemes supported for NTP
    authentication keys";
}

identity NTP_AUTH_MD5 {
  base NTP_AUTH_TYPE;
  description "MD5 encryption method";
}
```

### 3. 再利用可能な定義

#### grouping
データ構造の再利用可能な定義

```yang
grouping system-global-config {
  description "system-wide configuration parameters";

  leaf hostname {
    type oc-inet:domain-name;
    description
      "The hostname of the device -- should be a single domain
      label, without the domain.";
  }

  leaf domain-name {
    type oc-inet:domain-name;
    description
      "Specifies the domain name used to form fully qualified name
      for unqualified hostnames.";
  }

  leaf login-banner {
    type string;
    description
      "The console login message displayed before the login prompt,
      i.e., before a user logs into the system.";
  }
}
```

#### uses
groupingを実際に使用する

```yang
container config {
  description "Configuration data for system clock";
  uses system-clock-config;
}
```

### 4. 参照と制約

#### leafref
他のleafへの参照を行うための型。データの整合性を保証し、存在しない値を参照することを防ぎます。

**基本的な考え方:**
- leafrefは「他のleafの値を参照する」ポインタのような働き
- 参照先の値が存在しない場合はバリデーションエラーになる
- XPath形式のpathで参照先を指定

**シンプルな例:**

```yang
container user {
  container config {
    leaf username {
      type string;
      description "ユーザー名";
    }

    leaf primary-group {
      type string;
      description "プライマリグループ名";
    }
  }

  // このleafは上記のprimary-groupの値を参照
  leaf group-reference {
    type leafref {
      path "../config/primary-group";  // 相対パスで参照
    }
    description "グループへの参照 - 必ず存在するグループ名のみ指定可能";
  }
}
```

**リストでの使用例（最も一般的なパターン）:**

```yang
// DNSサーバーのリスト定義
list server {
  key "address";  // addressがこのリストのキー

  // このleafがリストのキーとして機能
  // leafrefで下のconfig/addressを参照することで、
  // キーと実際の設定値が常に同期される
  leaf address {
    type leafref {
      path "../config/address";
    }
    description "DNSサーバーのアドレス（キー）";
  }

  container config {
    leaf address {
      type oc-inet:ip-address;  // 実際のデータ型はここで定義
      description "DNSサーバーのIPアドレス（実体）";
    }

    leaf port {
      type oc-inet:port-number;
      default 53;
    }
  }
}
```

**実際のデータ例:**

上記のモデルから生成されるXMLデータ：
```xml
<server>
  <address>8.8.8.8</address>  <!-- leafrefで参照されるキー -->
  <config>
    <address>8.8.8.8</address>  <!-- 実体の値 -->
    <port>53</port>
  </config>
</server>
```

この構造により、キー（`server/address`）と実際の設定値（`server/config/address`）が常に一致することが保証されます。

**絶対パスと相対パスの例:**

```yang
container network {
  container interfaces {
    list interface {
      key "name";
      leaf name {
        type string;
      }
    }
  }

  container routes {
    list route {
      key "destination";
      leaf destination {
        type string;
      }

      // 相対パスの例
      leaf interface-ref {
        type leafref {
          path "../../interfaces/interface/name";
        }
        description "このルートで使用するインターフェース名";
      }

      // 絶対パスの例（/から始まる）
      leaf interface-ref-absolute {
        type leafref {
          path "/network/interfaces/interface/name";
        }
        description "絶対パスでの参照";
      }
    }
  }
}
```

**leafrefのメリット:**
1. **参照整合性**: 存在しない値を参照できない（外部キー制約のような働き）
2. **自動補完**: CLIやGUIツールで有効な値の候補を提示できる
3. **削除保護**: 参照されているデータは削除できない
4. **型の安全性**: 参照先の型が自動的に適用される

#### when
条件付きでノードを有効化

```yang
leaf ipv4-address {
  when "../address-family = 'ipv4'";
  type inet:ipv4-address;
}
```

#### must
制約条件の定義

```yang
leaf max-connections {
  type uint32;
  must ". <= ../total-connections" {
    error-message "Max connections cannot exceed total connections";
  }
}
```

### 5. 設定と状態の分離

#### config文
- `config true`: 設定データ（デフォルト）
- `config false`: 状態データ（読み取り専用）

```yang
container config {
  // config true が暗黙的に適用される
  leaf hostname {
    type string;
  }
}

container state {
  config false;  // 読み取り専用の状態データ

  leaf current-datetime {
    type oc-yang:date-and-time;
    description "The current system date and time.";
  }

  leaf boot-time {
    type oc-types:timeticks64;
    units "nanoseconds";
    description
      "This timestamp indicates the time that the system was last
      restarted.";
  }
}
```

---

## データモデリングの例

### DNSリゾルバの設定モデル

openconfig-system.yangから抜粋したDNS設定の例：

```yang
grouping system-dns-config {
  description "DNS / resolver related configuration data";

  leaf-list search {
    type oc-inet:domain-name;
    ordered-by user;
    description
      "An ordered list of domains to search when resolving
      a host name.";
  }
}

grouping system-dns-servers-config {
  description "Configuration data for DNS resolvers";

  leaf address {
    type oc-inet:ip-address;
    description
      "The address of the DNS server, can be either IPv4 or IPv6.";
  }

  leaf port {
    type oc-inet:port-number;
    default 53;
    description "The port number of the DNS server.";
  }
}

container dns {
  description "Enclosing container for DNS resolver data";

  container config {
    description "Configuration data for the DNS resolver";
    uses system-dns-config;
  }

  container state {
    config false;
    description "Operational state data for the DNS resolver";
    uses system-dns-config;
    uses system-dns-state;
  }

  container servers {
    description "Enclosing container for DNS resolver list";

    list server {
      key "address";
      ordered-by user;
      description "List of the DNS servers";

      leaf address {
        type leafref {
          path "../config/address";
        }
        description "References the configured address of the DNS server";
      }

      container config {
        uses system-dns-servers-config;
      }

      container state {
        config false;
        uses system-dns-servers-config;
        uses system-dns-servers-state;
      }
    }
  }
}
```

この構造により、以下のようなXMLやJSONデータを生成できます：

#### XML例
```xml
<dns>
  <config>
    <search>example.com</search>
    <search>test.example.com</search>
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

#### JSON例
```json
{
  "dns": {
    "config": {
      "search": ["example.com", "test.example.com"]
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

---

## OpenConfig systemモジュールの解説

### モジュールの目的

openconfig-system.yangは、ネットワークデバイスのシステム全体に関わるサービスや機能を管理するためのモデルです。

### 主な機能領域

1. **システムグローバル設定**
   - ホスト名
   - ドメイン名
   - ログインバナー
   - MOTDバナー

2. **クロック設定**
   - タイムゾーン
   - 現在時刻
   - ブート時刻

3. **DNS設定**
   - 検索ドメイン
   - DNSサーバーリスト
   - 静的ホストエントリ

4. **NTP設定**
   - NTPサーバー設定
   - 認証設定
   - 同期状態

5. **その他のサブモジュール**
   - AAA（認証・認可・アカウンティング）
   - ロギング
   - システム管理
   - ターミナル
   - プロセス監視
   - アラーム

### OpenConfigのデザインパターン

#### 1. Config/State分離パターン

OpenConfigでは、すべてのコンテナで設定(config)と状態(state)を明確に分離します：

```yang
container <name> {
  container config {
    // 設定可能なパラメータ
    uses <name>-config;
  }

  container state {
    config false;
    // 設定パラメータ + 状態データ
    uses <name>-config;
    uses <name>-state;
  }
}
```

**利点**:
- 設定と状態の明確な区別
- APIでの操作が直感的
- 状態データの取得が容易

#### 2. Groupingによる構造化

データ構造をgroupingで定義し、再利用します：

```yang
grouping system-ntp-server-config {
  description "Configuration data for NTP servers";

  leaf address {
    type oc-inet:host;
    description "The address or hostname of the NTP server.";
  }

  leaf port {
    type oc-inet:port-number;
    default 123;
    description "The port number of the NTP server.";
  }

  leaf association-type {
    type enumeration {
      enum SERVER { description "Use client association mode."; }
      enum PEER { description "Use symmetric active association mode."; }
      enum POOL { description "Use client association mode with DNS."; }
    }
    default SERVER;
    description "The desired association type for this NTP server.";
  }
}
```

#### 3. Leafrefによるキー参照

OpenConfigパターンでは、リストのキーは常にleafrefで参照します。これにより、キーと実際の設定値の整合性が保証されます。

**標準パターン:**

```yang
list server {
  key "address";  // ① キーの宣言

  // ② キー用のleaf（leafrefで実体を参照）
  leaf address {
    type leafref {
      path "../config/address";  // config/addressを参照
    }
    description "References the configured address";
  }

  // ③ 設定コンテナ
  container config {
    leaf address {
      type oc-inet:ip-address;  // ④ 実体の型定義
      description "実際のIPアドレス値";
    }

    leaf port {
      type oc-inet:port-number;
      default 53;
    }
  }

  // ⑤ 状態コンテナ
  container state {
    config false;
    // 設定値 + 状態値を含む
    leaf address {
      type oc-inet:ip-address;
    }
    leaf port {
      type oc-inet:port-number;
    }
    // 状態専用のデータ
    leaf last-query-time {
      type uint64;
      description "最後のクエリ時刻";
    }
  }
}
```

**データフローの説明:**

1. ユーザーが設定: `server/config/address = "8.8.8.8"`
2. YANGバリデータが自動的に: `server/address = "8.8.8.8"` をセット
3. この値がリストのキーとして機能

**完全なデータ例（JSON）:**

```json
{
  "servers": {
    "server": [
      {
        "address": "8.8.8.8",           // キー（leafref）
        "config": {
          "address": "8.8.8.8",         // 実体
          "port": 53
        },
        "state": {
          "address": "8.8.8.8",         // 状態（実行時の値）
          "port": 53,
          "last-query-time": 1234567890
        }
      },
      {
        "address": "8.8.4.4",
        "config": {
          "address": "8.8.4.4",
          "port": 53
        },
        "state": {
          "address": "8.8.4.4",
          "port": 53,
          "last-query-time": 1234567999
        }
      }
    ]
  }
}
```

**なぜこのパターンを使うのか？**

1. **一貫性**: キーと設定値が常に一致
2. **API設計**: RESTful APIで `/servers/server[address=8.8.8.8]/config` のようなパスが使える
3. **柔軟性**: キーは読み取り専用だが、config/addressは変更可能（変更時はキーも自動更新）

**従来のパターンとの比較:**

```yang
// 従来パターン（leafref不使用）
list server {
  key "address";
  leaf address {
    type oc-inet:ip-address;  // 直接型を指定
  }
  leaf port {
    type oc-inet:port-number;
  }
}

// OpenConfigパターン（leafref使用）
list server {
  key "address";
  leaf address {
    type leafref {
      path "../config/address";  // 参照で整合性保証
    }
  }
  container config {
    leaf address {
      type oc-inet:ip-address;
    }
    leaf port {
      type oc-inet:port-number;
    }
  }
}
```

### NTP設定の完全な例

```yang
grouping system-ntp-server-config {
  leaf address {
    type oc-inet:host;
    description "The address or hostname of the NTP server.";
  }

  leaf port {
    type oc-inet:port-number;
    default 123;
  }

  leaf version {
    type uint8 {
      range 1..4;
    }
    default 4;
    description "Version number to put in outgoing NTP packets";
  }

  leaf iburst {
    type boolean;
    default false;
    description "Indicates whether this server should enable burst synchronization";
  }

  leaf prefer {
    type boolean;
    default false;
    description "Indicates whether this server should be preferred";
  }
}

grouping system-ntp-server-state {
  leaf stratum {
    type uint8;
    description "Indicates the level of the server in the NTP hierarchy";
  }

  leaf root-delay {
    type uint32;
    units "milliseconds";
    description "The round-trip delay to the server";
  }

  leaf offset {
    type uint64;
    units "milliseconds";
    description "Estimate of the current time offset from the peer";
  }

  leaf poll-interval {
    type uint32;
    units "seconds";
    description "Polling interval of the peer";
  }
}
```

### リビジョン管理

YANGモジュールは、revisionステートメントでバージョン管理されます：

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

revision "2018-11-21" {
  description "Add OpenConfig module metadata extensions.";
  reference "0.6.1";
}
```

---

## まとめ

### YANGの利点

1. **標準化されたモデリング言語**: IETFで標準化
2. **強力な型システム**: データの整合性を保証
3. **再利用性**: grouping、typedef、identityで効率的なモデリング
4. **拡張性**: augment、deviationで柔軟な拡張
5. **ツールサポート**: pyang、yangson、libyang等の豊富なツール
6. **プロトコル非依存**: NETCONF、RESTCONF、gNMI等で利用可能

### OpenConfigの特徴

1. **ベンダー中立**: 複数のベンダーで共通利用可能
2. **運用重視**: 実際の運用ニーズに基づいた設計
3. **一貫したパターン**: config/state分離、grouping活用
4. **コミュニティ駆動**: オープンな開発プロセス

### 学習リソース

- **RFC 6020**: YANG 1.0仕様
- **RFC 7950**: YANG 1.1仕様
- **OpenConfig GitHub**: https://github.com/openconfig/public
- **pyang**: YANGバリデーションツール
- **YANG Explorer**: Webベースのブラウザ

### 次のステップ

1. pygツールでYANGモジュールをバリデーション
2. YANGからドキュメント（HTML、tree）を生成
3. NETCONF/RESTCONFでYANGモデルを実装
4. カスタムYANGモジュールの作成
5. augmentやdeviationで既存モデルを拡張
