answer=`cat /etc/hosts | grep '127.0.0.1       mytest.com'`
if test '$answer'='127.0.0.1       mytest.com';
then 
exit 0
fi
exit 1