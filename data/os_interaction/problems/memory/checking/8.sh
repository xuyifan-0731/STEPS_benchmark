cd test
status=`ls`
truth="1.txt  2.txt"
status="${status//[$'\t \n']}"
truth="${truth//[$'\t \n']}"
echo $status
if [[ $status != $truth ]]
then 
exit 1
fi
exit 0