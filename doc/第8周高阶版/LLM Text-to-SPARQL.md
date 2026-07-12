
---

# 从「规则映射」升级为「LLM Text-to-SPARQL」（第8周高阶版）

这部分解决的核心问题是：  
> ❌ 原来：人工 if-else 匹配问题  
> ✅ 现在：让 LLM **直接读懂问题 → 生成合法 SPARQL**

---

## 一、设计思路（先看这个，很重要）

我们采用 **Two-step Pipeline**：

```
自然语言问题
     ↓
Prompt 1：LLM 生成 SPARQL
     ↓
Fuseki 执行 SPARQL
     ↓
Prompt 2：LLM 根据 JSON 结果生成自然语言回答
```

✅ **为什么不直接让 LLM 回答？**  
因为 LLM 会“瞎编”。  
✅ **为什么还要第二次 LLM？**  
因为 SPARQL 返回的是 JSON，人看不懂。

---

## 二、给 LLM 的「SPARQL 生成 Prompt」（核心资产）

这个 Prompt 是你整个系统的灵魂，**请务必收藏**。

### ✅ SPARQL 生成 Prompt（可直接复制）

```text
你是一个 SPARQL 专家。请根据用户的问题和给定的本体定义，生成合法的 SPARQL 1.1 查询语句。

【本体前缀】
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

【核心类】
- uni:Person
- uni:Student
- uni:Teacher
- uni:Course
- uni:Department

【核心属性】
- uni:hasName (数据属性，xsd:string)
- uni:hasAge (数据属性，xsd:int)
- uni:teaches (Teacher → Student)
- uni:enrolledIn (Student → Course)
- uni:offeredBy (Course → Department)

【严格要求】
1. 只使用上述本体中的类、属性和前缀。
2. 输出必须是合法的 SPARQL，不要包含注释、解释或自然语言。
3. 如果问题无法用上述本体回答，请输出：ERROR: 无法生成合法SPARQL
4. 变量名要有语义，如 ?teacher, ?course, ?studentName。
5. 使用 SELECT 查询，并返回人类可读的字段。

【用户问题】
{{QUESTION}}

【SPARQL】
```

📌 **使用方式**：把用户问题填到 `{{QUESTION}}` 位置即可。

---

## 三、新版 `kg_qa_llm.py`（完整可运行代码）

> ✅ 旧的规则映射函数被彻底替换  
> ✅ 新增 `generate_sparql()`  
> ✅ 保留 `ask_llm()` 用于最终回答

```python
import requests
import json

# ===============================
# 配置区
# ===============================

FUSEKI_URL = "http://localhost:3030/university/query"

LLM_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
LLM_API_URL = "https://api.openai.com/v1/chat/completions"
LLM_MODEL = "gpt-3.5-turbo"

# ===============================
# LLM 调用封装
# ===============================

def chat_llm(prompt: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是知识图谱与SPARQL专家。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(LLM_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ===============================
# SPARQL 生成
# ===============================

SPARQL_GEN_PROMPT = """你是一个 SPARQL 专家。请根据用户的问题和给定的本体定义，生成合法的 SPARQL 1.1 查询语句。

【本体前缀】
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

【核心类】
uni:Person, uni:Student, uni:Teacher, uni:Course, uni:Department

【核心属性】
uni:hasName, uni:hasAge, uni:teaches, uni:enrolledIn, uni:offeredBy

【严格要求】
1. 只使用上述本体中的类、属性和前缀。
2. 输出必须是合法的 SPARQL，不要包含注释、解释或自然语言。
3. 如果问题无法用上述本体回答，请输出：ERROR: 无法生成合法SPARQL
4. 变量名要有语义，如 ?teacher, ?course, ?studentName。
5. 使用 SELECT 查询。

【用户问题】
{prompt}

【SPARQL】
"""

def generate_sparql(question: str) -> str:
    prompt = SPARQL_GEN_PROMPT.replace("{prompt}", question)
    sparql = chat_llm(prompt)

    if sparql.strip().startswith("ERROR"):
        raise ValueError("LLM 无法生成合法 SPARQL")

    return sparql.strip()

# ===============================
# Fuseki 查询
# ===============================

def run_sparql(query: str) -> dict:
    response = requests.post(
        FUSEKI_URL,
        data={"query": query},
        headers={"Accept": "application/json"}
    )
    response.raise_for_status()
    return response.json()

# ===============================
# 自然语言回答
# ===============================

def answer_from_results(question: str, kg_json: dict) -> str:
    context = json.dumps(kg_json, indent=2, ensure_ascii=False)

    prompt = f"""你是大学知识助手。请根据以下知识库查询结果回答问题。

【查询结果】
{context}

【问题】
{question}

【要求】
1. 仅基于上述结果回答，严禁编造。
2. 若无结果，请明确说“未查询到相关信息”。
3. 回答简洁、正式。
"""

    return chat_llm(prompt)

# ===============================
# 主流程
# ===============================

def main():
    print("=== University Text-to-SPARQL Demo ===")
    question = input("请输入问题：\n> ")

    try:
        sparql = generate_sparql(question)
        print("\n✅ LLM 生成 SPARQL：\n" + sparql)

        result = run_sparql(sparql)
        print("✅ Fuseki 查询成功")

        answer = answer_from_results(question, result)
        print("\n=== 回答 ===")
        print(answer)

    except Exception as e:
        print(f"\n❌ 错误：{e}")

if __name__ == "__main__":
    main()
```

---

## 四、运行效果示例（真实可用）

### 输入
```
> Alice 教的学生都选了哪些课？
```

### LLM 生成的 SPARQL（示例）
```sparql
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?course ?courseName
WHERE {
  ?teacher rdf:type uni:Teacher ;
           uni:hasName "Alice" ;
           uni:teaches ?student .

  ?student rdf:type uni:Student ;
           uni:enrolledIn ?course .

  ?course uni:hasName ?courseName .
}
```

### 最终回答
```
Alice 教的学生选修了《Artificial Intelligence》和《Knowledge Representation》。
```
