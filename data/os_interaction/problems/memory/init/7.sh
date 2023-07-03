mkdir test
cd test
touch 1.txt
for i in {1..1000}
do
    echo "hello world!\n" >> 1.txt
done