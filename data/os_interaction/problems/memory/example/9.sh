cd test

total_size=$(find . -type f -printf '%s\n' | awk '{sum += $1} END {print sum}')

# 获取当前目录下所有文件的数量
file_count=$(find . -type f | wc -l)

# 计算平均文件大小
avg_size=$(expr $total_size / $file_count)

echo $avg_size