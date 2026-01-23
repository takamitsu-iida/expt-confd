# ConfDを試す

<br>

ConfDのベーシック版は無料で使えますので、試してみます。

<br><br>

## ダウンロード

Cisco社のSoftware Downloadのページからダウンロードできます。

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

Hyper-Vの母艦からダウンロードします。

Hyper-Vの母艦はWindows Defenderファイアウォールで防御されているかもしれません。
その場合は一時的にファイアウォールを停止します。

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

ルート特権を取得します。

```bash
sudo -s -E
```

binファイルがインストーラのようです。実行できるようにモードを変えます。

```bash
cisco@confd:~$ chmod a+x *.bin
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

ファイルがさらに解凍されて　`confd-basic-8.0.20.linux.x86_64.installer.bin`　というファイルが生成されます。

これに実行権限を付けて実行します。

```bash
root@confd:~# chmod a+x confd-basic-8.0.20.linux.x86_64.installer.bin
root@confd:~#
root@confd:~#
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.installer.bin
Usage: ./confd-basic-8.0.20.linux.x86_64.installer.bin <install-dir>

This is the ConfD installation script. It will install ConfD in the
given directory in a way suitable for development with ConfD. See
the ConfD User Manual for information about how to install ConfD for
deployment on a host system.
```

おっと。

インストールする先のディレクトリを指定しないいけないようです。

ここではconfdというディレクトリを作成して、それを指定してみます。

```bash
mkdir $HOME/confd
```

再度実行してみます。

`./confd-basic-8.0.20.linux.x86_64.installer.bin $HOME/confd`

実行例。

```bash
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.installer.bin confd
INFO  Unpacked confd-basic-8.0.20 in /home/cisco/confd
INFO  Found and unpacked corresponding DOCUMENTATION_PACKAGE
INFO  Found and unpacked corresponding EXAMPLE_PACKAGE
INFO  Generating default SSH hostkey (this may take some time)
INFO  SSH hostkey generated
INFO  Generating self-signed certificates for HTTPS


REQUIRED LIBRARIES NOT FOUND

ConfD requires a version of the libcrypto.so library that could not
be found on your system:

        libcrypto.so.1.1 => not found

The missing library must be installed using exactly the name shown above
to succesfully run ConfD. If you have the correct library version
installed using another name, this problem may be solved by creating a
symbolic link to the installed library with the name ConfD requires.

The correct version of the crypto library may be downloaded and
installed using the standard mechanisms for your system. You may also
download the required OpenSSL package directly from the OpenSSL site
(www.openssl.org). Any patch level (indicated by a final letter in the
OpenSSL version number) within the required OpenSSL major version may be
used.

You are welcome to ask your Cisco support contact for assistance.

USING A DIFFERENT VERSION OF OpenSSL WITH ConfD

For ConfD, you may use a different version of OpenSSL than the one which
the distribution has been built with. For information on doing this,
please consult the section "Using a different version of OpenSSL" in the
"Advanced Topics" chapter of the ConfD User Guide.

INFO  Environment set-up generated in /home/cisco/confd/confdrc
INFO  ConfD installation script finished
root@confd:~#
```

ぐぬぬ。

libcrypto.so.1.1が必要と言っています。

OpenSSLのページからlibssl1.1を個別にダウンロードしてインストールします。

> [!NOTE]
>
> 古いバージョンはここからダウンロードします
>
> https://nz2.archive.ubuntu.com/ubuntu/pool/main/o/openssl/

<br>

```bash
wget https://nz2.archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb

dpkg -i libssl1.1_1.1.1f-1ubuntu2_amd64.deb
```

ディレクトリを削除して、もう一度最初からやり直します。

```bash
rm -rf confd
mkdir confd
./confd-basic-8.0.20.linux.x86_64.installer.bin confd
```

実行例

```bash
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.installer.bin confd
INFO  Unpacked confd-basic-8.0.20 in /home/cisco/confd
INFO  Found and unpacked corresponding DOCUMENTATION_PACKAGE
INFO  Found and unpacked corresponding EXAMPLE_PACKAGE
INFO  Generating default SSH hostkey (this may take some time)
INFO  SSH hostkey generated
INFO  Generating self-signed certificates for HTTPS
INFO  Environment set-up generated in /home/cisco/confd/confdrc
INFO  ConfD installation script finished
```

うまくいきました。
