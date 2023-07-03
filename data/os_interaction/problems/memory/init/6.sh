mkdir test
cd test
touch 1.txt
touch 2.txt
touch 3.txt

for i in {1..100}
do
    echo "hello\n" >> 1.txt
done

for i in {1..1000}
do
    echo "hello\n" >> 2.txt
done

echo "hello\n" >> 3.txt

mkdir origin
cd origin
touch 5.txt
for i in {1..100}
do
    echo "hello\n" >> 5.txt
done
touch 4.txt
for i in {1..1000}
do
    echo "hello\n" >> 4.txt
done

cd ..
