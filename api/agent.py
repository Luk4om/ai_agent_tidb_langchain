import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.vectorstores import TiDBVectorStore
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langgraph.graph import StateGraph, END

load_dotenv()

# --- คอนฟิกความปลอดภัยสำหรับ SSL ---
SSL_CA_CONTENT = os.getenv("TIDB_SSL_CA_CONTENT")
# บังคับใช้ /tmp/ เพื่อให้เขียนไฟล์ได้บน Vercel
ca_path = "/tmp/isrgrootx1.pem" 

if SSL_CA_CONTENT:
    with open(ca_path, "w") as f:
        f.write(SSL_CA_CONTENT)

TIDB_CONNECTION_STRING = os.getenv("TIDB_CONNECTION_STRING")

# --- โหลดโมเดล ---
llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=os.getenv("GROQ_API_KEY"))
embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    model="sentence-transformers/all-MiniLM-L6-v2"
)

# --- ตั้งค่าฐานข้อมูล ---
# ต้องส่ง ca_path เข้าไปใน engine ด้วย
engine = create_engine(
    TIDB_CONNECTION_STRING, 
    connect_args={"ssl": {"ca": ca_path, "ssl-mode": "REQUIRED"}}
)

vector_store = TiDBVectorStore(
    connection_string=TIDB_CONNECTION_STRING,
    embedding_function=embeddings,
    table_name="langchain_agent_memory",
    distance_strategy="cosine"
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# --- Nodes ---

def vector_search(state):
    query = state["question"]
    docs = retriever.invoke(query)
    context = "\n".join([doc.page_content.strip() for doc in docs]) if docs else "ไม่พบข้อมูล"
    return {**state, "raw_data": context}

def extract_course_code(state):
    query = state["question"]
    docs = retriever.invoke(query)
    for doc in docs:
        if "course_code" in doc.metadata:
            return {**state, "course_code": doc.metadata["course_code"]}
    return {**state, "course_code": None}

def sql_lookup(state):
    code = (state.get("course_code") or "").upper()
    if not code: return {**state, "raw_data": "ไม่พบรหัสวิชา"}
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT course_code, name, fee, capacity, enrolled FROM courses WHERE UPPER(course_code)=:code"), 
            {"code": code}
        ).fetchone()
        if result:
            row_code, name, fee, capacity, enrolled = result
            data = f"รหัส: {row_code}, ชื่อ: {name}, ค่าเรียน: {fee} บาท, ที่นั่ง: {enrolled}/{capacity}"
            return {**state, "raw_data": data}
    return {**state, "raw_data": "ไม่พบข้อมูลรายวิชานี้ในระบบฐานข้อมูล"}

def greet_node(state):
    return {**state, "raw_data": "สวัสดีครับ ผม AI ผู้ช่วยคอยแนะนำรายวิชาครับ"}

def generate_answer(state):
    """รวบรวมข้อมูลดิบมาตอบให้เป็นธรรมชาติ"""
    query = state["question"]
    raw_data = state.get("raw_data", "")
    
    prompt = f"""
    จงตอบคำถามผู้ใช้โดยใช้ข้อมูลที่ให้มาเท่านั้น ให้ตอบเป็นภาษาไทยที่สุภาพและเป็นธรรมชาติ
    คำถาม: "{query}"
    ข้อมูล: "{raw_data}"
    คำตอบ:
    """
    response = llm.invoke(prompt).content.strip()
    return {"response": response}

def llm_router_tool(state):
    query = state["question"]
    prompt = f"ตอบเพียงคำเดียว (greet, sql, search): {query}"
    res = llm.invoke(prompt).content.strip().lower()
    if any(k in res for k in ["sql", "price", "ราคา", "รหัส"]): return "sql"
    if any(k in res for k in ["greet", "สวัสดี"]): return "greet"
    return "search"

# --- Graph ---
graph = StateGraph(state_schema=dict)
graph.add_node("vector_search", vector_search)
graph.add_node("extract_code", extract_course_code)
graph.add_node("sql_lookup", sql_lookup)
graph.add_node("greet_node", greet_node)
graph.add_node("generate_answer", generate_answer)

graph.set_entry_point("greet_node")
graph.add_conditional_edges("greet_node", llm_router_tool, {
    "search": "vector_search",
    "sql": "extract_code",
    "greet": "generate_answer"
})

graph.add_edge("vector_search", "generate_answer")
graph.add_edge("extract_code", "sql_lookup")
graph.add_edge("sql_lookup", "generate_answer")
graph.add_edge("generate_answer", END)

app = graph.compile()