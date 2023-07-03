# Coding: HumanEval-X

We use [HumanEval-X](https://github.com/THUDM/CodeGeeX/blob/main/codegeex/benchmark/README.md), a benchmark for evaluating the multilingual coding ability of language models. HumanEval-X consists of 820 high-quality human-crafted data samples (each with test cases) in Python, C++, Java, JavaScript, and Go, and can be used for various tasks. 

## Environment Setup

HumanEval-X evaluates the generated code by executing it with test cases. For the execution environment, the versions of the programming language environments and packages we use are as follows:

| Dependency | Version  |
| ---------- | -------- |
| Python     | 3.8.12   |
| JDK        | 18.0.2.1 |
| Node.js    | 16.14.0  |
| js-md5     | 0.7.3    |
| C++        | 11       |
| g++        | 7.5.0    |
| Boost      | 1.71.0   |
| OpenSSL    | 3.0.0    |
| Go         | 1.18.4   |

For languages other than Python, we provide the script for setting up the environment [here](src/tasks/coding/setup/setup_ubuntu.sh).

To set up the programming language dependencies, run the following scripts:

```shell
bash src/tasks/coding/setup/setup_ubuntu.sh
source ~/.bashrc
```