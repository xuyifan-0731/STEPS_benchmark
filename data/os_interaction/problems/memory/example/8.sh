cd test
while [ "$(du -s . | awk '{print $1}')" -gt 17000 ]
do
  largest_file=$(ls -l | awk '{print $5,$9}' | sort -rn | head -n 1 | awk '{print $2}')
  rm ${largest_file}
  echo "Deleted ${largest_file}"
done
echo "Total size is now $(du -sh .)"