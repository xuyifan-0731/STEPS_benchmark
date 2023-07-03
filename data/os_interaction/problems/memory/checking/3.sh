answer=`cat /proc/meminfo | grep MemTotal`
echo $answer
echo $1
if [[ $answer = $1 ]]
then 
exit 0
fi
exit 1