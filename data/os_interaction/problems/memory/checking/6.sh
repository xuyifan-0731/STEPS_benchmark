cd test
status=`ls`
truth="1.txt  3.txt  origin  target"
status="${status//[$'\t \n']}"
truth="${truth//[$'\t \n']}"
echo $status
if [[ $status != "$truth" ]]
then 
exit 1
fi


cd target
status=`ls`
truth="2.txt  4.txt"
status="${status//[$'\t \n']}"
truth="${truth//[$'\t \n']}"
echo $status
if [[ $status != $truth ]]
then 
exit 1
fi

cd ../origin
status=`ls`
truth="5.txt"
status="${status//[$'\t \n']}"
truth="${truth//[$'\t \n']}"
echo $status
if [[ $status != $truth ]]
then 
exit 1
fi

exit 0

