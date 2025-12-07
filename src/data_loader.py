import json
import os


def load_split(split_name, dataset_dir):
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