mkdir test
cd test
touch 1.txt
for i in {1..1000}
do
    echo "hello world!" >> 1.txt
done

touch 2.txt
for i in {1..800}
do
    echo "hello world!" >> 2.txt
done

touch 1.txt
for i in {1..700}
do
    echo "hello world!" >> 3.txt
done

touch 1.txt
for i in {1..600}
do
    echo "hello world!" >> 4.txt
done
