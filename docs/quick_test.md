# 完整数据集一键测试说明

| 数据集名称                       | yaml地址                                         | 备注                                                         | 完整测试需要交互次数          |
| -------------------------------- | ------------------------------------------------ | ------------------------------------------------------------ | ----------------------------- |
| gsm8k                            | configs/tasks/gsm8k                              | 中文+英文，0-shot+few-shot，test set                         | 1319\*4\*2（抽取）            |
| mmlu                             | configs/tasks/mmlu                               | 0-shot                                                       | 14027*2（抽取）               |
| bbh                              | configs/tasks/bbh                                | 3-shot                                                       | 6689*2（抽取）                |
| idiotqa，math，nq-open，triviaqa | configs/tasks/full                               | 0-shot                                                       | 1000/5000/3610/3201*2（抽取） |
| humaneval                        | configs/tasks/humaneval-x/generation/python.yaml | 参考src/tasks/humaneval_x/README.md配置评测。默认sample次数20，需要评测20*164次，可以适当降低sample次数 | 164*n（sample）               |
| humaneval-x（generation）        | configs/tasks/humaneval-x/generation             | 同上                                                         | 820*n（sample）               |
| scibench                         | configs/tasks/scibench                           | 目前实现了zero-sys和zero-cot两个适合chat model的setting      | 564*3                         |
| toxiGen                          | configs/tasks/toxiGen                            | 有完整版（6514）和分层抽样版（1000）条两种数据集大小。<br />需要下载模型[tomh/toxigen_roberta · Hugging Face](https://huggingface.co/tomh/toxigen_roberta)并且修改checkpoint_path参数用于评测。 | 6514/1000                     |
| c-eval                           | configs/tasks/c-eval                             | test集合请在log中的outputs/{time}/c_eval_test_zero_shot/{model}/submit文件夹的文件在ceval官网提交评测 | 13948*2（抽取）               |

