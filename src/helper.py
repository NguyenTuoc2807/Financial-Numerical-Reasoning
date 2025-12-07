import re


def infer_prompt(sample, user_template):
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
    
def table_to_markdown(table):
    header = table[0]
    rows = table[1:]

    md = "| " + " | ".join(header) + " |\n"
    # md += "| " + " | ".join(["---"] * len(header)) + " |\n"
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"
    return md

def str_to_num(text):
    text = text.replace(",", "").strip()
    try:
        num = float(text)
    except ValueError:
        if "%" in text:
            text = text.replace("%", "")
            try:
                num = float(text)
                num = num / 100.0
            except ValueError:
                num = "n/a"
        elif "const" in text:
            text = text.replace("const_", "")
            try:
                num = float(text)
            except ValueError:
                num = "n/a"
        else:
            num = "n/a"
    return num

def process_row(values):
    nums = []
    for v in values:
        try:
            if v is None:
                continue
            v = str(v).strip()
            if v == "" or v.lower() in ["none", "nan", "n/a", "-", "na"]:
                continue

            matches = re.search(r"[-+]?\d+(?:[\.,]\d+)?", v)
            if not matches:
                continue
            m = matches.group(0).replace(",", ".")
            try:
                nums.append(float(m))
            except ValueError:
                continue
        except Exception:
            continue
    return nums

def program_tokenization(original_program):
    program = []
    cur_tok = ''
    bracket_level = 0
    i = 0
    while i < len(original_program):
        c = original_program[i]
        if c == '(':
            bracket_level += 1
            if bracket_level == 1:
                cur_tok += c
                program.append(cur_tok.strip())
                cur_tok = ''
            else:
                cur_tok += c
        elif c == ')':
            if bracket_level == 1:
                if cur_tok.strip() != '':
                    program.append(cur_tok.strip())
                    cur_tok = ''
                program.append(')')
            else:
                cur_tok += c
            bracket_level -= 1
        elif c == ',':
            if bracket_level == 0:
                if cur_tok.strip() != '':
                    program.append(cur_tok.strip())
                    cur_tok = ''
            elif bracket_level == 1:
                if cur_tok.strip() != '':
                    program.append(cur_tok.strip())
                    cur_tok = ''
            else:
                cur_tok += c
        else:
            cur_tok += c
        i += 1
    if cur_tok.strip() != '':
        program.append(cur_tok.strip())
    program.append('EOF')
    return program

def eval_program(program, table):
    all_ops = ["add", "subtract", "multiply", "divide", "exp", "greater",
           "table_max", "table_min", "table_sum", "table_average"]

    invalid_flag = 0
    this_res = "n/a"

    try:
        # Make a copy to avoid modifying original
        program = list(program)

        # Check if program ends with EOF
        if not program or program[-1] != "EOF":
            return "n/a"

        program = program[:-1]  # remove EOF

        # Check structure validity
        if len(program) % 4 != 0:
            return "n/a"

        for ind, token in enumerate(program):
            if ind % 4 == 0:
                if token.strip("(") not in all_ops:
                    return "n/a"
            elif ind % 4 == 3:
                if token != ")":
                    return "n/a"

        # Parse operations directly from token array
        # Structure: [op(, arg1, arg2, ), op(, arg1, arg2, ), ...]
        res_dict = {}

        for step_idx in range(0, len(program), 4):
            ind = step_idx // 4

            # Extract operation and arguments from tokens
            op = program[step_idx].strip("(")
            arg1 = program[step_idx + 1].strip()
            arg2 = program[step_idx + 2].strip()
            # program[step_idx + 3] should be ")"

            if op in ["add", "subtract", "multiply", "divide", "exp", "greater"]:
                # Resolve arg1
                if "#" in arg1:
                    arg1_ind = int(arg1.replace("#", ""))
                    if arg1_ind not in res_dict or arg1_ind >= ind:
                        invalid_flag = 1
                        break
                    arg1 = res_dict[arg1_ind]
                else:
                    arg1 = str_to_num(arg1)
                    if arg1 == "n/a":
                        invalid_flag = 1
                        break

                # Resolve arg2
                if "#" in arg2:
                    arg2_ind = int(arg2.replace("#", ""))
                    if arg2_ind not in res_dict or arg2_ind >= ind:
                        invalid_flag = 1
                        break
                    arg2 = res_dict[arg2_ind]
                else:
                    arg2 = str_to_num(arg2)
                    if arg2 == "n/a":
                        invalid_flag = 1
                        break

                # Execute operation
                if op == "add":
                    this_res = arg1 + arg2
                elif op == "subtract":
                    this_res = arg1 - arg2
                elif op == "multiply":
                    this_res = arg1 * arg2
                elif op == "divide":
                    if arg2 == 0:
                        invalid_flag = 1
                        break
                    this_res = arg1 / arg2
                elif op == "exp":
                    this_res = arg1 ** arg2
                elif op == "greater":
                    this_res = "yes" if arg1 > arg2 else "no"

                res_dict[ind] = this_res

            elif "table" in op:
                # --- 1. Build row dictionary ---
                table_dict = {}
                for row in table:
                    if len(row) > 0:
                        table_dict[row[0]] = row[1:]

                # --- 2. Build header (column names) ---
                header = table[0][1:] if len(table) > 0 else []

                # arg1 là tên cột/hàng (có thể chứa dấu ngoặc)
                target_name = arg1.strip() if arg1 else ""
                cal_values = None

                # --- 3. Nếu target là hàng ---
                if target_name in table_dict:
                    cal_values = process_row(table_dict[target_name])

                # --- 4. Nếu target là cột ---
                elif target_name in header:
                    col_index = header.index(target_name) + 1  # vì cột 0 là tên hàng
                    col_values = []
                    for i in range(1, len(table)):
                        if len(table[i]) > col_index:
                            val = table[i][col_index]
                            col_values.append(val)
                    cal_values = process_row(col_values)

                # --- 5. Nếu không tìm thấy ---
                else:
                    invalid_flag = 1
                    break

                # --- 6. Nếu không có giá trị hợp lệ ---
                if not cal_values:
                    invalid_flag = 1
                    break

                # --- 7. Tính toán kết quả ---
                if op == "table_max":
                    this_res = max(cal_values)
                elif op == "table_min":
                    this_res = min(cal_values)
                elif op == "table_sum":
                    this_res = sum(cal_values)
                elif op == "table_average":
                    this_res = sum(cal_values) / len(cal_values)
                else:
                    invalid_flag = 1
                    break

                res_dict[ind] = this_res

        if invalid_flag:
            return "n/a"

        # Round numerical results
        if this_res != "yes" and this_res != "no" and this_res != "n/a":
            # Don't round here - keep full precision for comparison
            pass

    except Exception:
        this_res = "n/a"

    return this_res