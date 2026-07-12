import requests
import json

import read_config as conf


config = conf.ConfigManager().load()

ai_config = config.get("ai_api_list", {})

MODEL_NAME = "ds_flash" # 选择模型

# ===============================
# 配置区（你只需要改这里）
# ===============================

FUSEKI_URL = "http://localhost:3030/university/query"

# DeepSeek
LLM_API_KEY = ai_config.get(MODEL_NAME).get("apiKey")
LLM_API_URL = ai_config.get(MODEL_NAME).get("base_url")
LLM_MODEL = ai_config.get(MODEL_NAME).get("model_name")

# print(ai_config)
# print(LLM_MODEL)
# print( LLM_API_URL)
# print(  LLM_API_KEY)

# 如果是 DeepSeek / 智谱 / 千问，只需换 URL 和 Key

# ===============================
# SPARQL 查询加载
# ===============================

def load_sparql(file_path: str) -> str:
    """读取 SPARQL 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# ===============================
# Fuseki 查询
# ===============================

def run_sparql(query: str) -> dict:
    """向 Fuseki 发送 SPARQL 查询"""
    response = requests.post(
        FUSEKI_URL,
        data={"query": query},
        headers={"Accept": "application/json"}
    )
    response.raise_for_status()
    return response.json()

# ===============================
# LLM 调用
# ===============================

def ask_llm(context: str, question: str) -> str:
    """调用大模型生成自然语言回答"""
    prompt = f"""
你是一个大学知识助手。请根据以下知识库查询结果，用简洁、准确的中文回答问题。

【知识库查询结果】
{context}

【问题】
{question}

【要求】
1. 仅基于上述知识回答，不要编造信息
2. 如果没有相关信息，请明确说“未查询到相关信息”
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是知识图谱问答助手。"},
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
    result = response.json()

    return result["choices"][0]["message"]["content"]

# ===============================
# 意图映射（简化版 NLU）
# ===============================

def map_question_to_sparql(question: str) -> str:
    """
    将自然语言问题映射到 SPARQL 文件
    这是一个规则式示例，后续可替换为 LLM 意图识别
    """
    q = question.lower()

    if "alice" in q and ("教" in q or "课程" in q):
        return load_sparql("sparql/courses_by_teacher.rq")

    if "学生" in q and "课程" in q:
        return load_sparql("sparql/students_by_course.rq")

    if "alice" in q and ("年龄" in q or "多大" in q):
        return load_sparql("sparql/teacher_info.rq")

    raise ValueError("暂不支持该问题类型，请扩展意图映射规则。")

# ===============================
# 主流程
# ===============================

def main():
    print("=== University 知识图谱问答 Demo ===")
    question = input("请输入你的问题：\n> ")

    try:
        # 1. 意图 → SPARQL
        sparql_query = map_question_to_sparql(question)
        print("\n✅ 已匹配 SPARQL 查询")

        # 2. 查询 Fuseki
        kg_result = run_sparql(sparql_query)
        print("✅ Fuseki 查询成功")

        # 3. 格式化 KG 结果
        kg_context = json.dumps(kg_result, indent=2, ensure_ascii=False)

        # 4. LLM 生成回答
        answer = ask_llm(kg_context, question)

        print("\n=== 回答 ===")
        print(answer)

    except Exception as e:
        print(f"\n❌ 出错了：{e}")

if __name__ == "__main__":
    main()

    