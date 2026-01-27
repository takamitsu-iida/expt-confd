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
他のleafへの参照

```yang
leaf address {
  type leafref {
    path "../config/address";
  }
  description "References the configured address of the DNS server";
}
```

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

リストのキーはleafrefで参照します：

```yang
list server {
  key "address";

  leaf address {
    type leafref {
      path "../config/address";
    }
    description "References the configured address";
  }

  container config {
    leaf address {
      type oc-inet:ip-address;
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
