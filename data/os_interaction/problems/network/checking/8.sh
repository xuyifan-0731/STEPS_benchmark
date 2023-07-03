status=`cat /etc/resolv.conf | grep 'nameserver 208.67.222.222'`
if test '$status'='nameserver 208.67.222.222'; 
then 
exit 0
fi
exit 1