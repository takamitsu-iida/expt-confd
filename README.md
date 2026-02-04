# ConfDを試す

<br>

tail-f社は2014年にCisco社に買収されました。

tail-fのNCS(Network Control System)はCisco NSO(Network Services Orchestrator)として継続しています。

tail-fのConfD(Pro版)は既にEnd of Lifeとなっていますが、機能を制限したベーシック版は2026年1月現在もDevNetのサイトで公開されています（8.0.x系が最後のリリースと言われています）。

ベーシック版ConfDが入手可能なうちに、実際に動かしてみます。

<br><br>

コンフィグの作成やバリデーションといった作業は日常使っているWSL(Ubuntu)で実行できるようにしておくと便利です。

ConfDを使ってなんちゃってアプライアンスを仕立てる、みたいなことはCML上にLinuxを立てたり、コンテナを作成した方がいいでしょう。

<br><br>

## ダウンロード

Cisco社のSoftware Downloadのページからダウンロードできます。

ログインが必要です。

![構成](/assets/download_confd.png)

<br><br>

リリースノートとか、そういうのは見当たりません。

x86_64の方のzipファイルをダウンロードします。

今回ダウンロードしたのは　`confd-basic-8.0.20.linux.x86_64.signed.zip`　です。

CML上のUbuntuにインストールするのであれば、
これをHyper-Vホストになっている母艦の `C:\inetpub\wwwroot` においておきます。

<br><br>

## ConfDの動作に必要な環境

試行錯誤した結果、以下が判明しています。

- xmllintが必要（libxml2-utilsに含まれる）
- gccが必要
- makeが必要
- 古いOpenSSL 1.1が必要（ダウンロードしてインストール）
- Pythonモジュール paramiko が必要（pipでインストール）

他にも入れておいたほうがよいものがあります。概ね以下のようなものが入っていれば大丈夫です。

- jq
- yq
- libxml2-utils  # for xmllint
- curl
- wget
- git
- zip
- unzip
- make
- gcc  # for ConfD build
- python3-venv
- direnv

<br><br>

## WSL(Ubuntu)にインストール

普段使っているWSL(Ubuntu)にインストールすると、いつでもConfDを使えて便利です。

前述の環境を整えた上でConfDをインストールします。

不要になったらいつでも消せるように、インストール先は `~/confd` とします。

1. `~/tmp`にダウンロードしたzipファイルを置きます。

2. unzipで解凍します。

3. binファイルに実行権限を付与して実行すると、インストーラのbinファイルが追加されます。

4. インストーラのbinファイルに実行権限を付与して実行します。

```bash
$ mkdir -p ~/confd

$ mkdir -p ~/tmp

$ mkdir -p ~/tmp/confd

$ cd ~/tmp/confd

$ mv ~/confd-basic-8.0.20.linux.x86_64.signed.zip .

$ unzip confd-basic-8.0.20.linux.x86_64.signed.zip
Archive:  confd-basic-8.0.20.linux.x86_64.signed.zip
  inflating: confd-basic-8.0.20.libconfd.tar.gz
  inflating: confd-basic-8.0.20.examples.tar.gz
  inflating: confd-basic-8.0.20.linux.x86_64.signed.bin
  inflating: confd-basic-8.0.20.doc.tar.gz

$ chmod a+x *.bin

$ ./confd-basic-8.0.20.linux.x86_64.signed.bin
Unpacking...
Verifying signature...
CA chain innerspace chosen based on finding 'innerspace' string in eecert
Using cert chain 'innerspace' (crcam2.cer and innerspace.cer)
Retrieving rootCA certificate from https://www.cisco.com/security/pki/certs/crcam2.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/crcam2.cer
Using downloaded rootCA cert /tmp/tmptwcame4s/crcam2.cer
Retrieving subCA certificate from https://www.cisco.com/security/pki/certs/innerspace.cer ...
Success in downloading https://www.cisco.com/security/pki/certs/innerspace.cer
Using downloaded subCA cert /tmp/tmptwcame4s/innerspace.cer
Successfully verified root, subca and end-entity certificate chain.
Successfully fetched a public key from tailf.cer
Successfully verified the signature of confd-basic-8.0.20.linux.x86_64.installer.bin using tailf.cer

$ chmod a+x *.bin

$ ./confd-basic-8.0.20.linux.x86_64.installer.bin ~/confd
INFO  Unpacked confd-basic-8.0.20 in /home/iida/confd
INFO  Found and unpacked corresponding DOCUMENTATION_PACKAGE
INFO  Found and unpacked corresponding EXAMPLE_PACKAGE
INFO  Generating default SSH hostkey (this may take some time)
INFO  SSH hostkey generated
INFO  Generating self-signed certificates for HTTPS
INFO  Environment set-up generated in /home/iida/confd/confdrc
INFO  ConfD installation script finished
```

これで `~/confd` にインストールされました。

作業ディレクトリ `~/tmp/confd` は消して大丈夫です。

`~/confd/confdrc` に環境設定用のファイルがありますので、それを読み込むように、`~/.bashrc`を変更します。

```bash
cat - << 'EOS' >> ~/.bashrc

#
if [ -f ~/confd/confdrc ]; then
    source ~/confd/confdrc
fi
EOS
```

一度シェルを抜けてWSL(Ubuntu)を開き直します。

コンパイラ `confdc` がPATHの中に存在するか、確認します。

```bash
cisco@confd:~$ which confdc
/usr/lib/confd/bin/confdc

cisco@confd:~$ confdc --version
confd-8.0.20
```

<br><br>

## CMLでの環境構築

CML上にラボを立てて、そこで実験する場合です。

CMLが稼働するHyper-Vの母艦となっているWindowsのWSL(Ubuntu)で作業を行います。

母艦のWSL(Ubuntu)にて、このリポジトリをクローンします。

```bash
git clone https://github.com/takamitsu-iida/expt-confd.git
```

ディレクトリを移動します。

```bash
cd expt-confd
```

Python環境を整えるために、初期セットアップスクリプトを実行します。

```bash
bin/setup.sh
```

<br>

### ラボのセットアップ

CML上にラボを作成して、Ubuntuを作成します。

ラボ構成はこのようにします。

![構成](/assets/lab.png)

<br><br>

ラボの作成は手作業だと大変なのでスクリプトで作成します。

cmlディレクトリにMakefileを準備してありますので、移動します。

```bash
cd cml
```

makeコマンドでラボを作成します。

```bash
$ make
create                         ラボをCML上に作成する
start                          ラボを開始する
stop                           ラボを停止する
delete                         ラボを削除する
terminal                       ルータのコンソールに接続する
```

作成　`make create`

```bash
$ make create
../bin/cml_create_confd_host.py --create --title "ConfD Lab" --description "ConfD lab for testing"
2026-01-26 11:30:17,310 - INFO - Lab 'ConfD Lab' created successfully
2026-01-26 11:30:17,310 - INFO - id: d05b8d5c-76e2-4795-bc1f-109fd5eb9a42
```

起動　`make start`

```bash
$ make start
../bin/cml_create_confd_host.py --start --title "ConfD Lab"
2026-01-26 11:30:39,154 - INFO - Starting lab 'ConfD Lab'
2026-01-26 11:30:59,218 - INFO - Lab 'ConfD Lab' started
```

UbuntuのコンソールをWindows Terminalで開く　`make terminal`

```bash
$ make terminal
../bin/open_terminal.sh 7000
```

<br>

### ConfDのインストール

ここからはラボ内のUbuntuのコンソールで作業します。

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

作業用ディレクトリ /tmp/confd は不要ですので、削除します。

```bash
rm -rf /tmp/confd
```

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

<br><br><br>

## 動作確認

ConfDをインストールしたディレクトリ内にサンプルが提供されていますので、それが動くか確認します。

```bash
cd $CONFD_DIR
cd examples.confd/intro/python/1-2-3-start-query-model
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

ConfDデーモンおよびPythonスクリプトを起動します。

フォアグラウンドで起動されますので、バックグランドに回します。

```bash
make start &
```

CLIで確認します。

```bash
confd_cli -u admin
```

もしくは、

```bash
make cli
```

CLIが起動したら、'show running-config' など、Ciscoライクなコマンドを試してみて、動作することを確認します。

動作確認ができたらバックグランドに回した make start を停止します。

```bash
make stop
```

dhcpd_conf.pyというスクリプトも同時に走っていますが、
もしこのプロセスが残ってしまっていたら、手作業で停止します。

```bash
pkill -f dhcpd_conf.py
```

<br><br>

## confdの設定

confdは `confd -c 設定ファイル名` で起動します。

設定ファイルはXML形式です。

<br>

### ArcOSにおけるConfDの設定

`cat /usr/etc/confd/confd.conf`

```xml
<!-- -*- nxml -*- -->
<confdConfig xmlns="http://tail-f.com/ns/confd_cfg/1.0">
  <loadPath>
    <dir>/usr/etc/confd</dir>
    <dir>/usr/etc/confd/snmp</dir>
    <dir>/usr/share/arcos/ui</dir>
  </loadPath>
  <runtimeReconfiguration>namespace</runtimeReconfiguration>
  <cryptHash>
    <algorithm>sha-512</algorithm>
  </cryptHash>
  <scripts>
    <dir>/usr/share/arcos/confd-scripts</dir>
  </scripts>
  <stateDir>/var/confd/state</stateDir>
  <cdb>
    <enabled>true</enabled>
    <dbDir>/var/confd/cdb</dbDir>
    <clientTimeout>PT1800S</clientTimeout>
    <operational>
      <enabled>true</enabled>
    </operational>
  </cdb>
  <datastores>
    <startup>
      <enabled>false</enabled>
    </startup>
    <candidate>
      <enabled>true</enabled>
      <implementation>confd</implementation>
      <storage>auto</storage>
      <filename>/var/confd/candidate/candidate.db</filename>
      <confirmedCommit>
        <revertByCommit>true</revertByCommit>
      </confirmedCommit>
    </candidate>
    <running>
      <access>writable-through-candidate</access>
    </running>
  </datastores>
  <enableAttributes>true</enableAttributes>
  <enableInactive>false</enableInactive>
  <rollback>
    <enabled>true</enabled>
    <directory>/var/confd/rollback</directory>
    <historySize>50</historySize>
    <type>delta</type>
  </rollback>
  <aaa>
    <sshServerKeyDir>/etc/ssh</sshServerKeyDir>
    <aaaBridge>
      <enabled>false</enabled>
      <file>/usr/etc/confd/aaa.conf</file>
    </aaaBridge>
  </aaa>
  <cli>
    <ssh>
      <enabled>false</enabled>
    </ssh>
    <nmda>
      <showOperationalState>true</showOperationalState>
    </nmda>
  </cli>
  <netconf>
    <capabilities>
      <startup>
        <enabled>false</enabled>
      </startup>
      <candidate>
        <enabled>true</enabled>
      </candidate>
      <confirmed-commit>
        <enabled>true</enabled>
      </confirmed-commit>
      <writable-running>
        <enabled>false</enabled>
      </writable-running>
      <rollback-on-error>
        <enabled>true</enabled>
      </rollback-on-error>
      <url>
        <enabled>true</enabled>
        <file>
          <enabled>true</enabled>
          <rootDir>/var/confd/state</rootDir>
        </file>
        <ftp>
          <enabled>true</enabled>
        </ftp>
      </url>
      <xpath>
        <enabled>true</enabled>
      </xpath>
      <notification>
        <enabled>true</enabled>
        <interleave>
          <enabled>false</enabled>
        </interleave>
      </notification>
    </capabilities>
  </netconf>
  <notifications>
    <eventStreams>
      <stream>
        <name>interface</name>
        <description>notifications stream</description>
        <replaySupport>true</replaySupport>
        <builtinReplayStore>
          <!-- enableBuiltinReplayStore -->
          <dir>./</dir>
          <maxSize>S1M</maxSize>
          <maxFiles>5</maxFiles>
        </builtinReplayStore>
      </stream>
    </eventStreams>
  </notifications>
  <ignoreBindErrors>
    <enabled>true</enabled>
  </ignoreBindErrors>
  <logs>
    <syslogConfig>
      <facility>daemon</facility>
    </syslogConfig>
    <confdLog>
      <enabled>true</enabled>
      <file>
        <enabled>true</enabled>
        <name>/var/log/arcos/confd/confd.log</name>
      </file>
      <syslog>
        <enabled>false</enabled>
      </syslog>
    </confdLog>
    <developerLog>
      <enabled>true</enabled>
      <file>
        <enabled>true</enabled>
        <name>/var/log/arcos/confd/devel.log</name>
      </file>
      <syslog>
        <enabled>false</enabled>
      </syslog>
    </developerLog>
    <auditLog>
      <enabled>true</enabled>
      <file>
        <enabled>true</enabled>
        <name>/var/log/arcos/confd/audit.log</name>
      </file>
      <syslog>
        <enabled>false</enabled>
      </syslog>
    </auditLog>
  </logs>
</confdConfig>
```

<br>

### 注意事項

- aaa_init.xmlが必要

コンフィグのデータベースの位置には aaa_init.xml が必要です。
このファイルがないと、設定できなくなります。

confd.confで以下のように設定した場合は `./confd-cdb/aaa_init.xml` が必要です。

```xml
  <cdb>
    <enabled>true</enabled>
    <dbDir>./confd-cdb</dbDir>
```

aaa_init.xmlは自分で作成するよりも、ConfDをインストール場所からコピーするのが手っ取り早いです。

<br>

- ssh-keydirが必要

これもConfDをインストールした先にあるものを流用します。

コピーしてもいいですし、シンボリックリンクを張ってもいいです。

```bash
ln -s $CONFD_DIR/etc/confd/ssh ssh-keydir
```
