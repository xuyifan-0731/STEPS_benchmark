answer=`df -m | grep overlay`
answer="${answer//[$'\t \n']}"
inf="${1//[$'\t \n']}"
echo $answer
echo $inf
if [[ $answer = $inf ]]
then 
exit 0
fi
exit 1