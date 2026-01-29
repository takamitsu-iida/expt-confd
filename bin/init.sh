#!/bin/bash

for dir in confd-cdb confd-state log loadpath; do
  mkdir -p "$dir"
  touch "$dir/.gitkeep"
done

cp ../confd.conf.example ./confd.conf

# ssh-keydirのシンボリックリンクを作成
rm -rf ssh-keydir
ln -s $CONFD_DIR/etc/confd/ssh ssh-keydir

cp $CONFD_DIR/var/confd/cdb/*.xml ./confd-cdb/
