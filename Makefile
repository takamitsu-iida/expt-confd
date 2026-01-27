# 変数の定義
CONFD_DIR ?= /usr/lib/confd
YANG_DIR = ./yang
LOADPATH_DIR = ./loadpath
BIN_DIR = ./bin
LOG_DIR = ./log
CONFIG_FILE = ./confd.conf
STATE_DIR = ./confd-state

# 検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/yang --yangpath $(YANG_DIR)

# 生成するファイルを明示的に指定
# FXS_FILES = $(LOADPATH_DIR)/example.fxs $(LOADPATH_DIR)/network-device.fxs
FXS_FILES = $(LOADPATH_DIR)/example.fxs

# NS_FILES  = $(BIN_DIR)/example_ns.py $(BIN_DIR)/network_device_ns.py
NS_FILES  = $(BIN_DIR)/example_ns.py

# デフォルトターゲット
all: $(FXS_FILES) $(NS_FILES)

# example.yang → example.fxs (サブモジュール含む)
$(LOADPATH_DIR)/example.fxs: $(YANG_DIR)/example.yang #   $(YANG_DIR)/example-config.yang $(YANG_DIR)/example-state.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $(YANG_DIR)/example.yang $(YANGPATH)

# network-device.yang → network-device.fxs (サブモジュールなし)
$(LOADPATH_DIR)/network-device.fxs: $(YANG_DIR)/network-device.yang
	@mkdir -p $(LOADPATH_DIR)
	confdc -c -o $@ $< $(YANGPATH)

# example.fxs → example_ns.py
$(BIN_DIR)/example_ns.py: $(LOADPATH_DIR)/example.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@touch $@

# network-device.fxs → network_device_ns.py
$(BIN_DIR)/network_device_ns.py: $(LOADPATH_DIR)/network-device.fxs
	@mkdir -p $(BIN_DIR)
	confdc --emit-python $@ $<
	@touch $@

# お掃除
clean:
	rm -f $(LOADPATH_DIR)/*.fxs $(BIN_DIR)/*_ns.py
	rm -rf $(STATE_DIR)/*
	rm -rf $(LOG_DIR)/*

# ConfD 起動
start: all
	# confd -c $(CONFIG_FILE)
	confd -c $(CONFIG_FILE) --addloadpath $(LOADPATH_DIR)

# ConfD 停止
stop:
	confd --stop || true

# デバッグ用: どのファイルが対象か確認
.PHONY: all clean start stop debug
debug:
	@echo "FXS_FILES = $(FXS_FILES)"
	@echo "NS_FILES = $(NS_FILES)"
