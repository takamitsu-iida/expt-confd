#!/bin/bash

# open_terminal.sh のラッパースクリプト
# telnet:// プロトコルハンドラーから呼び出されます
#
# 使い方:
# bin/open_terminal_wrapper.sh "telnet://cml:5001"
# bin/open_terminal_wrapper.sh "telnet://192.168.122.212:5001"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 引数から telnet:// URL を受け取る
URL="$1"

if [ -z "$URL" ]; then
    echo "Error: URL argument is required"
    echo "Usage: $0 <telnet://host:port>"
    exit 1
fi

# URLからポート番号を抽出
# telnet://cml:5001 -> 5001
# telnet://192.168.122.212:5001 -> 5001
PORT=$(echo "$URL" | sed -E 's#^telnet://[^:]+:([0-9]+).*$#\1#')

if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Error: Could not extract port number from URL: $URL"
    exit 1
fi

# open_terminal.sh を実行
"${SCRIPT_DIR}/open_terminal.sh" "$PORT"
