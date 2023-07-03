ip=`ifconfig eth0 | grep inet | awk -F ' ' '{print $2}'`
if test '$ip'='$1'; 
then 
exit 0
fi
exit 1