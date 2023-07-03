import re
import json
import gzip
from typing import Dict, Iterable

LANGUAGE_TAG = {
    "c++"          : "// C++",
    "cpp"          : "// C++",
    "c"            : "// C",
    "c#"           : "// C#",
    "go"           : "// Go",
    "java"         : "// Java",
    "javascript"   : "// JavaScript",
    "js"           : "// JavaScript",
    "kotlin"       : "// Kotlin",
    "php"          : "// PHP",
    "python"       : "# Python",
    "rust"         : "// Rust",
    "ruby"         : "# Ruby",
    "typescript"   : "// TypeScript",
}

def process_extra_prompt(prompt, language):
    language = language.lower()
    if language in LANGUAGE_TAG:
        extra_prompt = LANGUAGE_TAG[language] + "\n"
    else:
        extra_prompt = ""

    return extra_prompt + prompt.lstrip()

def code_generation_end(code, language):
    if language.lower() == 'python':
        end_words = ["\ndef", "\nclass", "\nif", "\n#", "\nprint", "\nassert"]
        for w in end_words:
            if w in code:
                return True
    
    return False

re_cpp_sig = r"^ *(?:[a-zA-Z_][a-zA-Z0-9_<>,: ]*|long long) +(?!main[ (])([a-zA-Z_][a-zA-Z0-9_]*) *\([^\)]*\) *{ *$"
re_java_sig = r"^ *public [a-zA-Z_][a-zA-Z0-9_<>, ]* +(?!main[ (])([a-zA-Z_][a-zA-Z0-9_]*) *\([^\)]*\) *(?: throws +[a-zA-Z_][a-zA-Z0-9_]*)? *{ *$"
re_js_sig = r"^ *const ([a-zA-Z_][a-zA-Z0-9_]*) = \([^\)]*\) => *{ *$"
re_go_sig = r"^ *func ([a-zA-Z_][a-zA-Z0-9_]*) *\([^\)]*\) *(?:[^ ]+)? *{ *$"
re_python_sig = r"^ *def ([a-zA-Z_][a-zA-Z0-9_]*)\(.+: *$"
sig_regex = {
    'cpp': re_cpp_sig,
    'go': re_go_sig,
    'java': re_java_sig,
    'js': re_js_sig,
    'python': re_python_sig
}
def _find_gen_func_sig(prompt, language):
    func_name = ""
    for x in prompt.splitlines():
        m = re.match(sig_regex[language], x)
        if m:
            # always pick the last one, since there could pre-defined functions.
            func_name = m.group(1)
    return func_name.strip()

def parse_code_from_chat(ret, prompt, language_tag="python"):
    if language_tag == 'js':
        ret = ret.replace('```\n}', '}')
    if ret.count("```") % 2 == 1:
        ret = ret[:ret.rfind("```")]
    has_code_block = "```" in ret
    if has_code_block:
        gen = ret.split("```")[1]
        gen = gen[gen.find('\n'):].strip()
    else:
        gen = ret
    func_name = _find_gen_func_sig(prompt, language_tag)
    gen_lines = gen.splitlines()
    for i, l in enumerate(gen_lines):
        sub_name = _find_gen_func_sig(l, language_tag)
        if sub_name.lower() == func_name.lower():
            gen = '\n'.join(gen_lines[i + 1:])
            break
    if language_tag == 'python':
        gen = '\n    ' + gen.strip()
    elif language_tag == 'java':
        cnt_lbrace, cnt_rbrace = gen.count('{'), gen.count('}')
        if cnt_rbrace - cnt_lbrace == 1:
            gen = '\n'.join(['    ' + l for l in gen.splitlines()]).rstrip() + '\n}'
    elif language_tag == 'cpp':
        main_pos = gen.find('\nint main')
        if main_pos != -1:
            gen = gen[:main_pos]
    elif language_tag == 'go':
        main_pos = gen.find('\nfunc main')
        if main_pos != -1:
            gen = gen[:main_pos]
    elif language_tag == 'js':
        gen = gen.replace('console.log', '')
        end_pos = gen.find('\n};')
        if end_pos != -1:
            gen = gen[:end_pos + len('\n};')]
    if language_tag in ['cpp', 'go', 'js']:
        cnt_lbrace, cnt_rbrace = gen.count('{'), gen.count('}')
        if cnt_rbrace == cnt_lbrace:
            gen = gen + '\n}'
    return gen

def cleanup_code(
    code: str,
    language: str = None,
):  
    code = code.replace('\t', '    ')
    if language.lower() == "python":
        end_words = ["\ndef", "\nclass", "\nif", "\n#", "\nprint", "\nassert"]
        for w in end_words:
            if w in code:
                code = code[:code.rfind(w)].rstrip()
        lines = code.splitlines()
        for i, l in enumerate(lines):
            l = l.rstrip()
            if len(l) > 0 and not l.startswith(' '):
                code = '\n'.join(lines[:i])
                break
    elif language.lower() == "java":
        main_pos = code.find("public static void main")
        if main_pos != -1:
            code = code[:main_pos] + '}'
        if '}' in code:
            code = code[:code.rfind('}')] + '}'
        if code.count('{') + 1 == code.count('}'):
            code += "\n}"
        bracket_stack = 2
        for pos in range(len(code)):
            if code[pos] == '{':
                bracket_stack += 1
            elif code[pos] == '}':
                bracket_stack -= 1
            if bracket_stack == 0:
                code = code[:pos + 1]
                break
    elif language.lower() == "go":
        end_words = ["\n//", "\nfunc main("]
        for w in end_words:
            if w in code:
                code = code[:code.rfind(w)]
        if '}' in code:
            code = code[:code.rfind('}')] + '}'
        bracket_stack = 1
        for pos in range(len(code)):
            if code[pos] == '{':
                bracket_stack += 1
            elif code[pos] == '}':
                bracket_stack -= 1
            if bracket_stack == 0:
                code = code[:pos + 1]
                break
    elif language.lower() == "cpp":
        if '}' in code:
            code = code[:code.rfind('}')] + '}'
        bracket_stack = 1
        for pos in range(len(code)):
            if code[pos] == '{':
                bracket_stack += 1
            elif code[pos] == '}':
                bracket_stack -= 1
            if bracket_stack == 0:
                code = code[:pos + 1]
                break
    elif language.lower() == "js":
        if '}' in code:
            code = code[:code.rfind('}')] + '}'
        bracket_stack = 1
        for pos in range(len(code)):
            if code[pos] == '{':
                bracket_stack += 1
            elif code[pos] == '}':
                bracket_stack -= 1
            if bracket_stack == 0:
                code = code[:pos + 1]
                break
    return code

def stream_jsonl(filename: str) -> Iterable[Dict]:
    """
    Parses each jsonl line and yields it as a dictionary
    """
    if filename.endswith(".gz"):
        with open(filename, "rb") as gzfp:
            with gzip.open(gzfp, "rt") as fp:
                for line in fp:
                    if any(not x.isspace() for x in line):
                        yield json.loads(line)
    else:
        with open(filename, "r", encoding='utf-8') as fp:
            for line in fp:
                if any(not x.isspace() for x in line):
                    yield json.loads(line)