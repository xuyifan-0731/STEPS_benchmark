#!/bin/bash

cd test

# 创建目标目录，如果不存在
mkdir -p target

# 查找所有大于1KB的文件，并移动到目标目录下
find . -type f -size +1k -exec mv {} target \;