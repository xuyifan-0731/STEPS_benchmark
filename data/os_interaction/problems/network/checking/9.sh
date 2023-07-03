time=`ping -c 10 baidu.com | grep '10 packets' | awk -F ' ' '{print $10}'`
if test '$time'='$1'; 
then 
exit 0
fi
exit 1