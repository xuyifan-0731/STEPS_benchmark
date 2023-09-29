cp /etc/apt/sources.list /etc/apt/sources.list.bak
apt-get update
apt-get install -y curl npm git nano
mkdir -p download

# go
# curl -o download/go.tar.gz -SL https://go.dev/dl/go1.18.4.linux-amd64.tar.gz
tar -zxf download/go.tar.gz -C /usr/local
echo "export PATH=/usr/local/go/bin:\$PATH" >> ~/.bashrc
source ~/.bashrc

# js: node
# curl -o download/node.tar.gz -SL https://nodejs.org/download/release/v16.14.0/node-v16.14.0-linux-x64.tar.gz
mkdir -p /usr/local/lib/nodejs
tar -zxf download/node.tar.gz -C /usr/local/lib/nodejs
mv /usr/local/lib/nodejs/node-v16.14.0-linux-x64 /usr/local/lib/nodejs/node
npm install -g js-md5@0.7.3
echo "export PATH=/usr/local/lib/nodejs/node/bin:\$PATH" >> ~/.bashrc
echo "export NODE_PATH=/usr/local/lib/node_modules" >> ~/.bashrc

# c++: boost
apt-get install -y build-essential
apt-get install -y g++
# curl -o download/boost_1_71_0.tar.gz -SL https://boostorg.jfrog.io/artifactory/main/release/1.71.0/source/boost_1_71_0.tar.gz
tar -zxf download/boost_1_71_0.tar.gz -C download/boost_1_71_0
cd download/boost_1_71_0 && ./bootstrap.sh && ./b2 install --prefix=/usr/ && cd ../..

# c++: openssl
# curl -o download/openssl.tar.gz -SL https://www.openssl.org/source/old/3.0/openssl-3.0.0.tar.gz
tar -zxf download/openssl.tar.gz
cd openssl-3.0.0 && ./Configure && make && make install && cd .. && rm -r openssl-3.0.0
echo "export PATH=/usr/bin/openssl:\$PATH" >> ~/.bashrc

# java: jdk
# curl -o download/jdk.tar.gz -SL https://download.oracle.com/java/18/archive/jdk-18_linux-x64_bin.tar.gz
mkdir -p /usr/java
tar -zxf download/jdk.tar.gz -C /usr/java
java_path=`ls /usr/java/`
JAVA_HOME=/usr/java/${java_path}
echo "export JAVA_HOME=/usr/java/${java_path}" >> ~/.bashrc
update-alternatives --install /usr/bin/java java $JAVA_HOME/bin/java 20000
update-alternatives --install /usr/bin/javac javac $JAVA_HOME/bin/javac 20000

tar -zxf src/tasks/humaneval_x/env/vendor.tar.gz -C src/tasks/humaneval_x/env

source ~/.bashrc