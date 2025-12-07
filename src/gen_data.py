import os
import json
import asyncio
import unicodedata
from typing import Any

from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

from helper import infer_prompt
from data_loader import load_split
from prompts import system_template, user_template


import json
import unicodedata
from typing import Any

def clean_text(s: Any) -> str:
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\u202f", " ")  # narrow no-break space
    s = s.replace("\xa0", " ")    # non-breaking space
    s = unicodedata.normalize("NFKC", s)
    return s.strip()

def parse_response_openai(response) -> dict:
    output = getattr(response, "output", []) or []
    structured_output = {
        "message": None,
        "reasoning": None,
    }

    for sub_output in output:
        if getattr(sub_output, "type", None) == "reasoning":
            reasoning_texts = [
                clean_text(getattr(c, "text", "")) for c in sub_output.content if hasattr(c, "text")
            ]
            structured_output["reasoning"] = "\n".join(reasoning_texts).strip()

        elif getattr(sub_output, "type", None) == "message":
            message_texts = [
                clean_text(getattr(c, "text", "")) for c in sub_output.content if hasattr(c, "text")
            ]
            structured_output["message"] = "\n".join(message_texts).strip()
    return structured_output


# ============================================
# 6. ASYNC LLM CALL
# ============================================
async def infer(sample, client, semaphore, system_template, user_template, model_name):
    messages = [
        {"role": "system", "content": system_template},
        {"role": "user", "content": infer_prompt(sample, user_template)},
    ]

    async with semaphore:
        response = await client.responses.create(
            model=model_name,
            input=messages,
            temperature=0.2,
        )
    return parse_response_openai(response)["message"]


async def async_infer(data, client, system_template, user_template, model_name):
    semaphore = asyncio.Semaphore(100)
    tasks = [
        infer(sample, client, semaphore, system_template, user_template, model_name)
        for sample in data
    ]

    results = await tqdm_asyncio.gather(*tasks, desc="Inference")
    return results


# ============================================
# 7. MAIN SCRIPT
# ============================================
async def main():
    # ----------------------------------------
    # ENV + CONFIG
    # ----------------------------------------
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME")


    dataset_dir = "./data/viNumericalQA"
    out_path = "training_data/gpt_train_data_vlsp.json"

    # ----------------------------------------
    # LOAD DATA
    # ----------------------------------------
    data = load_split(dataset_dir, "train")

    client = AsyncOpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY
    )

    # ----------------------------------------
    # INFERENCE
    # ----------------------------------------
    outputs = await async_infer(
        data, client, system_template, user_template, MODEL_NAME
    )

    # ----------------------------------------
    # MERGE + SAVE
    # ----------------------------------------
    with open(out_path, "r", encoding="utf-8") as f:
        old_data = json.load(f)

    results = []
    for output, sample in zip(outputs, old_data):
        sample["reasoning"] = output
        results.append(sample)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"[DONE] Saved to {out_path}")


# ============================================
# 8. ENTRY POINT
# ============================================
if __name__ == "__main__":
    asyncio.run(main())
