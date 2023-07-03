status=`ping baidu.com -c 1 | grep '1 packets received'`
if test -n '$status'; 
then 
echo 'yes'
else
echo 'no'
fi

if test '$ans'='$1'; 
then 
exit 0
fi
exit 1