# Config

test_times = 50
root_dir = '..'

# Register your AI
AIs = {
    'chatgpt-en': f'python+{root_dir}/AI_SDK/Python/main.py+en+chatgpt+%d+%d+%s',
    'chatgpt-cn': f'python+{root_dir}/AI_SDK/Python/main.py+cn+chatgpt+%d+%d+%s',
    'baseline1': f'python+{root_dir}/AI_SDK/Python/basline1.py+%d+%d+%s',
    'baseline2': f'python+{root_dir}/AI_SDK/Python/basline2.py+%d+%d+%s',
    'chatglm-cn': f'python+{root_dir}/AI_SDK/Python/main.py+cn+chatglm+%d+%d+%s',
    'gpt4-en': f'python+{root_dir}/AI_SDK/Python/main.py+en+gpt4+%d+%d+%s',
    'claude-en': f'python+{root_dir}/AI_SDK/Python/main.py+en+claude+%d+%d+%s',
    'vicuna-en': f'python+{root_dir}/AI_SDK/Python/main.py+en+vicuna+%d+%d+%s',
}


result_dir = f'{root_dir}/result'