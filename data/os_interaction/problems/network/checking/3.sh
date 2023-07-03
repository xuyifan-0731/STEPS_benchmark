answer=`cat /etc/proxychains.conf | grep 'socks5 127.0.0.1 8000'`
if test '$answer'='socks5 127.0.0.1 8000';
then 
exit 0
fi
exit 1