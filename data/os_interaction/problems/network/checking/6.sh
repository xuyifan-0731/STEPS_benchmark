cache=`nscd -g | grep 'used data pool size' | sed -n '3p' | awk -F ' ' '{print $1}'`
if test '$cache'='0'; 
then 
exit 0
fi
exit 1