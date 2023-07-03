ans=`route | grep default | awk -F ' ' '{print $2}'`
if test '$ans'='$1'; 
then 
exit 0
fi
exit 1