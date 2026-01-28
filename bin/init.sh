#!/bin/bash

for dir in confd-cdb confd-state ssh-keydir log loadpath; do
  mkdir -p "$dir"
  touch "$dir/.gitkeep"
done

cp ../confd.conf.example ./confd.conf
