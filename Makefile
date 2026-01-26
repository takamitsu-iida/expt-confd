# 変数の定義
CONFD_DIR ?= /usr/lib/confd

YANG_DIR = yang

LOADPATH_DIR = ./loadpath
CONF_FILE = ./confd.conf


YANG_SOURCES = $(wildcard $(YANG_DIR)/*.yang)
FXS_FILES = $(patsubst $(YANG_DIR)/%.yang, $(LOADPATH_DIR)/%.fxs, $(YANG_SOURCES))

# デフォルトターゲット
all: $(FXS_FILES)

# コンパイルルール
$(LOADPATH_DIR)/%.fxs: $(YANG_DIR)/%.yang
	mkdir -p $(LOADPATH_DIR)
	confdc -c $< -o $@ --yangpath $(CONFD_DIR)/src/confd/standard
	confdc --emit-python bin/server_status_ns.py server-status.fxs

clean:
	rm -f $(LOADPATH_DIR)/*.fxs

start:
	confd -c $(CONF_FILE) --addloadpath $(CONFD_DIR)/src/confd/standard

stop:
	confd --stop || true