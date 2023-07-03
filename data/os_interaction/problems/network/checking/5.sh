status=`ping baidu.com -c 1 | grep '1 packets received'`
if test -n '$status'; 
then 
ans='yes'
else
ans='no'
fi

