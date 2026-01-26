# ConfDを試す

<br>

ConfDのベーシック版は無料で使えますので、実際に動かしてみます。

日常使っているWSLのUbuntuは汚したくないので、CML上にUbuntuを立てて、そこで試してみます。

<br><br>

## ダウンロード

Cisco社のSoftware Downloadのページからダウンロードできます。

ログインが必要です。

![構成](/assets/download_confd.png)

<br><br>

リリースノートとか、そういうのは見当たりません。

x86_64の方のzipファイルをダウンロードします。

今回ダウンロードしたのは　`confd-basic-8.0.20.linux.x86_64.signed.zip`　です。

これをHyper-Vホストになっている母艦の `C:\inetpub\wwwroot` においておきます。

<br><br>

## 環境構築

Hyper-VホストのWSL(Ubuntu)で作業を行います。

このリポジトリをクローンします。

```bash
git clone https://github.com/takamitsu-iida/expt-confd.git
```

ディレクトリを移動します。

```bash
cd expt-confd
```

初期セットアップスクリプトを実行して環境を整えます。

```bash
bin/setup.sh
```

<br><br>

## Ubuntuのセットアップ

CML上にラボを作成して、Ubuntuを作成します。

ラボの構成はこのようにします。

![構成](/assets/lab.png)

<br><br>

ラボの作成は手作業だと大変なのでスクリプトで作成します。

Makefileの場所に移動します。

```bash
cd cml
```

makeコマンドで作成します。

```bash
iida@s400win:~/git/expt-confd/cml$ make
create                         ラボをCML上に作成する
start                          ラボを開始する
stop                           ラボを停止する
delete                         ラボを削除する
terminal                       ルータのコンソールに接続する
```

作成　`make create`

```bash
iida@s400win:~/git/expt-confd/cml$ make create
../bin/cml_create_confd_host.py --create --title "ConfD Lab" --description "ConfD lab for testing"
2026-01-26 11:30:17,310 - INFO - Lab 'ConfD Lab' created successfully
2026-01-26 11:30:17,310 - INFO - id: d05b8d5c-76e2-4795-bc1f-109fd5eb9a42
```

起動　`make start`

```bash
iida@s400win:~/git/expt-confd/cml$ make start
../bin/cml_create_confd_host.py --start --title "ConfD Lab"
2026-01-26 11:30:39,154 - INFO - Starting lab 'ConfD Lab'
2026-01-26 11:30:59,218 - INFO - Lab 'ConfD Lab' started
```

UbuntuのコンソールをWindows Terminalで開く　`make terminal`

```bash
iida@s400win:~/git/expt-confd/cml$ make terminal
../bin/open_terminal.sh 7000
```

<br><br>

## ConfDのインストール

試行錯誤の結果、分かったこと。

- 古いOpenSSL（バージョン 1.1）が必要
- gccが必要
- makeが必要
- インストール時にディレクトリを指定する必要がある

スクリプトで作成したUbuntuはこれらを反映した状態で起動します。

ConfDのインストール先は /usr/lib/confd としています。

<br><br>

ここからはUbuntuのコンソールで作業します。

作業はroot特権で行います。

```bash
sudo -s -E
```

ConfDをインストールする先を `/usr/lib/confd` とします。

このディレクトリを作ります（Ubuntuの起動時にすでに作られているので念の為）。

```bash
mkdir -p /usr/lib/confd
```

インストール作業を行うフォルダを/tmpに作成します。

```bash
mkdir /tmp/confd
cd /tmp/confd
```

Hyper-Vの母艦からConfDのファイルをダウンロードします。

> [!NOTE]
>
> Hyper-Vの母艦はWindows Defenderファイアウォールで防御されているかもしれません。
>
> その場合は一時的にファイアウォールを停止します。

<br>

```bash
wget http://192.168.0.198/confd-basic-8.0.20.linux.x86_64.signed.zip
```

unzipコマンドで解凍します。

```bash
unzip confd-basic-8.0.20.linux.x86_64.signed.zip
```

実行例。

```bash
root@confd:/tmp/confd# unzip confd-basic-8.0.20.linux.x86_64.signed.zip
Archive:  confd-basic-8.0.20.linux.x86_64.signed.zip
  inflating: confd-basic-8.0.20.libconfd.tar.gz
  inflating: confd-basic-8.0.20.examples.tar.gz
  inflating: confd-basic-8.0.20.linux.x86_64.signed.bin
  inflating: confd-basic-8.0.20.doc.tar.gz
```

confd-basic-8.0.20.linux.x86_64.signed.bin を実行できるようにモードを変更します。

```bash
chmod a+x *.bin
```

実行します。

```bash
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.signed.bin
Unpacking...
Verifying signature...
CA chain innerspace chosen based on finding 'innerspace' string in eecert
Using cert chain 'innerspace' (crcam2.cer and innerspace.cer)
Retrieving rootCA certificate from https://www.cisco.com/security/pki/certs/crcam2.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/crcam2.cer
Using downloaded rootCA cert /tmp/tmpx7zzmn0e/crcam2.cer
Retrieving subCA certificate from https://www.cisco.com/security/pki/certs/innerspace.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/innerspace.cer
Using downloaded subCA cert /tmp/tmpx7zzmn0e/innerspace.cer
Successfully verified root, subca and end-entity certificate chain.
Successfully fetched a public key from tailf.cer
Successfully verified the signature of confd-basic-8.0.20.linux.x86_64.installer.bin using tailf.cer
```

ファイルがさらに解凍され　`confd-basic-8.0.20.linux.x86_64.installer.bin`　というファイルが生成されます。

これがインストーラです。このbinファイルにも実行権限を付けます。

```bash
chmod a+x .bin
```

インストール先のディレクトリを指定して実行します。

```bash
./confd-basic-8.0.20.linux.x86_64.installer.bin /usr/lib/confd
```

実行例。

```bash
root@confd:/tmp/confd# ./confd-basic-8.0.20.linux.x86_64.installer.bin /usr/lib/confd
INFO  Unpacked confd-basic-8.0.20 in /usr/lib/confd
INFO  Found and unpacked corresponding DOCUMENTATION_PACKAGE
INFO  Found and unpacked corresponding EXAMPLE_PACKAGE
INFO  Generating default SSH hostkey (this may take some time)
INFO  SSH hostkey generated
INFO  Generating self-signed certificates for HTTPS
INFO  Environment set-up generated in /usr/lib/confd/confdrc
INFO  ConfD installation script finished
root@confd:/tmp/confd#
```

インストールできました。

/usr/lib/confd/confdrc を反映するために一度ログアウトします。

もう一度ログインして、ルート特権を取ります。

```bash
sudo -s -E
```

コンパイラ `confdc` がPATHに存在するか、確認します。

```bash
cisco@confd:~$ which confdc
/usr/lib/confd/bin/confdc

cisco@confd:~$ confdc --version
confd-8.0.20
```

<br>

サンプルディレクトリへ移動します。

```bash
cd /usr/lib/confd/examples.confd/intro/python/1-2-3-start-query-model
```

YANGモデルをコンパイルします。

```bash
make all
```

実行例。

```bash
root@confd:/usr/lib/confd/examples.confd/intro/python/1-2-3-start-query-model# make all
/usr/lib/confd/bin/confdc --fail-on-warnings  -c -o dhcpd.fxs  dhcpd.yang
/usr/lib/confd/bin/confdc -c commands-j.cli
/usr/lib/confd/bin/confdc -c commands-c.cli
mkdir -p ./confd-cdb
cp /usr/lib/confd/var/confd/cdb/aaa_init.xml ./confd-cdb
ln -s /usr/lib/confd/etc/confd/ssh ssh-keydir
/usr/lib/confd/bin/confdc --emit-python dhcpd_ns.py dhcpd.fxs
Python build complete
```

ConfDデーモンを起動します。

フォアグラウンドで起動されますので、バックグランドに回します。

```bash
make start &
```

CLIで確認します。

```bash
confd_cli -u admin
```

CLIが起動したら、'show running-config' など、Ciscoライクなコマンドを試してみて、動作することを確認します。


動作確認ができたらバックグランドに回した make start を停止します。

```bash
kill %%
```



```bash
confd -c confd.conf --addloadpath $CONFD_DIR/src/confd/standard
```

停止

```bash
confd --stop || true
```

```bash
pkill -f subscribe.py || true
```

<!--

ArcOSの場合、/usr/share/arcos/uiにfxsファイルが多数格納されてます。
これがload_dirだと思われます。



-->