answer=`ls -sh 1.txt`
echo $answer
echo $1
if [[ $answer = $1 ]]
then 
exit 0
fi

answer=`ls -l |grep 1.txt`
if [[ $answer = $1 ]]
then 
exit 0
fi

exit 1