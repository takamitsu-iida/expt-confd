.PHONY: usage init clean start start_confd start_subscriber stop cli cli-c validate-xml

usage:
	@echo "make init    ディレクトリと設定ファイルを準備します"
	@echo "make all     実行できるようにビルドします"
	@echo "make clean   中間ファイルを削除します"
	@echo "make start   confdとPythonのエージェントを起動します"
	@echo "make stop    confdとエージェントを停止します"
	@echo "make cli     CONFDコマンドラインインターフェイス（Jスタイル）を起動します"
	@echo "make cli-c   CONFDコマンドラインインターフェイス（Cスタイル）を起動します"

######################################################################

# ベースとなるYANGファイル名（拡張子なし）
YANG_BASE = example

# example.yangからexample.fxsを生成し、さらにexample_ns.pyを生成する
TARGET = bin/$(YANG_BASE)_ns.py

# Python アクションデーモンスクリプトのパス
SUBSCRIBER = bin/action_daemon.py

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

# YANGファイルのリスト（必要に応じて調整）
YANG_FILES = $(wildcard $(YANG_DIR)/*.yang)
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang,$(LOADPATH_DIR)/%.fxs,$(YANG_FILES))

# CLI 定義ファイル
CLI_DIR = $(PWD)/cli
CLI_J = $(CLI_DIR)/commands-j.cli
CLI_C = $(CLI_DIR)/commands-c.cli
CLI_SPECS = $(LOADPATH_DIR)/commands-j.ccl $(LOADPATH_DIR)/commands-c.ccl

######################################################################

# FXSファイルの作成ルール
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $< $(YANGPATH)

# CLIスペック(.ccl)の作成ルール
$(LOADPATH_DIR)/%.ccl: $(CLI_DIR)/%.cli
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $<

# Python名前空間ファイルを生成するルール
$(BIN_DIR)/%_ns.py: $(LOADPATH_DIR)/%.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@touch $@

######################################################################


# デフォルトターゲット
all: $(TARGET) $(CLI_SPECS)
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

# お掃除
clean:
	@rm -f $(LOADPATH_DIR)/*.fxs $(LOADPATH_DIR)/*.ccl $(BIN_DIR)/*_ns.py || true
	@rm -f log/* || true

# 起動
start:  stop start_confd start_subscriber

# ConfD 起動
start_confd: stop all
	confd -c confd.conf $(CONFD_FLAGS)

# Pythonサブスクライバ起動
start_subscriber:
	python $(SUBSCRIBER) --start

# ConfD 停止
stop:
	confd --stop || true
	# pkill -f $(SUBSCRIBER) || true
	python $(SUBSCRIBER) --stop || true

# ConfD CLI 起動
cli:
	$(CONFD_DIR)/bin/confd_cli -J --user=admin --groups=admin --interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin --interactive || echo Exit

# XML形式のコンフィグファイルの検証
XML_CONFIG_FILE ?= config.xml
validate-xml:
	yanglint -p ./yang -p "$(CONFD_DIR)/src/confd/yang" -t config example.yang "$(XML_CONFIG_FILE)"