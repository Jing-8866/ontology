import requests
import json

# ===============================
# 配置区
# ===============================

FUSEKI_URL = "http://localhost:3030/university/query"

# DeepSeek
LLM_API_KEY = "sk-127e7acf2d444c1486abf3a069f044f8"
LLM_API_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-v4-flash"

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