cd test
status=`ls`
truth="1.txt  3.txt"
status="${status//[$'\t \n']}"
truth="${truth//[$'\t \n']}"
echo $truth
echo $status
if [[ $status = $truth ]]
then 
exit 0
else
exit 1
fi
