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

## Testing
The method for running this test is the same as for other tasks except as noted below:

Since HumanEval-X verifies results by running test cases, it is necessary to detect runnable code from the entire output of the model. Unlike **completion** models which directly outputs the code, **chat-based** models tend to mix code and text in their output. To extract code components from these outputs, we design a function [`parse_code_from_chat`](utils.py#L62) that aims to match code snippets. Despite our best efforts, this function may be buggy and in some cases may not recognize the code. If this happens, please contact us!

The evaluation procedure by default runs the extraction process mentioned above. If you are evaluating a **completion** model which outputs the function implementation directly, you can remove this extraction process by commenting out [line 1](task.py#L75) and [line 2](task.py#L106) to avoid potential bugs in the `parse_code_from_chat` function.