#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re

from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from prompts import re_infer_user_template as re_infer_user_template
from prompts import rewrite_sys_template as rewrite_sys_template
from prompts import rewrite_user_template as rewrite_user_template
from prompts import system_template_vi as system_template
from prompts import user_template_vi as user_template
from prompts import verify_sys_template as verify_sys_template
from prompts import verify_user_template as verify_user_template


# -----------------------
# Helper
# -----------------------
def table_to_markdown(table):
    if not table:
        return ""
    header = table[0]
    rows = table[1:]
    md = "| " + " | ".join(header) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"
    return md

def extract_verification_json(response: str):
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()

    json_match = re.search(r'\{.*\}', response, flags=re.DOTALL)
    if not json_match:
        return None

    json_str = json_match.group(0)

    try:
        json_str = json_str.replace('\n', ' ').replace('\r', ' ').strip()
        json_str = re.sub(r"\\'", "'", json_str)
        data = json.loads(json_str)
        return {
            "comment": data.get("comment", "").strip(),
            "conclusion": data.get("conclusion", "").strip()
        }
    except json.JSONDecodeError:
        return None

def extract_answer(response: str):
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()

    return response


def verify_prompt(sample):
    pre_text = ''.join(sample['pre_text']).strip()
    table_md_str = table_to_markdown(sample['table'])
    post_text = ''.join(sample['post_text']).strip()
    question = sample['question']
    model_answer = sample['model_answer']
    return verify_user_template.format(
        pre_text=pre_text,
        table_md_str=table_md_str,
        post_text=post_text,
        question=question,
        model_answer=model_answer
    )
def re_infer_prompt(sample):
    pre_text = ''.join(sample['pre_text']).strip()
    table_md_str = table_to_markdown(sample['table'])
    post_text = ''.join(sample['post_text']).strip()
    question = sample['question']
    model_answer = sample['model_answer']
    comment = sample['comment']
    return re_infer_user_template.format(
        pre_text=pre_text,
        table_md_str=table_md_str,
        post_text=post_text,
        question=question,
        model_answer=model_answer,
        comment=comment
    )

def infer_prompt(sample):
    pre_text = ''.join(sample['pre_text']).strip()
    table_md_str = table_to_markdown(sample['table'])
    post_text = ''.join(sample['post_text']).strip()
    question = sample['question']
    return user_template.format(
        pre_text=pre_text,
        table_md_str=table_md_str,
        post_text=post_text,
        question=question
    )


def build_prompt(data, system_template, flag, think=True):
    prompts = []
    for sample in data:
        if flag == 2:
            prompt = infer_prompt(sample)
        elif flag == 3:
            prompt = verify_prompt(sample)
        elif flag == 4:
            prompt = re_infer_prompt(sample)
    
        messages = [
            {"role" : "system", "content" : system_template},
            {"role": "user", "content": prompt}
        ]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=think,
        )
        prompts.append(text)

    return prompts

dataset_dir = "data/viNumericalQA"

def load_split(split_name):
    file_path = os.path.join(dataset_dir, f"{split_name}.json")
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    result = []
    for item in data:
        example = {
            "id": item.get("id", ""),
            "pre_text": item.get("pre_text", ""),
            "post_text": item.get("post_text", ""),
            "table": item.get("table", {}),
            "question": item.get("qa", {}).get("question", ""),
            "program": item.get("qa", {}).get("program", ""),
            "exe_ans": item.get("qa", {}).get("exe_ans", ""),
        }
        result.append(example)

    print(f"{len(result)} sample {split_name}")
    return result


# -----------------------
# MAIN
# -----------------------
def run_batch(prompts, llm, tokenizer, sampling_params):
    texts = []
    for msg in prompts:
        text = tokenizer.apply_chat_template(
            [{"role": "user", "content": msg}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True
        )
        texts.append(text)
    outputs = llm.generate(texts, sampling_params)
    return [o.outputs[0].text.strip() for o in outputs]

if __name__ == "__main__":
    dataset_dir = "./data/viNumericalQA"
    model_id = "unsloth/Qwen3-8B"
    sampling_params = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, repetition_penalty=1.15, max_tokens=32768)

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    llm = LLM(
        model=model_id,
        gpu_memory_utilization=0.5,
        enable_chunked_prefill=False,
        max_model_len=8192,
    )

    # Load dataset
    data = load_split("test")


    print("PHASE 2 — PRE-ANALYSIS")
    pa_prompts = build_prompt(data, system_template, 2)
    pa_outputs = run_batch(pa_prompts, llm, tokenizer, sampling_params)

    for s, out in zip(data, pa_outputs):
        s["model_answer"] = extract_answer(out)

    print("PHASE 3 — VERIFY")
    verify_prompts = build_prompt(data, verify_sys_template, 3, False)
    verify_outputs = run_batch(verify_prompts, llm, tokenizer, sampling_params)

    for s, out in zip(data, verify_outputs):
        js = extract_verification_json(out)
        if not js:
            s["verify"] = "No"
            s["comment"] = "parse error"
        else:
            s["verify"] = js.get("conclusion", "")
            s["comment"] = js.get("comment","")

    max_loop = 3
    for loop in range(max_loop):
        fail = [s for s in data if s["verify"] != "Yes"]
        if not fail:
            break

        print(f"Loop {loop+1}: re-infer {len(fail)} samples")

        reinfer_prompts = build_prompt(fail, system_template, 4, False)
        reinfer_outputs = run_batch(reinfer_prompts, llm, tokenizer, sampling_params)

        # Cập nhật pre-analysis
        for s, out in zip(fail, reinfer_outputs):
            s["model_answer"] = extract_answer(out)

        # Verify lại
        verify_prompts = build_prompt(fail, verify_sys_template, 3, False)
        verify_outputs = run_batch(verify_prompts, llm, tokenizer, sampling_params)

        for s, out in zip(fail, verify_outputs):
            js = extract_verification_json(out)
            if not js:
                s["verify"] = "No"
                s["comment"] = "parse error"
            else:
                s["verify"] = js.get("conclusion", "")
                s["comment"] = js.get("comment","")


    with open("flow_reasoning.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("DONE.")
