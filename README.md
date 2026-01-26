# ConfDを試す

<br>

ConfDのベーシック版は無料で使えますので、実際に動かしてみます。

日常使っているWSLのUbuntuは汚したくないので、CML上にUbuntuを立てて、そこで試してみます。

<br><br>

## ダウンロード

Cisco社のSoftware Downloadのページからダウンロードできます。

ログインが必要です。

![構成](/assets/download_confd.png)

リリースノートとか、そういうのは見当たりません。

zipファイルをダウンロードします。

今回は　`confd-basic-8.0.20.linux.x86_64.signed.zip`　をダウンロードしました。

これをHyper-Vホストになっている母艦のC:\inetpub\wwwrootにおいておきます。

<br><br>

## Ubuntuのセットアップ

CML上にラボを作成して、Ubuntuを作成します。

![構成](/assets/lab.png)

<br>

ラボの作成は手作業だと大変なのでスクリプトで作成します。

```bash
(.venv) iida@s400win:~/git/expt-confd$ make
create                         ラボをCML上に作成する
start                          ラボを開始する
stop                           ラボを停止する
delete                         ラボを削除する
terminal                       ルータのコンソールに接続する
```

作成　`make create`

```bash
(.venv) iida@s400win:~/git/expt-confd$ make create
bin/cml_create_confd_host.py --create --title "ConfD Lab" --description "ConfD lab for testing"
2026-01-23 11:25:41,793 - INFO - Lab 'ConfD Lab' created successfully
2026-01-23 11:25:41,793 - INFO - id: d3202949-96da-4b88-9fdd-75a844126aa2
```

起動　`make start`

```bash
(.venv) iida@s400win:~/git/expt-confd$ make start
bin/cml_create_confd_host.py --start --title "ConfD Lab"
2026-01-23 11:25:49,025 - INFO - Starting lab 'ConfD Lab'
2026-01-23 11:26:09,085 - INFO - Lab 'ConfD Lab' started
```

Windows TerminalでUbuntuのコンソールを開く　`make terminal`

```bash
(.venv) iida@s400win:~/git/expt-confd$ make terminal
bin/open_terminal.sh 7000
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

作業はroot特権で行います。

```bash
sudo -s -E
```

ConfDをインストールする先を `/usr/lib/confd` とします。

このディレクトリをあらかじめ作っておきます。

```bash
mkdir /usr/lib/confd
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

`wget http://192.168.0.198/confd-basic-8.0.20.linux.x86_64.signed.zip`

unzipコマンドで解凍します。

`unzip confd-basic-8.0.20.linux.x86_64.signed.zip`

実行例。

```bash
cisco@confd:~$ unzip confd-basic-8.0.20.linux.x86_64.signed.zip
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

実行例。

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

これがインストーラです。このファイルにも実行権限を付けます。

```bash
chmod a+x .bin
```

インストール先のディレクトリを指定して実行します。

```bash
./confd-basic-8.0.20.linux.x86_64.installer.bin /usr/lib/confd
```

実行例。

```bash
```



<!--

ArcOSの場合、/usr/share/arcos/uiにfxsファイルが多数格納されてます。
これがload_dirだと思われます。



-->