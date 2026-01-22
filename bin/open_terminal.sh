#!/bin/bash

# 使い方:
#
# 引数にPATtyで接続したい装置のポート番号を列挙して実行します。
#
# bin/open_terminal.sh 5011 5012 5013 5014

# CML="192.168.122.212"
CML="cml"

#
# 以下、変更不要
#

SCRIPT_NAME=$(basename "$0")

# Windows Terminalで開くアクションプロファイル名(PowerShellを開く)
PS="Windows PowerShell"

# wsl内にある/usr/bin/telnetを起動する
TELNET="wsl -e /usr/bin/telnet"

# 引数でポート番号を受け取る
PORT_LIST=("$@")

# 実行するのはこんな感じのコマンド
# wt.exe -p 'Windows PowerShell' wsl -e /usr/bin/telnet 192.168.122.212 5001

if [ ${#PORT_LIST[@]} -eq 0 ]; then
    echo "Usage: $0 <PORT1> [PORT2 ...]"
    exit 1
fi

# 引数がすべて数字かチェック
for port in "${PORT_LIST[@]}"; do
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        echo "Error: All arguments must be numeric port numbers."
        exit 1
    fi
done

# 引数が1個だけなら、そのまま開く
if [ ${#PORT_LIST[@]} -eq 1 ]; then
    wt.exe --title ${SCRIPT_NAME} -p ${PS} ${TELNET} ${CML} ${PORT_LIST[0]}
    exit 0
fi

# 引数が2個なら、垂直分割で2ペインにする
if [ ${#PORT_LIST[@]} -eq 2 ]; then
    wt.exe --title ${SCRIPT_NAME} -p ${PS} ${TELNET} ${CML} ${PORT_LIST[0]} \
      \; split-pane -V --size 0.5 -p ${PS} ${TELNET} ${CML} ${PORT_LIST[1]} \
      \; move-focus first
    exit 0
fi

#
# 以下、3個以上のペインを開く場合
#

# 必要なペインの総数を取得
N=${#PORT_LIST[@]}

# 左右の列のペイン数を計算
LEFT_COUNT=$(( (N + 1) / 2 ))  # 左側のペイン数 (切り上げ)
RIGHT_COUNT=$(( N / 2 ))       # 右側のペイン数 (切り捨て)

LEFT_LIST=()
for ((i=0; i<LEFT_COUNT; i++)); do
    LEFT_LIST[$i]="${PORT_LIST[$i]}"
done

RIGHT_LIST=()
for ((i=0; i<RIGHT_COUNT; i++)); do
    RIGHT_LIST[$i]="${PORT_LIST[$((LEFT_COUNT + i))]}"
done

# 最初のターミナルを開いて
COMMAND_STRING="wt.exe --title ${SCRIPT_NAME} -p ${PS} ${TELNET} ${CML} ${LEFT_LIST[0]}"

# 垂直分割で右側にペインを開く
COMMAND_STRING="${COMMAND_STRING} \; split-pane -V --size 0.5 -p ${PS} ${TELNET} ${CML} ${RIGHT_LIST[0]}"

# 左のペインにフォーカスを移動
COMMAND_STRING="${COMMAND_STRING} \; move-focus left"

# 左側で2番目以降のペインを水平 (上下) に均等分割
for ((i=1; i<$LEFT_COUNT; i++)); do
    # 現在の残りのスペースに対して、新しいペインが必要な割合を計算
    REMAINING_PANES=$(( LEFT_COUNT - i + 1 ))
    SIZE_ARG=$(echo "scale=3; 1 / $REMAINING_PANES" | bc)

    # 水平分割で下にペインを作成
    COMMAND_STRING="${COMMAND_STRING} \; split-pane -H --size ${SIZE_ARG} -p ${PS} ${TELNET} ${CML} ${LEFT_LIST[$i]}"

    # 分割後、フォーカスを新しく作成されたペインから上（次に分割すべきペイン）に移動
    if [ "$i" -lt "$((LEFT_COUNT-1))" ]; then
        COMMAND_STRING="${COMMAND_STRING} \; move-focus up"
    fi
done

# 右のペインにフォーカスを移動
COMMAND_STRING="${COMMAND_STRING} \; move-focus right"

# 右側で2番目以降のペインを水平 (上下) に均等分割
RIGHT_START_INDEX=$LEFT_COUNT
for ((i=1; i<$RIGHT_COUNT; i++)); do
    # 現在の残りのスペースに対して、新しいペインが必要な割合を計算
    REMAINING_PANES=$(( RIGHT_COUNT - i + 1 ))
    SIZE_ARG=$(echo "scale=3; 1 / $REMAINING_PANES" | bc)

    # 水平分割のコマンドを追加
    COMMAND_STRING="${COMMAND_STRING} \; split-pane -H --size ${SIZE_ARG} -p ${PS} ${TELNET} ${CML} ${RIGHT_LIST[$i]}"

    # 分割後、フォーカスを新しく作成されたペインから上（次に分割すべきペイン）に移動
    if [ "$i" -lt "$((RIGHT_COUNT-1))" ]; then
        COMMAND_STRING="${COMMAND_STRING} \; move-focus up"
    fi
done

# すべてのペイン作成後、左上のペインにフォーカスを移動
COMMAND_STRING="${COMMAND_STRING} \; move-focus first"

# デバッグ用
# echo "実行コマンド: ${COMMAND_STRING}"

# evalを使用して、セミコロンが正しくwt.exeの区切り文字として解釈されるように実行
eval "${COMMAND_STRING}"