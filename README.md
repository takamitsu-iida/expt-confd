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

ラボの作成は手作業だと大変なので、Pythonで作ります。

```bash
(.venv) iida@s400win:~/git/expt-confd$ bin/cml_create_confd_host.py
usage: cml_create_confd_host.py [-h] [--create] [--delete] [--stop] [--start] [--title TITLE]
                                [--description DESCRIPTION]

create confd host lab

options:
  -h, --help            show this help message and exit
  --create              Create lab
  --delete              Delete lab
  --stop                Stop lab
  --start               Start lab
  --title TITLE         Lab title (default: confd_host_lab)
  --description DESCRIPTION
                        Lab description (default: ConfD host lab created by cml_create_confd_host.py)
```

作成。

```bash
(.venv) iida@s400win:~/git/expt-confd$ bin/cml_create_confd_host.py --create
2026-01-22 14:06:39,144 - INFO - Lab 'confd_host_lab' created successfully
2026-01-22 14:06:39,144 - INFO - id: 534d0247-7119-44d5-81eb-b4b3842cca40
```

起動。

```bash
(.venv) iida@s400win:~/git/expt-confd$ bin/cml_create_confd_host.py --start
2026-01-22 14:06:46,934 - INFO - Starting lab 'confd_host_lab'
2026-01-22 14:07:06,997 - INFO - Lab 'confd_host_lab' started
```

## ConfDのインストール

Hyper-Vの母艦からダウンロードします。

`wget http://192.168.0.198/confd-basic-8.0.20.linux.x86_64.signed.zip`


unzipコマンドで解凍します。

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

README.signatureにかかれている通りに実行します。

```bash
python3 cisco_x509_verify_release.py3 \
-e tailf.cer \
-i confd-basic-8.0.20.linux.x86_64.installer.bin \
-s confd-basic-8.0.20.linux.x86_64.installer.bin.signature \
-v dgst --algo sha512
```

実行例。大丈夫そうです。

```bash
root@confd:~# python3 cisco_x509_verify_release.py3 \
-e tailf.cer \
-i confd-basic-8.0.20.linux.x86_64.installer.bin \
-s confd-basic-8.0.20.linux.x86_64.installer.bin.signature \
-v dgst --algo sha512
CA chain innerspace chosen based on finding 'innerspace' string in eecert
Using cert chain 'innerspace' (crcam2.cer and innerspace.cer)
Retrieving rootCA certificate from https://www.cisco.com/security/pki/certs/crcam2.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/crcam2.cer
Using downloaded rootCA cert /tmp/tmpnqa5eula/crcam2.cer
Retrieving subCA certificate from https://www.cisco.com/security/pki/certs/innerspace.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/innerspace.cer
Using downloaded subCA cert /tmp/tmpnqa5eula/innerspace.cer
Successfully verified root, subca and end-entity certificate chain.
Successfully fetched a public key from tailf.cer
Successfully verified the signature of confd-basic-8.0.20.linux.x86_64.installer.bin using tailf.cer
```

binファイルがインストーラのようです。実行できるようにモードを変えます。

```bash
cisco@confd:~$ chmod a+x *.bin
```

実行します。

```bash
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.installer.bin
Usage: ./confd-basic-8.0.20.linux.x86_64.installer.bin <install-dir>

This is the ConfD installation script. It will install ConfD in the
given directory in a way suitable for development with ConfD. See
the ConfD User Manual for information about how to install ConfD for
deployment on a host system.
root@confd:~#
```

ディレクトリを指定しないといけないようです。

```bash
mkdir $HOME/confd
```

再度実行してみます。

```bash
root@confd:~# ./confd-basic-8.0.20.linux.x86_64.installer.bin $HOME/confd
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
```

ぐぬぬ。

libcrypto.so.1.1をインストールします。
