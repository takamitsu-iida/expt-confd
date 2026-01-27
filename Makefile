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

# サブモジュールの依存関係を自動検出する関数
# 各メインモジュールがインクルードするサブモジュールを探す
define get-submodules
$(shell grep -h "^[[:space:]]*include" $(1) 2>/dev/null | \
        sed 's/include[[:space:]]*\([^;]*\);.*/\1/' | \
        xargs -I {} echo "$(YANG_DIR)/{}.yang")
endef

# 1. YANG から FXS をコンパイルするルール
# 各モジュールは、それ自身とインクルードするサブモジュールに依存する
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $< $(YANGPATH)

# 明示的な依存関係を追加（example.yangの例）
$(LOADPATH_DIR)/example.fxs: $(YANG_DIR)/example.yang $(YANG_DIR)/example-config.yang $(YANG_DIR)/example-state.yang

# network-deviceにサブモジュールがある場合は同様に追加
# $(LOADPATH_DIR)/network-device.fxs: $(YANG_DIR)/network-device.yang $(YANG_DIR)/network-device-xxx.yang

# 2. FXS から Python 用名前空間ファイルを生成するルール
$(BIN_DIR)/%_ns.py: $(LOADPATH_DIR)/%.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@touch $@  # タイムスタンプを明示的に更新

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
