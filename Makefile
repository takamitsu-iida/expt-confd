# 変数の定義
CONFD_DIR ?= /usr/lib/confd
YANG_DIR   = yang
LOADPATH_DIR = ./loadpath
BIN_DIR    = ./bin
CONF_FILE  = ./confd.conf

# ソースファイルのリスト作成
YANG_SOURCES = $(wildcard $(YANG_DIR)/*.yang)
# .fxs ファイルのリスト
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang, $(LOADPATH_DIR)/%.fxs, $(YANG_SOURCES))
# Python 共通定義（_ns.py）ファイルのリスト
NS_FILES  = $(patsubst $(LOADPATH_DIR)/%.fxs, $(BIN_DIR)/%_ns.py, $(FXS_FILES))

# 検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/standard --yangpath $(YANG_DIR)

# デフォルトターゲット
all: $(FXS_FILES) $(NS_FILES)

# 1. YANG から FXS をコンパイルするルール
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang
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

# ConfD 起動
start: all
	confd -c $(CONF_FILE) --addloadpath $(CONFD_DIR)/src/confd/standard --addloadpath $(LOADPATH_DIR)

# ConfD 停止
stop:
	confd --stop || true

root@confd:~/expt-confd# make
make: *** No rule to make target 'loadpath/network-device.fxs', needed by 'all'.  Stop.
