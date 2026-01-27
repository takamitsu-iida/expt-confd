# 変数の定義
CONFD_DIR ?= /usr/lib/confd
YANG_DIR   = yang
LOADPATH_DIR = ./loadpath
BIN_DIR    = ./bin
CONF_FILE  = ./confd.conf
STATE_DIR = ./confd-state

# ソースファイルのリスト作成
# サブモジュール（submodule）を除外し、メインモジュール（module）のみを対象にする
YANG_SOURCES = $(shell grep -l "^module " $(YANG_DIR)/*.yang 2>/dev/null)

# .fxs ファイルのリスト
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang, $(LOADPATH_DIR)/%.fxs, $(YANG_SOURCES))

# Python 共通定義（_ns.py）ファイルのリスト
NS_FILES  = $(patsubst $(LOADPATH_DIR)/%.fxs, $(BIN_DIR)/%_ns.py, $(FXS_FILES))

# 検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/standard --yangpath $(YANG_DIR)

# デフォルトターゲット
all: $(FXS_FILES) $(NS_FILES)

# 1. YANG から FXS をコンパイルするルール
# サブモジュールは自動的にインクルードされる
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang $(YANG_DIR)/*.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $< $(YANGPATH)

# 2. FXS から Python 用名前空間ファイルを生成するルール
# ファイル名は example_ns.py のようになるように設定
$(BIN_DIR)/%_ns.py: $(LOADPATH_DIR)/%.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<

# お掃除
clean:
	rm -f $(LOADPATH_DIR)/*.fxs $(BIN_DIR)/*_ns.py
	rm -rf $(STATE_DIR)/*

# ConfD 起動
start: all
	confd -c $(CONF_FILE) --addloadpath $(CONFD_DIR)/src/confd/standard --addloadpath $(LOADPATH_DIR)

# ConfD 停止
stop:
	confd --stop || true

# デバッグ用: どのファイルが対象か確認
.PHONY: all clean start stop debug
debug:
	@echo "YANG_SOURCES = $(YANG_SOURCES)"
	@echo "FXS_FILES = $(FXS_FILES)"
	@echo "NS_FILES = $(NS_FILES)"