http_proxy=`echo $HTTP_PROXY`
if test '$http_proxy'='http://127.0.0.1:1086'; 
then 
exit 0
fi
exit 1