#!/bin/bash

set -e  # エラー時に即座に終了
set -u  # 未定義変数の使用時にエラー

# CONFD_DIRの存在確認
if [ -z "${CONFD_DIR:-}" ]; then
  echo "Error: CONFD_DIR environment variable is not set" >&2
  exit 1
fi

if [ ! -d "$CONFD_DIR" ]; then
  echo "Error: CONFD_DIR ($CONFD_DIR) does not exist" >&2
  exit 1
fi

# ディレクトリの作成
for dir in confd-cdb confd-state log tmp loadpath; do
  mkdir -p "$dir"
  touch "$dir/.gitkeep"
done

# confd.confのコピー
if [ ! -f ../confd.conf.example ]; then
  echo "Error: ../confd.conf.example not found" >&2
  exit 1
fi
cp ../confd.conf.example ./confd.conf

# ssh-keydirのシンボリックリンクを作成
rm -rf ssh-keydir
if [ ! -d "$CONFD_DIR/etc/confd/ssh" ]; then
  echo "Error: $CONFD_DIR/etc/confd/ssh does not exist" >&2
  exit 1
fi
ln -s "$CONFD_DIR/etc/confd/ssh" ssh-keydir

# CDBファイルのコピー(aaa_init.xml)
if [ -d "$CONFD_DIR/var/confd/cdb" ] && [ -n "$(ls -A "$CONFD_DIR/var/confd/cdb"/*.xml 2>/dev/null)" ]; then
  cp "$CONFD_DIR/var/confd/cdb"/*.xml ./confd-cdb/
else
  echo "Warning: No XML files found in $CONFD_DIR/var/confd/cdb" >&2
fi

echo "Initialization completed successfully"
