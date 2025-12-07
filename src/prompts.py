system_template_vi = '''Tôi sẽ cung cấp cho bạn một tài liệu bao gồm:
- pre_text: phần văn bản của tài liệu, nằm trước bảng dữ liệu
- table: bảng dữ liệu
- post_text: phần văn bản bổ sung

Dựa vào các thông tin này, bạn cần đưa ra lời giải cho câu hỏi dựa trên các phép toán đã cho.
Các phép toán được định nghĩa như sau:
    - add(x, y): Cộng hai số x và y.
    - subtract(x, y): Trừ số y khỏi số x.
    - multiply(x, y): Nhân hai số x và y.
    - divide(x, y): Chia số x cho số y.
    - table_average(column_name, none): Tính trung bình của một cột trong bảng.
    - table_sum(column_name, none): Tính tổng của một cột trong bảng.
    - table_min(column_name, none): Tìm giá trị nhỏ nhất trong một cột của bảng.
    - table_max(column_name, none): Tìm giá trị lớn nhất trong một cột của bảng.
    - greater(x, y): So sánh hai số x và y, trả về "yes" nếu x lớn hơn y, ngược lại trả về "no".
    - exp(x, y): Tính lũy thừa x mũ y.

*Ví dụ về một chuỗi phép toán*:
Hàng tồn kho cũng tăng mạnh 15% so với đầu năm lên 5.310 tỷ đồng với 18 dự án bất động sản dở dang.
- Hàng tồn kho hiện tại là 5.310 tỷ đồng
- Hàng tồn kho đầu năm = hàng tồn kho hiện tại / (1 + 15%)
Vậy để tính hàng tồn kho đầu năm, cần thực hiện 2 phép toán add và divide:
```add(1, 15%), divide(5310, #0)```

LƯU Ý:
- Các đối số (argument) của phép toán phải được lấy trực tiếp từ tài liệu, bảng dữ liệu hoặc tham chiếu từ các phép toán trước đó. (Ví dụ: 1 tỷ muốn quy ra 1000 triệu thì phải qua phép toán multiply(1, 1000))
- Khi lấy dữ liệu từ bảng, chỉ cần tham chiếu trực tiếp nếu có giá trị cụ thể, không bắt buộc phải dùng table_sum hoặc table_average nếu giá trị đã xác định.
- Đối số thứ hai của các phép toán table_* luôn là None.
- Dữ liệu từ bảng có thể lấy trực tiếp không cần phép toán nếu đã xác định (Ví dụ: table_sum("Tổng cộng", None) có thể thay bằng giá trị cụ thể nếu bảng chỉ có một giá trị)
- Các bảng có tên cột và hàng phải đối chiếu đúng.
  - Ví dụ:
  | FY (Dec) | FY 2015 | FY 2016 | FY 2017 | FY 2018 | FY 2019F |
  | Doanh thu (VNDbn) | 23230 | 28212 | 29710 | 32662 | 32769.5 |
  Thì FY 2017 -> 29710 và FY 2018 -> 32662
- Các phép toán phải viết liền nhau, cách nhau bằng dấu phẩy, và chỉ được sử dụng các phép toán đã cho.
- Các phép toán trong chuỗi phải có liên kết với nhau, nghĩa là kết quả của phép toán trước phải được sử dụng trong phép toán sau.
- Không sử dụng các phép toán lồng nhau. Nếu cần tham chiếu đến kết quả trước, sử dụng #0, #1, #2… để tham chiếu.
- Các giá trị trong bảng được bổ sung thông tin từ pre_text và post_text hãy phân tích kỹ trước khi tham chiếu (Ví dụ: Từ bảng ta có "| số dư tại ngày 31 tháng 12 năm 2013 | $ 177947 |" nhưng post_text nói "tổng số dư trong bảng trên không bao gồm lãi và các khoản phạt", khi tính số dư tại ngày 31 tháng 12 năm 2013 ta phải cộng thêm lãi và các khoản phạt)
- Phân tích kỹ câu hỏi — nó sẽ yêu cầu tính một giá trị cụ thể — và bạn cần đưa ra chuỗi phép toán phù hợp.

Đáp án là một chuỗi các phép toán đúng định dạng để dẫn đến câu trả lời.
Ví dụ: ```add(1, 15%), divide(5310, #0)```
'''

user_template_vi = """
**Hãy suy luận từng bước trả lời câu hỏi dựa vào tài liệu sau:**

Tài liệu:
{pre_text}

{table_md_str}

{post_text}

Câu hỏi: {question}
"""

system_template_en = '''I will provide you with a document containing:
- pre_text: the text part of the document, appearing before the data table
- table: the data table
- post_text: additional text

Based on this information, you need to provide a solution to the question using the defined operations.
The operations are defined as follows:
    - add(x, y): Add two numbers x and y.
    - subtract(x, y): Subtract y from x.
    - multiply(x, y): Multiply x and y.
    - divide(x, y): Divide x by y.
    - table_average(column_name, none): Compute the average of a column in the table.
    - table_sum(column_name, none): Compute the sum of a column in the table.
    - table_min(column_name, none): Find the minimum value in a column of the table.
    - table_max(column_name, none): Find the maximum value in a column of the table.
    - greater(x, y): Compare two numbers x and y, return "yes" if x > y, otherwise "no".
    - exp(x, y): Compute x raised to the power of y.

*Example of an operation sequence*:
Inventory also rose sharply by 15% from the beginning of the year to 5,310 billion VND with 18 ongoing real estate projects.
- Current inventory = 5,310 billion VND
- Beginning-of-year inventory = current inventory / (1 + 15%)
Thus, to calculate the beginning-of-year inventory, we need 2 operations: add and divide:
```add(1, 15%), divide(5310, #0)```

NOTE:
- The arguments of operations must be taken directly from the document, data table, or referenced from previous operations. (Example: to convert 1 billion to 1,000 million, use multiply(1, 1000))
- When taking data from a table, you can reference it directly if a specific value exists; using table_sum or table_average is not required if the value is known.
- The second argument of table_* operations is always None.
- Table data can be used directly without operations if already specified (Example: table_sum("Total", None) can be replaced by the actual value if the table has only one value).
- Column and row names in tables must be correctly matched.
  - Example:
  | FY (Dec) | FY 2015 | FY 2016 | FY 2017 | FY 2018 | FY 2019F |
  | Revenue (VNDbn) | 23230 | 28212 | 29710 | 32662 | 32769.5 |
  Then FY 2017 -> 29710 and FY 2018 -> 32662
- Operations must be written in sequence, separated by commas, and only the defined operations can be used.
- Operations in the sequence must be linked, meaning the result of a previous operation should be used in the next.
- Do not use nested operations. If referencing previous results, use #0, #1, #2… for referencing.
- Values in the table supplemented by pre_text and post_text should be carefully analyzed before referencing. (Example: From the table we have "| balance at Dec 31, 2013 | $177,947 |" but post_text says "the total balance in the table excludes interest and penalties", so when calculating the balance at Dec 31, 2013, you must add interest and penalties.)
- Analyze the question carefully — it will ask for a specific value — and provide a proper sequence of operations.

The answer should be a correctly formatted sequence of operations that leads to the solution.
Example: ```add(1, 15%), divide(5310, #0)```
'''

user_template_en = """
**Please reason step by step to answer the question based on the following document:**  

Document:
{pre_text}

{table_md_str}

{post_text}

Question: {question}
"""


rewrite_sys_template = '''
Nhiệm vụ của bạn là dựa vào toàn bộ tài liệu và câu hỏi gốc, hãy viết lại câu hỏi theo cách rõ ràng, đầy đủ và không mơ hồ tập trung vào nội dung chính của câu hỏi.
Lưu ý:
- Câu hỏi sau khi viết lại chỉ được chứa một yêu cầu tính toán duy nhất không phải là xác định một giá trị nào đó.
- Câu hỏi được viết lại phải làm rõ nội dung cần tính, nêu rõ các đối tượng đề cập nhưng không được thay đổi ý nghĩa gốc.
- Nêu không rõ đối tượng đề cập giữ nguyên từ câu hỏi ban đầu
- Không được trả lời câu hỏi, chỉ được viết lại câu hỏi.
- Không được tự suy luận thêm phép tính, chỉ làm rõ nội dung cần hỏi.

*Ví dụ về viết lại câu hỏi cho rõ nghĩa*:
Câu hỏi gốc:
"Tỷ lệ LNHĐKD (%) của HPG trong năm 2020 dự kiến tăng so với năm 2019 là bao nhiêu?"

Câu hỏi đã viết lại:
-> ```Mức chênh lệch giữa tỷ lệ LNHĐKD (%) năm 2020 dự kiến và tỷ lệ LNHĐKD (%) năm 2019 là bao nhiêu?```

---
Câu hỏi gốc:
"P/E mục tiêu năm 2020 và 2021 lần lượt là bao nhiêu và giảm bao nhiêu lần?"

Câu hỏi đã viết lại:
-> ```P/E mục tiêu trong năm 2020 và 2021 giảm tương ứng bao nhiêu lần?```
'''
rewrite_user_template = '''
Dựa vào bối cảnh sau viết lại câu hỏi.

Tài liệu:
{pre_text}
{table_md_str}
{post_text}

Câu hỏi gốc: {question}

Hãy viết lại câu hỏi không mơ hồ tập trung vào nội dung chính của câu hỏi.
'''
verify_sys_template = '''Tôi sẽ cung cấp cho bạn một tài liệu bao gồm:
- pre_text: phần văn bản của tài liệu, nằm trước bảng dữ liệu
- table: bảng dữ liệu
- post_text: phần văn bản bổ sung

Dựa vào các thông tin này, bạn cần đánh giá xem lời giải cho câu hỏi đã cho có hoàn toàn chính xác hay không.
Các phép toán được định nghĩa như sau:
    - add(x, y): Cộng hai số x và y.
    - subtract(x, y): Trừ số y khỏi số x.
    - multiply(x, y): Nhân hai số x và y.
    - divide(x, y): Chia số x cho số y.
    - table_average(column_name, none): Tính trung bình của một cột trong bảng.
    - table_sum(column_name, none): Tính tổng của một cột trong bảng.
    - table_min(column_name, none): Tìm giá trị nhỏ nhất trong một cột của bảng.
    - table_max(column_name, none): Tìm giá trị lớn nhất trong một cột của bảng.
    - greater(x, y): So sánh hai số x và y, trả về yes nếu x lớn hơn y, ngược lại trả về no.
    - exp(x, y): Tính lũy thừa x mũ y.

LƯU Ý:
- Các đối số (argument) của phép toán phải được lấy trực tiếp từ tài liệu, bảng dữ liệu hoặc tham chiếu từ các phép toán trước đó. (Ví dụ: 1 tỷ muốn quy ra 1000 triệu thì phải qua phép toán multiply(1, 1000))
- Với các phép toán liên quan đến bảng (table operation), đối số thứ hai luôn là None. Khi lấy dữ liệu từ bảng ta chỉ cần tham chiếu thẳng đến số liệu không cần phép toán nào.
- Các phép toán phải được viết liền nhau, cách nhau bằng dấu phẩy, và chỉ được sử dụng các phép toán đã cho ở trên.
- Các phép toán trong chuỗi phải có liên kết với nhau, nghĩa là kết quả của phép toán trước phải được sử dụng trong phép toán sau.
- Không sử dụng các phép toán lồng nhau. Nếu cần tham chiếu đến một phép toán trước đó, hãy sử dụng #0, #1, #2... để tham chiếu đến kết quả của các phép toán đó.
- Các giá trị trong bảng được bổ sung thông tin từ pre_text và post_text hãy phân tích kĩ trước khi tham chiếu (ví dụ: bảng ghi 177,947 nhưng mô tả nói số dư chưa bao gồm lãi/phạt → phải cộng thêm phần lãi/phạt khi tính).

Đáp án là một chuỗi các phép toán đúng định dạng để dẫn đến câu trả lời.
Ví dụ: ```add(1, 15%), divide(5310, #0)```

Nhiệm vụ của bạn:
- Dựa vào tài liệu và câu hỏi gốc, hãy đánh giá xem **lời giải hiện tại** (chuỗi phép toán) có:
  1. Đúng về mặt số liệu tham chiếu,
  2. Đúng về mặt logic,
  3. Đúng về định dạng và quy tắc nêu trên,
  4. Và thực sự dẫn đến đáp án đúng cho câu hỏi hay không.

Bạn phải trả về kết quả dưới dạng JSON với cấu trúc cố định sau:

{
  "comment": "<nhận xét ngắn gọn, mô tả vì sao lời giải đúng hoặc sai>",
  "conclusion": "<Yes hoặc No>"
}

- "comment": mô tả vì sao lời giải đúng hoặc sai (ngắn gọn, rõ ràng).
- "conclusion": 
    - "Yes" nếu lời giải hoàn toàn chính xác.
    - "No" nếu lời giải sai hoặc vi phạm bất kỳ quy tắc nào.

Tuyệt đối không trả về nội dung ngoài JSON.
'''
verify_user_template = '''
Hãy đánh giá độ chính xác của lời giải dựa trên bối cảnh sau:

Tài liệu:
{pre_text}

{table_md_str}

{post_text}

Câu hỏi:
{question}

Câu trả lời được đưa ra:
{model_answer}

Hãy cung cấp đánh giá của bạn đối với lời giải trên.
'''
re_infer_user_template = """
**Hãy suy luận từng bước trả lời câu hỏi dựa vào tài liệu sau:**

Tài liệu:
{pre_text}

{table_md_str}

{post_text}

Câu hỏi: {question}

Câu trả lời được đưa ra:
{model_answer}

Đánh giá:
{comment}

Dựa vào phân tích trước đó đưa ra câu trả lời cho phù hợp. Trả về câu trả lời đúng cuối cùng.
"""

system_template = '''I will provide you with a document that includes:
- pre_text: the text appearing before the data table
- table: the data table
- post_text: the supplementary text appearing after the table

Based on this information, you must produce a **detailed step-by-step analysis** that leads to the correct answer for the given question. Your explanation should justify each operation used and show how it contributes to the final answer.

The available operations are defined as follows:
    - add(x, y): Add numbers x and y.
    - subtract(x, y): Subtract y from x.
    - multiply(x, y): Multiply x and y.
    - divide(x, y): Divide x by y.
    - table_average(column_name, none): Compute the average of a column in the table.
    - table_sum(column_name, none): Compute the sum of a column in the table.
    - table_min(column_name, none): Find the minimum value of a column in the table.
    - table_max(column_name, none): Find the maximum value of a column in the table.
    - greater(x, y): Compare x and y, return "yes" if x is greater than y, otherwise "no".
    - exp(x, y): Compute x to the power of y.

*Example of reasoning for a question*:
Question: What was the beginning inventory value?

The answer must follow this format and include a detailed explanation:

“The inventory increased sharply by 15% from the beginning of the year to 5,310 billion VND, with 18 ongoing real-estate projects.”
- Current inventory is 5,310 billion VND.
- Beginning inventory = current inventory / (1 + 15%)

To calculate the beginning inventory, the required operations are add and divide:
```add(1, 15%), divide(5310, #0)```

The final answer for the question is:
```add(1, 15%), divide(5310, #0)```

**Important:** The answer must include:
1. Perform a thorough analysis of the question, clearly identifying exactly what is being asked and what the final result should represent.  
2. Identify all relevant data and numerical values from the document that are necessary for the calculations, **and explain in detail why each value is chosen and how it relates to the question**.  
3. Provide a step-by-step reasoning for each calculation, showing how each operation is applied, how intermediate results are derived, and why these steps are logically necessary to reach the answer.  
4. Justify how each operation and calculation contributes to the final result, ensuring that the explanation connects the data, the operations, and the conclusion in a clear and detailed manner.
'''

user_template = """
**Reason step-by-step to answer the question based on the following document.**
The answer must be in English.

Document:
{pre_text}

{table_md_str}

{post_text}

Question: {question}
Answer: {program}
"""

system_template_verify = '''I will provide you with a document that includes:
- pre_text: the text appearing before the data table
- table: the data table
- post_text: the supplementary text appearing after the table

Based on this information and the computed program/answer, you must produce a **verification of the answer**, explaining clearly why the final answer is correct based on the data and operations.  
Focus only on confirming the correctness of the result, not on reproducing the initial step-by-step calculation.

The available operations are defined as follows:
    - add(x, y): Add numbers x and y.
    - subtract(x, y): Subtract y from x.
    - multiply(x, y): Multiply x and y.
    - divide(x, y): Divide x by y.
    - table_average(column_name, none): Compute the average of a column in the table.
    - table_sum(column_name, none): Compute the sum of a column in the table.
    - table_min(column_name, none): Find the minimum value of a column in the table.
    - table_max(column_name, none): Find the maximum value of a column in the table.
    - greater(x, y): Compare x and y, return "yes" if x is greater than y, otherwise "no".
    - exp(x, y): Compute x to the power of y.

**Important:** The verification must include:
1. Identify the relevant data in the document that supports the answer.
2. Check that each operation in the program correctly applies to the chosen data.
3. Confirm that the final computed value is consistent with the data and logic.
4. Clearly explain why the answer is valid and accurate.
'''

user_template_verify = """
**Verify the correctness of the answer based on the following document.**
The answer must be in English.

Document:
{pre_text}

{table_md_str}

{post_text}

Question: {question}
Program: {program}

Verification:
"""

system_template_summary = '''I will provide you with a document that includes:
- pre_text: the text appearing before the data table
- table: the data table
- post_text: the supplementary text appearing after the table

Your task is to produce a **concise summary** of the document **focusing only on the information relevant to the given question and the computed answer/program**.

The summary should:
1. Extract only the key facts from the document that are necessary to understand or answer the question.
2. Ignore unrelated narrative details, disclaimers, or formatting text.
3. Highlight the specific data points or table fields that the question and program rely on.
4. Present the summary in clear and concise English (no more than a short paragraph unless needed).

Do **not** verify correctness, do **not** explain the steps of the program, and do **not** restate the full document.  
Focus purely on filtering the document down to the most relevant information for the question.
'''

user_template_summary = """**Provide a concise relevance-focused summary of the document.**
The summary must be in English.

Document:
{pre_text}

{table_md_str}

{post_text}

Question: {question}
Program: {program}

Summary:
"""

