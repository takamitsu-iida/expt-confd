.DEFAULT_GOAL := help
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# 作成するラボタイトル
LAB_TITLE = ConfD Lab

# 作成するラボのデスクリプション
DESCRIPTION = ConfD lab for testing

SCRIPT = ../bin/cml_create_confd_host.py
TERMINAL = ../bin/open_terminal.sh

create: ## ラボをCML上に作成する
	$(SCRIPT) --create --title "$(LAB_TITLE)" --description "$(DESCRIPTION)"

start: ## ラボを開始する
	$(SCRIPT) --start --title "$(LAB_TITLE)"

stop: ## ラボを停止する
	$(SCRIPT) --stop --title "$(LAB_TITLE)"

delete: ## ラボを削除する
	$(SCRIPT) --delete --title "$(LAB_TITLE)"

terminal: ## ルータのコンソールに接続する
	$(TERMINAL) 7000