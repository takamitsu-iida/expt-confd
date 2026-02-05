usage:
	@echo "make init          ディレクトリと設定ファイルを準備します"
	@echo "make all           実行できるようにビルドします"
	@echo "make clean         中間ファイルを削除します"
	@echo "make start         confdとPythonのエージェントを起動します"
	@echo "make start_confd   confdを起動します"
	@echo "make stop          confdとエージェントを停止します"
	@echo "make cli           CONFDコマンドラインインターフェイス（Jスタイル）を起動します"
	@echo "make cli-c         CONFDコマンドラインインターフェイス（Cスタイル）を起動します"

######################################################################

# ベースとなるYANGファイル名（拡張子なし）
YANG_BASE = dnsmasq-dhcp

# dnsmasq-dhcp.yangからdnsmasq-dhcp.fxsを生成し、さらにdnsmasq_dhcp_ns.pyを生成する
TARGET = bin/$(YANG_BASE:_-=%)_ns.py

# Pythonスクリプトのパス
CONFIG_SYNC = bin/dnsmasq_config_sync.py
LEASE_PROVIDER = bin/dhcp_lease_provider.py

######################################################################

# confdのインストールディレクトリ
CONFD_DIR ?= $(HOME)/confd

# YANGファイルを置いている場所
YANG_DIR = $(PWD)/yang

# FXSファイルを出力するディレクトリ
LOADPATH_DIR = $(PWD)/loadpath

# binディレクトリ
BIN_DIR = $(PWD)/bin

# FXSファイルを生成するときの追加の検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/yang --yangpath $(YANG_DIR)

# confd実行時の引数
CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd

# YANGファイルのリスト
YANG_FILES = $(wildcard $(YANG_DIR)/*.yang)
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang,$(LOADPATH_DIR)/%.fxs,$(YANG_FILES))

# CLI 定義ファイル
CLI_J = commands-j.cli

######################################################################

# FXSファイルの作成ルール
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $< $(YANGPATH)

# Python名前空間ファイルを生成するルール
$(BIN_DIR)/%_ns.py: $(LOADPATH_DIR)/%.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@touch $@

######################################################################

# デフォルトターゲット
all: $(TARGET)
	@echo "Build complete"

# TARGETを生成する明示的なルール
$(TARGET): $(LOADPATH_DIR)/$(YANG_BASE).fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@rm -f $(BIN_DIR)/__init__.py || true
	@touch $@

# 初期化（ディレクトリ作成、設定ファイルコピー）
init:
	@../bin/init.sh || true
	@if [ -f $(CLI_J) ]; then \
		confdc -c $(CLI_J); \
	fi

# お掃除
clean:
	@rm -f $(LOADPATH_DIR)/*.fxs $(BIN_DIR)/*_ns.py || true
	@rm -f log/* || true

# 起動
start:  stop start_confd start_agents

# ConfD 起動
start_confd: stop all
	confd -c confd.conf $(CONFD_FLAGS)

# Pythonエージェント起動
start_agents:
	python $(CONFIG_SYNC) --start
	python $(LEASE_PROVIDER) --start

# ConfD 停止
stop:
	confd --stop || true
	python $(CONFIG_SYNC) --stop || true
	python $(LEASE_PROVIDER) --stop || true

# ConfD CLI 起動
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin --interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin --interactive || echo Exit
