#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unsloth
import argparse
import json
import os
import re

import numpy as np
import torch
import yaml
from datasets import Dataset
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel
from vllm import SamplingParams

from data_loader import load_split
from helper import eval_program, infer_prompt, program_tokenization
from prompts import system_template_vi as system_template
from prompts import user_template_vi as user_template

# =================================================================
# REWARD FUNCTIONS
# =================================================================

PRINTED_TIMES = 0
PRINT_EVERY_STEPS = 5

def check_answer(prompts, completions, answer, tables, **kwargs):
    global PRINTED_TIMES, PRINT_EVERY_STEPS

    question = prompts[0][-1]["content"]
    responses = [completion[0]["content"] for completion in completions]
    answer_format = re.compile(
        r"```(?:[^\n]*\n)?([\s\S]*?)```",
        re.MULTILINE
    )

    responses_ans = [re.sub(r"<think>[\s\S]*?</think>", "", r, flags=re.DOTALL).strip() for r in responses]

    # Lấy nội dung bên trong code block ```
    extracted = [
        match.group(1).strip() if (match := answer_format.search(r)) else None
        for r in responses_ans
    ]

    scores = []

    if PRINTED_TIMES % PRINT_EVERY_STEPS == 0:
        print("*" * 20)
        print("Question:\n", question)
        print("Response:\n", responses[0])
        print("Extracted:\n", extracted[0])
        print("True Answer:\n", answer[0])
    PRINTED_TIMES += 1

    for guess, true_answer, table in zip(extracted, answer, tables):
        if guess is None:
            scores.append(-2.0)
            continue

        score = 0
        if guess.strip() == true_answer.strip():
            score += 3.5
        try:
            guess_program = program_tokenization(guess.strip())
            gold_program = program_tokenization(true_answer.strip())
            exe_guess = eval_program(guess_program, table)
            exe_gold = eval_program(gold_program, table)

            ratio = float(exe_guess) / float(exe_gold)
            if 0.9 <= ratio <= 1.1:
                score += 2.0
            elif 0.8 <= ratio <= 1.2:
                score += 1.5
            else:
                score -= 2.5
        except:
            score -= 4.5

        scores.append(score)

    return scores


# =================================================================
# MAIN TRAINING
# =================================================================
def main(config):

    # ---------------- MODEL ----------------
    model_cfg = config["model"]
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_cfg["base_model"],
        max_seq_length=model_cfg["max_seq_length"],
        load_in_4bit=model_cfg["load_in_4bit"],
        fast_inference=model_cfg["fast_inference"],
        max_lora_rank=model_cfg["lora_rank"],
        gpu_memory_utilization=model_cfg["gpu_memory_utilization"],
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=model_cfg["lora_rank"],
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=model_cfg["lora_rank"] * 2,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # ---------------- DATA ----------------
    data_cfg = config["dataset"]
    data = load_split(data_cfg["dataset_type"], data_cfg["data_dir"])

    prompts = [infer_prompt(x, user_template) for x in data]
    answers = [x["program"] for x in data]
    tables = [x["table"] for x in data]

    dataset = Dataset.from_dict({
        "prompt": prompts,
        "answer": answers,
        "tables": tables,
    })

    dataset = dataset.map(
        lambda x: {
            "prompt": [
                {"role": "system", "content": system_template},
                {"role": "user", "content": x["prompt"]},
            ],
            "answer": x["answer"],
            "tables": x["tables"],
        }
    )

    # tokenize
    tokenized = dataset.map(
        lambda x: {
            "tokens": tokenizer.apply_chat_template(
                x["prompt"], add_generation_prompt=True, tokenize=True
            )
        },
        batched=True,
    )

    tokenized = tokenized.map(lambda x: {"L": len(x["tokens"])})
    max_L = int(np.quantile(tokenized["L"], data_cfg["quantile_filter"]))
    keep = np.where(np.array(tokenized["L"]) <= max_L)[0]
    dataset = dataset.select(keep)

    max_prompt_length = max_L + 1
    max_completion_length = model_cfg["max_seq_length"] - max_prompt_length

    # ---------------- SAMPLING ----------------
    s = config["sampling"]
    sampling = SamplingParams(
        min_p=s["min_p"],
        top_p=s["top_p"],
        top_k=s["top_k"],
        seed=s["seed"],
        stop=[tokenizer.eos_token],
        include_stop_str_in_output=True,
    )

    # ---------------- TRAIN CONFIG ----------------
    grpo_cfg = config["grpo"]
    train_cfg = config["training"]

    args = GRPOConfig(
        vllm_sampling_params=sampling,
        temperature=grpo_cfg["temperature"],
        learning_rate=grpo_cfg["learning_rate"],
        weight_decay=grpo_cfg["weight_decay"],
        warmup_ratio=grpo_cfg["warmup_ratio"],
        lr_scheduler_type=grpo_cfg["lr_scheduler_type"],
        optim=grpo_cfg["optim"],
        logging_steps=1,
        per_device_train_batch_size=grpo_cfg["batch_size"],
        gradient_accumulation_steps=grpo_cfg["grad_acc_steps"],
        num_generations=grpo_cfg["num_generations"],

        max_prompt_length=max_prompt_length,
        max_completion_length=max_completion_length,
        num_train_epochs=train_cfg["num_epochs"],
        max_steps=train_cfg["max_steps"],
        save_steps=train_cfg["save_steps"],
        output_dir=train_cfg["output_dir"],
        report_to="none",
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[check_answer],
        args=args,
        train_dataset=dataset,
    )

    print("Start GRPO training…")
    stats = trainer.train()
    print(f"Training time: {stats.metrics['train_runtime']} sec")

    model.save_lora("grpo_saved_lora")
    # model.save_pretrained_merged("model_grpo", tokenizer, save_method="merged_16bit")

    print("Training complete!")


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    main(cfg)
