import sys
import os, shutil
import signal
import subprocess
import platform
import time
import json
from config import *
 
def run_cmd(cmd_string, timeout=600):
    print("命令为：" + cmd_string)
    p = subprocess.Popen(cmd_string, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True, close_fds=True,
                         start_new_session=True)
 
    format = 'utf-8'
    if platform.system() == "Windows":
        format = 'gbk'
 
    try:
        (msg, errs) = p.communicate(timeout=timeout)
        ret_code = p.poll()
        if ret_code:
            code = 1
            msg = "[Error]Called Error ： " + str(msg.decode(format))
        else:
            code = 0
            msg = str(msg.decode(format))
    except subprocess.TimeoutExpired:
        # 注意：不能只使用p.kill和p.terminate，无法杀干净所有的子进程，需要使用os.killpg
        p.kill()
        p.terminate()
        os.killpg(p.pid, signal.SIGTERM)
 
        # 注意：如果开启下面这两行的话，会等到执行完成才报超时错误，但是可以输出执行结果
        # (outs, errs) = p.communicate()
        # print(outs.decode('utf-8'))
 
        code = 1
        msg = "[ERROR]Timeout Error : Command '" + cmd_string + "' timed out after " + str(timeout) + " seconds"
    except Exception as e:
        code = 1
        msg = "[ERROR]Unknown Error : " + str(e)
 
    return code, msg

if __name__ == '__main__':
    ai1 = sys.argv[1]
    ai2 = sys.argv[2]
    stage = int(sys.argv[3])
    # winrate
    ai1_winrate = 0
    ai2_winrate = 0
    
    for i in range(test_times):
        stamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(int(time.time())))
        save_dir = f'{result_dir}/{stage}_{ai1}_{ai2}/{stamp}'
        os.makedirs(save_dir)
        
        cmd = f'python judger.py {root_dir}/logic/bin/main3 %s %s config {save_dir}/replay.json'
        msg = run_cmd(cmd % (AIs[ai1] % (stage, 0, save_dir), AIs[ai2] % (stage, 1, save_dir)))[1]
        time.sleep(1)
        print(msg)
        
        meta = {'ai1': ai1, 'ai2': ai2}
        
        if "\"0\" : 0" in msg:
            meta['winner'] = '1'
            ai2_winrate += 1
        else:
            meta['winner'] = '0'
            ai1_winrate += 1
                
        with open(save_dir + '/meta.json', 'w') as f:
            f.write(json.dumps(meta))
    
    ai1_winrate /= test_times
    ai2_winrate /= test_times
    
    print(f'ai1 win: {ai1_winrate}\nai2 win: {ai2_winrate}')