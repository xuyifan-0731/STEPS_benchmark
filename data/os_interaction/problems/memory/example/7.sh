#!/bin/bash
cd test

# 获取原始文件的大小
size_before=$(du -b 1.txt | awk '{print $1}')

# 将文件压缩到 tar 归档文件中
tar -cvf 1.tar 1.txt >/dev/null 2>&1

# 删除原始文件
rm 1.txt

# 获取压缩后的文件大小
size_after=$(du -b 1.tar | awk '{print $1}')

# 计算节省的磁盘空间
space_saved=$((size_before - size_after))

echo $space_saved
