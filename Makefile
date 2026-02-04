# 変数の定義
CONFD_DIR ?= /usr/lib/confd
YANG_DIR = ./yang
LOADPATH_DIR = ./loadpath
BIN_DIR = ./bin
LOG_DIR = ./log
CONFIG_FILE = ./confd.conf
OPENCONFIG_DIR = ./openconfig

# 検索パス
YANGPATH = --yangpath $(CONFD_DIR)/src/confd/yang --yangpath $(YANG_DIR) --yangpath $(OPENCONFIG_DIR)

# openconfigディレクトリ内の全YANGファイルを検索
OPENCONFIG_YANG_FILES = $(wildcard $(OPENCONFIG_DIR)/*.yang)

# サブモジュール（submodule）を除外し、トップレベルモジュールのみを抽出
OPENCONFIG_MODULES = $(shell grep -l '^module ' $(OPENCONFIG_YANG_FILES))
OPENCONFIG_FXS_FILES = $(patsubst $(OPENCONFIG_DIR)/%.yang,$(LOADPATH_DIR)/%.fxs,$(OPENCONFIG_MODULES))

# 生成するファイルを明示的に指定
FXS_FILES = $(LOADPATH_DIR)/example.fxs $(LOADPATH_DIR)/network-device.fxs $(OPENCONFIG_FXS_FILES)
NS_FILES  = $(BIN_DIR)/example_ns.py $(BIN_DIR)/network_device_ns.py

usage:
	@echo "make all     Build all example files for Python"
	@echo "make clean   Remove all built and intermediary files"
	@echo "make start   Start CONFD daemon and python example agent"
	@echo "make stop    Stop any CONFD daemon and example agent"
	@echo "make cli     Start the CONFD Command Line Interface, J-style"
	@echo "make cli-c   Start the CONFD Command Line Interface, C-style"


# %_ns.py: %.fxs
# 	$(CONFDC) $(CONFDC_PYTHON_FLAGS) --emit-python $*_ns.py $*.fxs

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

# openconfigディレクトリ内の各YANGファイルをコンパイル
$(LOADPATH_DIR)/%.fxs: $(OPENCONFIG_DIR)/%.yang
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
	rm -rf $(LOG_DIR)/*

# ConfD 起動
start: stop all
	confd -c $(CONFIG_FILE)

# ConfD 停止
stop:
	confd --stop || true

# ConfD CLI 起動
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin --interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin --interactive || echo Exit