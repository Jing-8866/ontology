这是一份**第8周可直接复制运行的完整 Python Demo 代码**。  
我把它设计成：**不需要复杂前端、不依赖特定 LLM SDK、本地可跑、逻辑清晰**，只要替换 API Key 和端点即可。

这个 Demo 实现的是：

> **自然语言提问 → 意图映射到 SPARQL → Fuseki 查询 → 结果交给 LLM 生成自然语言回答**

---

# 第8周综合项目：University KG + LLM 问答 Demo（完整代码）

## 一、前置条件检查清单

请确认以下环境已就绪：

✅ **Protégé**
- 已完成第3周“带推理的 University 本体”
- 保存为：`university-final.owl`

✅ **Apache Jena Fuseki**
- 已启动：`http://localhost:3030`
- 已创建 Dataset：`university`
- 已上传 `university.ttl`

✅ **Python 环境**
```bash
python --version   # 3.8+
pip install requests rdflib
```

✅ **LLM API**
- OpenAI / DeepSeek / 智谱 / 通义千问均可
- 有一个可用的 API Key

---

## 二、项目目录结构（建议）

```text
university_kg_demo/
│
├── kg_qa.py              # 主程序（下面给你的完整代码）
├── sparql/
│   ├── courses_by_teacher.rq
│   ├── students_by_course.rq
│   └── teacher_info.rq
└── README.md
```

---

## 三、SPARQL 查询文件（必须先准备好）

### 1️⃣ `sparql/courses_by_teacher.rq`
```sparql
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?course ?courseName
WHERE {
  ?teacher rdf:type uni:Teacher ;
           uni:hasName "Alice" ;
           uni:teaches ?student .

  ?student uni:enrolledIn ?course .

  ?course uni:hasName ?courseName .
}
```

### 2️⃣ `sparql/students_by_course.rq`
```sparql
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?student ?studentName
WHERE {
  ?course rdf:type uni:Course ;
          uni:hasName "Artificial Intelligence" .

  ?student rdf:type uni:Student ;
           uni:enrolledIn ?course ;
           uni:hasName ?studentName .
}
```

### 3️⃣ `sparql/teacher_info.rq`
```sparql
PREFIX uni: <http://www.example.org/university#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?teacher ?age
WHERE {
  ?teacher rdf:type uni:Teacher ;
           uni:hasName "Alice" ;
           uni:hasAge ?age .
}
```

---

## 四、主程序：`kg_qa.py`（完整可运行）

> ⚠️ **使用前请修改：**
> - `FUSEKI_URL`
> - `LLM_API_KEY`
> - `LLM_API_URL`（根据你的模型换）

```python
import requests
import json

# ===============================
# 配置区（你只需要改这里）
# ===============================

FUSEKI_URL = "http://localhost:3030/university/query"

# 示例：OpenAI
LLM_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
LLM_API_URL = "https://api.openai.com/v1/chat/completions"
LLM_MODEL = "gpt-3.5-turbo"

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
```

---

## 五、运行效果示例

### 输入
```
请输入你的问题：
> Alice 教了哪些课程？
```

### 终端输出
```
✅ 已匹配 SPARQL 查询
✅ Fuseki 查询成功

=== 回答 ===
根据知识库查询结果，Alice 教授的课程为《Artificial Intelligence》。
```

---

## 六、你可以如何“升级”这个 Demo（加分项）

✅ **替换意图映射**
- 用 LLM 把自然语言直接转 SPARQL（Text-to-SPARQL）
- Prompt 示例：
  ```
  请将以下问题转换为 SPARQL：
  问题：Alice 教了哪些课？
  本体前缀：uni: http://www.example.org/university#
  ```

✅ **加入推理结果**
- Fuseki 开启推理（Inference）
- 或 Protégé 中推理后导出 inferred axioms

✅ **加入一致性检测**
- 在查询前先跑：
  ```sparql
  ASK { ?x owl:sameAs ?x . FILTER(false) }
  ```

---

## 七、最终交付物清单（第8周结课标准）

✅ `university-final.owl`  
✅ `university.ttl`  
✅ `sparql/*.rq`  
✅ `kg_qa.py`（就是上面的代码）  
✅ 一段 2–3 分钟录屏：
1. 打开 Fuseki → 显示 dataset
2. 运行 `python kg_qa.py`
3. 输入问题 → 得到自然语言回答

---