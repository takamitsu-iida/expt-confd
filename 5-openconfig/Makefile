.PHONY: usage init clean start start_confd stop cli cli-c

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
# OpenConfig の代表的なトップレベルモジュールを指定
YANG_BASE = openconfig-system

# Python モジュール名用に、YANG モジュール名の '-' を '_' に変換
YANG_BASE_PY = $(subst -,_,$(YANG_BASE))

# openconfig-system.yang から openconfig_system_ns.py を生成する
TARGET = bin/$(YANG_BASE_PY)_ns.py

######################################################################

# confdのインストールディレクトリ
CONFD_DIR ?= $(HOME)/confd

# YANGファイルを置いている場所
YANG_DIR = $(PWD)/yang

# FXSファイルを出力するディレクトリ
LOADPATH_DIR = $(PWD)/loadpath

# binディレクトリ
BIN_DIR = $(PWD)/bin

# CLI 定義ファイル
CLI_DIR = $(PWD)/cli
CLI_J = $(CLI_DIR)/commands-j.cli
CLI_C = $(CLI_DIR)/commands-c.cli
CLI_SPECS = $(LOADPATH_DIR)/commands-j.ccl $(LOADPATH_DIR)/commands-c.ccl

# FXSファイルを生成するときの追加の検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/yang --yangpath $(YANG_DIR)

# confd実行時の引数
CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd

# YANGファイルのリスト（必要に応じて調整）
# submodule はコンパイル対象から外し、"module" 宣言を持つトップレベルモジュールのみを対象とする
OPENCONFIG_YANG_FILES = $(wildcard $(YANG_DIR)/*.yang)
OPENCONFIG_MODULES = $(shell grep -l '^module ' $(OPENCONFIG_YANG_FILES))
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang,$(LOADPATH_DIR)/%.fxs,$(OPENCONFIG_MODULES))

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
# すべての YANG から FXS を生成し、代表モジュールの Python 名前空間も生成
all: $(FXS_FILES) $(TARGET) $(CLI_SPECS)
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
start:  stop start_confd

# ConfD 起動
start_confd: stop all
	confd -c confd.conf $(CONFD_FLAGS)

# ConfD 停止
stop:
	confd --stop || true

# ConfD CLI 起動
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin --interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin --interactive || echo Exit
