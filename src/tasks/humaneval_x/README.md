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

For languages other than Python, we provide the script for setting up the environment [here](setup/setup_ubuntu.sh).

To set up the programming language dependencies, run the following script:

```shell
bash src/tasks/humaneval_x/setup/setup_ubuntu.sh
```

You can modify the script if you want to install dependencies for languages of your choice.

If you encounter the error `sudo: command not found`, please remove all `sudo` from the commands in the script and try again.

After installing the dependencies, run

```shell
source ~/.bashrc
```

to update the environment variables.
