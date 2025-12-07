#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unsloth
import argparse
import json
import os

import pandas as pd
import torch
import yaml
from datasets import Dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only

from helper import infer_prompt
from prompts import system_template_vi as system_template
from prompts import user_template_vi as user_template


# -----------------------------
# Helper functions
# -----------------------------
def assistant_msg(sample):
    summary = sample.get("summary","")
    reasoning = sample.get("reasoning","")
    verify = sample.get("verify", "")
    program = sample.get("program","")

    think_block = (
        "<think>"
        f"Based on the question, the document provides the following information:\n"
        f"{summary}\n"
        f"{reasoning}"
        f"{verify}"
        "</think>"
    )
    return f"{think_block}\n```{program}```"

def format_dataset(x):
    return [
        {"role": "user",      "content": infer_prompt(x, user_template)},
        {"role": "assistant", "content": assistant_msg(x)},
    ]


# -----------------------------
# Main workflow
# -----------------------------
def main(cfg):
    # ---------
    # Load data
    # ---------
    print(f"Loading data from {cfg['data_path']} ...")
    with open(cfg["data_path"], "r", encoding="utf-8") as f:
        data = json.load(f)

    dataset = pd.DataFrame(data)
    print(f"Loaded {len(dataset)} samples.")

    dataset["Messages"] = dataset.apply(format_dataset, axis=1)

    # ---------------------------
    # Load model + tokenizer
    # ---------------------------
    print("Loading model and tokenizer...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=cfg["model_name"],
        max_seq_length=cfg["max_seq_length"],
        load_in_4bit=False,
        max_lora_rank=cfg["lora_rank"],
        gpu_memory_utilization=cfg["gpu_memory_utilization"],
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=cfg["lora_rank"],
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=cfg["lora_rank"] * 2,
        use_gradient_checkpointing="unsloth",
        random_state=cfg["seed"],
    )

    # Tokenize
    dataset["Messages"] = dataset.apply(format_dataset, axis=1)
    dataset["N"] = dataset["Messages"].apply(lambda x: len(tokenizer.apply_chat_template(x)))

    dataset = dataset.loc[dataset["N"] <= cfg["max_seq_length"] // 2].copy()
    dataset["text"] = tokenizer.apply_chat_template(dataset["Messages"].values.tolist(), tokenize = False)
    dataset = Dataset.from_pandas(dataset)

    # ---------------------------
    # Prepare SFT trainer
    # ---------------------------
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            per_device_train_batch_size=cfg["training"]["batch_size"],
            gradient_accumulation_steps=cfg["training"]["gradient_accumulation_steps"],
            warmup_steps=cfg["training"]["warmup_steps"],
            num_train_epochs=cfg["training"]["epochs"],
            learning_rate=cfg["training"]["learning_rate"],
            logging_steps=cfg["training"]["logging_steps"],
            optim=cfg["training"]["optim"],
            weight_decay=cfg["training"]["weight_decay"],
            lr_scheduler_type=cfg["training"]["lr_scheduler_type"],
            seed=cfg["seed"],
            report_to=cfg["report_to"],
            logging_dir = cfg["training"]["logging_dir"],
        ),
    )

    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )

    # -------------
    # GPU stats
    # -------------
    gpu_stats = torch.cuda.get_device_properties(0)
    start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
    print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
    print(f"{start_gpu_memory} GB of memory reserved.")

    trainer_stats = trainer.train()

    # -------------
    # Memory stats
    # -------------
    used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
    used_percentage = round(used_memory / max_memory * 100, 3)
    lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
    print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
    print(
        f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training."
    )
    print(f"Peak reserved memory = {used_memory} GB.")
    print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
    print(f"Peak reserved memory % of max memory = {used_percentage} %.")
    print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")

    # -------------------------
    # Save model
    # -------------------------
    os.makedirs(cfg["output_dir"], exist_ok=True)
    out_path = os.path.join(cfg["output_dir"], cfg["output_name"])
    print(f"Saving merged model to {out_path}")
    model.save_pretrained(out_path)
    tokenizer.save_pretrained(out_path)
    # model.save_pretrained_merged(out_path, tokenizer, save_method="merged_16bit")

    print("All done.")


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True, help="YAML config file")
    args = parser.parse_args()

    # Load YAML
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    main(cfg)
