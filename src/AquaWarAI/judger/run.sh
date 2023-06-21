#!bin/bash
python batch_test.py baseline1 chatgpt-en 1
python cal_metric.py /workspace/hanyu/dhl/AquaWarAI/result/1_baseline1_chatgpt-en > chatgpt-en_second1.txt

python batch_test.py chatgpt-en baseline1 1
python cal_metric.py /workspace/hanyu/dhl/AquaWarAI/result/1_chatgpt-en_baseline1 > chatgpt-en_first1.txt

python batch_test.py baseline1 claude-en 1
python cal_metric.py /workspace/hanyu/dhl/AquaWarAI/result/1_baseline1_claude-en > claude-en_second1.txt

python batch_test.py claude-en baseline1 1
python cal_metric.py /workspace/hanyu/dhl/AquaWarAI/result/1_claude-en_baseline1 > claude-en_first1.txt