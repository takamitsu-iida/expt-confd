# 6-dnsmasq: ConfD で dnsmasq DHCP を操作する例

## ゴール

- dnsmasq の DHCP サーバ設定を YANG モデル (dnsmasq-dhcp.yang) で表現
- ConfD の CDB を通じて設定し、その内容から dnsmasq.conf を自動生成
- dnsmasq のリースファイルから DHCP リース状態を読み取り、`show dhcp leases` 風に閲覧

## ディレクトリ構成

- yang/dnsmasq-dhcp.yang: dnsmasq DHCP 設定 + リース状態の YANG モデル
- loadpath/: confdc が生成する FXS
- bin/dnsmasq_dhcp_ns.py: confdc --emit-python で生成される namespace モジュール
- bin/dnsmasq_config_sync.py: CDB 変更から dnsmasq.conf を生成するデーモン
- bin/dhcp_lease_provider.py: dnsmasq.leases から DHCP リース状態を提供するデーモン

## 使い方 (概要)

```sh
cd 6-dnsmasq
make init      # 必要なディレクトリを作成
make all       # YANG から FXS / Python ns を生成
make start     # ConfD + 2つの Python デーモン起動
make cli       # ConfD CLI にログイン
```

### dnsmasq.conf の出力先

- デフォルト: `./tmp/dnsmasq.conf`
- 実機の dnsmasq と連携したい場合は、環境変数 `DNSMASQ_CONF_PATH` を設定してから
  `make start` することで `/etc/dnsmasq.conf` などに変更可能です。

```sh
export DNSMASQ_CONF_PATH=/etc/dnsmasq.conf
```

### DHCP リースファイルの参照先

- デフォルト: `/var/lib/misc/dnsmasq.leases`
- 環境によって異なる場合は、環境変数 `DNSMASQ_LEASES_PATH` で上書きできます。

```sh
export DNSMASQ_LEASES_PATH=/path/to/dnsmasq.leases
```

## 補足

- callpoint/CLI の詳細定義は YANG (または別途 *.cli ファイル) で調整が必要ですが、
  基本的なデーモンスケルトンと YANG モデルはこのディレクトリで完結しています。
