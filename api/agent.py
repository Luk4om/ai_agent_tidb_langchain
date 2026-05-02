import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.vectorstores import TiDBVectorStore
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from duckduckgo_search import DDGS
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
# ใช้ DDGS โดยตรงไม่ต้องผ่าน LangChain Tool

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

def web_search(state):
    """ค้นหาข้อมูลจากอินเทอร์เน็ตโดยใช้ DDGS โดยตรง"""
    query = state["question"]
    print(f"--- Web Searching for: {query} ---")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=5)]
            if results:
                context = "\n".join([f"หัวข้อ: {r['title']}\nเนื้อหา: {r['body']}" for r in results])
                return {**state, "raw_data": f"ข้อมูลจากเว็บ:\n{context}"}
    except Exception as e:
        print(f"Web Search Error: {e}")
    
    return {**state, "raw_data": "ไม่พบข้อมูลจากอินเทอร์เน็ต"}

def check_relevance(state):
    """ตรวจสอบว่าข้อมูลที่หามาได้เพียงพอที่จะตอบคำถามหรือไม่"""
    query = state["question"]
    raw_data = state.get("raw_data", "")
    
    if not raw_data or "ไม่พบข้อมูล" in raw_data:
        return "not_relevant"
        
    prompt = f"""
    คุณเป็นผู้ตรวจสอบข้อมูล จงตอบเพียงคำเดียว 'yes' หรือ 'no'
    ข้อมูลนี้เพียงพอที่จะตอบคำถาม: "{query}" หรือไม่?
    ข้อมูล: "{raw_data}"
    คำตอบ (yes/no):
    """
    res = llm.invoke(prompt).content.strip().lower()
    return "relevant" if "yes" in res else "not_relevant"

def llm_router_tool(state):
    """วิเคราะห์คำถามว่าจะตอบเลย, ใช้ SQL, หรือใช้ RAG/Web Search"""
    query = state["question"]
    prompt = f"""
    วิเคราะห์คำถาม: "{query}"
    ตอบเพียงคำเดียว:
    - 'greet' ถ้าเป็นคำถามทั่วไปที่คุณสามารถตอบได้ทันทีโดยไม่ต้องค้นหา (เช่น สวัสดี, คุณคือใคร, 1+1 ได้เท่าไหร่)
    - 'sql' ถ้าถามหาราคา, รหัสวิชา, หรือจำนวนที่นั่งของวิชาเรียน
    - 'rag' ถ้าเป็นคำถามเกี่ยวกับเนื้อหาวิชาหรือความรู้อื่นๆ ที่ต้องใช้การค้นหา
    
    คำตอบ:
    """
    res = llm.invoke(prompt).content.strip().lower()
    
    if "sql" in res or any(k in query for k in ["ราคา", "ค่าเรียน", "ที่นั่ง", "รหัส"]): 
        return "sql"
    if "greet" in res or any(k in query for k in ["สวัสดี", "ใคร"]): 
        return "greet"
    return "rag"

# --- Graph ---
graph = StateGraph(state_schema=dict)
graph.add_node("vector_search", vector_search)
graph.add_node("extract_code", extract_course_code)
graph.add_node("sql_lookup", sql_lookup)
graph.add_node("greet_node", greet_node)
graph.add_node("web_search", web_search)
graph.add_node("generate_answer", generate_answer)

graph.set_entry_point("greet_node")

graph.add_conditional_edges("greet_node", llm_router_tool, {
    "rag": "vector_search",
    "sql": "extract_code",
    "greet": "generate_answer"
})

graph.add_conditional_edges("vector_search", check_relevance, {
    "relevant": "generate_answer",
    "not_relevant": "web_search"
})

graph.add_edge("web_search", "generate_answer")
graph.add_edge("extract_code", "sql_lookup")
graph.add_edge("sql_lookup", "generate_answer")
graph.add_edge("generate_answer", END)

app = graph.compile()