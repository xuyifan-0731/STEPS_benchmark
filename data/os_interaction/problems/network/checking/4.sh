ip_addr=`ping -c 1 baidu.com | grep '64 bytes from' | awk -F ' ' '{print $4}'`
if test '$ip_addr'='$1'; 
then 
exit 0
fi
exit 1