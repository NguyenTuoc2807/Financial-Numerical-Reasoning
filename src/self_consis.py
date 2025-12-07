#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json

import yaml
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from data_loader import load_split
from helper import infer_prompt
from prompts import system_template_vi as system_template
from prompts import user_template_vi as user_template


def main(cfg):
    # -----------------------------
    # LOAD DATA
    # -----------------------------
    test_data = load_split(
        cfg["dataset"]["split"],
        cfg["dataset"]["data_dir"]
    )

    # -----------------------------
    # TOKENIZER
    # -----------------------------
    tokenizer = AutoTokenizer.from_pretrained(
        cfg["model"]["model_id"]
    )

    # -----------------------------
    # SAMPLING PARAMS
    # -----------------------------
    sampling_params = SamplingParams(
        temperature   = cfg["sampling"]["temperature"],
        top_p         = cfg["sampling"]["top_p"],
        top_k         = cfg["sampling"]["top_k"],
        max_tokens    = cfg["sampling"]["max_tokens"],
    )

    # -----------------------------
    # LOAD MODEL
    # -----------------------------
    llm = LLM(
        model                    = cfg["model"]["model_id"],
        gpu_memory_utilization  = cfg["model"]["gpu_memory_utilization"],
        enable_chunked_prefill  = False,
        max_model_len           = cfg["model"]["max_model_len"],
    )

    # -----------------------------
    # BUILD PROMPTS
    # -----------------------------
    prompts = []
    for sample in test_data:
        prompt_text = infer_prompt(sample, user_template)

        messages = [
            {"role": "system", "content": system_template},
            {"role": "user", "content": prompt_text}
        ]

        chat_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )

        prompts.append(chat_text)

    # -----------------------------
    # INFERENCE
    # -----------------------------
    N = 7
    for i in range(N - 1):
        outputs = llm.generate(prompts, sampling_params)
        results = []
        for output, sample in zip(outputs, test_data):
            sample[f"model_answer_{i}"] = output.outputs[0].text.strip()
            results.append(sample)

    # -----------------------------
    # SAVE
    # -----------------------------
    with open(cfg["dataset"]["output_path"], "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"Results saved to {cfg['dataset']['output_path']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    main(cfg)
