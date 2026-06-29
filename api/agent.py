import os
import tempfile
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.vectorstores import TiDBVectorStore
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langgraph.graph import StateGraph, END

load_dotenv()

# --- คอนฟิกความปลอดภัยสำหรับ SSL ---
SSL_CA_CONTENT = os.getenv("TIDB_SSL_CA_CONTENT")
ca_path = os.path.join(tempfile.gettempdir(), "isrgrootx1.pem")

if SSL_CA_CONTENT:
    try:
        with open(ca_path, "w", encoding="utf-8") as f:
            f.write(SSL_CA_CONTENT)
    except Exception as e:
        print(f"Warning: Failed to write SSL_CA_CONTENT to {ca_path}: {e}")

# Fallback: หากไม่มีเนื้อหาไฟล์ CA ใน Env หรือบันทึกไม่สำเร็จ ให้ใช้ไฟล์ใน root ของโปรเจกต์
if not os.path.exists(ca_path):
    local_ca = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "isrgrootx1.pem"))
    if os.path.exists(local_ca):
        ca_path = local_ca

TIDB_CONNECTION_STRING = os.getenv("TIDB_CONNECTION_STRING")

# --- โหลดโมเดล ---
llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=os.getenv("GROQ_API_KEY"))
embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
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
    # 1. พยายามหาด้วย regex ก่อน (เช่น CS101, cs 102)
    match = re.search(r'\bCS[- ]?(\d{3})\b', query, re.IGNORECASE)
    if match:
        code = f"CS{match.group(1)}"
        return {**state, "course_code": code}
    
    # 2. หากหาไม่เจอ ให้โมเดลช่วยสกัดความต้องการรหัสวิชา
    try:
        prompt = f"ระบุรหัสวิชาที่เป็นภาษาอังกฤษ (เช่น CS101) จากคำถามต่อไปนี้ หากไม่มีในคำถาม ให้ตอบกลับคำว่า None เพียงอย่างเดียว: {query}"
        res = llm.invoke(prompt).content.strip()
        match = re.search(r'\bCS[- ]?(\d{3})\b', res, re.IGNORECASE)
        if match:
            code = f"CS{match.group(1)}"
            return {**state, "course_code": code}
    except Exception:
        pass
        
    return {**state, "course_code": None}

def sql_lookup(state):
    code = (state.get("course_code") or "").upper()
    if not code: return {**state, "raw_data": "ไม่พบรหัสวิชา"}
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT course_code, name, description, fee, capacity, enrolled FROM courses WHERE UPPER(course_code)=:code"), 
            {"code": code}
        ).fetchone()
        if result:
            row_code, name, desc, fee, capacity, enrolled = result
            data = f"รหัส: {row_code}, ชื่อ: {name}, รายละเอียดวิชา: {desc}, ค่าเรียน: {fee} บาท, ที่นั่ง: {enrolled}/{capacity}"
            return {**state, "raw_data": data}
    return {**state, "raw_data": "ไม่พบข้อมูลรายวิชานี้ในระบบฐานข้อมูล"}

def greet_node(state):
    return {**state, "raw_data": "สวัสดีครับ ผม AI ผู้ช่วยคอยแนะนำรายวิชาครับ"}

def web_search(state):
    """ค้นหาข้อมูลจากอินเทอร์เน็ตโดยใช้ DDGS โดยตรง (มีระบบแปลคำค้นหาเป็นภาษาอังกฤษอัตโนมัติเพื่อผลลัพธ์ที่แม่นยำ)"""
    query = state["question"]
    search_query = query
    
    # 1. แปลคำถามภาษาไทยเป็นอังกฤษเพื่อความแม่นยำในการค้นหาเว็บ
    try:
        translate_prompt = f"""
        Translate the following Thai search query into a concise English search term suitable for search engines.
        Respond ONLY with the translated English search term, no quotes, no explanation.

        Query: "{query}"
        English Search Term:
        """
        english_term = llm.invoke(translate_prompt).content.strip()
        if english_term and len(english_term) > 2:
            search_query = english_term
    except Exception:
        pass

    # 2. ค้นหาใน DuckDuckGo
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=3))
            if results:
                context = "\n".join([f"หัวข้อ/Title: {r['title']}\nเนื้อหา/Snippet: {r['body']}" for r in results])
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
    คุณเป็นผู้ตรวจสอบข้อมูล จงตอบเพียงคำเดียว 'yes' หรือ 'no' เท่านั้น
    ข้อมูลนี้มีความเกี่ยวข้องและเพียงพอที่จะตอบคำถาม: "{query}" หรือไม่?
    ข้อมูลที่หาได้: "{raw_data}"
    คำตอบ (yes/no):
    """
    try:
        res = llm.invoke(prompt).content.strip().lower()
        if "yes" in res:
            return "relevant"
    except Exception:
        pass
    return "not_relevant"

def generate_answer(state):
    """รวบรวมข้อมูลดิบมาตอบให้เป็นธรรมชาติ"""
    query = state["question"]
    raw_data = state.get("raw_data", "")
    
    prompt = f"""
    คำถาม: "{query}"
    ข้อมูลอ้างอิง: "{raw_data}"
    
    บทบาท: คุณคือ AI ผู้ช่วยผู้มีความรอบรู้ แนะนำรายวิชาเรียน และตอบคำถามทั่วไปได้
    กติกาการตอบภาษาไทย:
    1. หากข้อมูลอ้างอิงมีเนื้อหาที่เกี่ยวข้องกับวิชาเรียนหรือคำถาม ให้ใช้ข้อมูลอ้างอิงนั้นมาเป็นข้อมูลหลักในการอธิบายคำตอบ
    2. หากข้อมูลอ้างอิงระบุว่า "ไม่พบข้อมูลจากอินเทอร์เน็ต" หรือ "ไม่พบข้อมูล" หรือเป็นข้อมูลที่ว่างเปล่า/ไม่เกี่ยวข้องกับคำถามเลย ให้คุณใช้ความรู้ทั่วไปของตนเอง (General Knowledge) ตอบคำถามให้ถูกต้องที่สุดและเป็นประโยชน์แก่ผู้ใช้ แทนการตอบปฏิเสธ
    3. ตอบเป็นภาษาไทยด้วยความสุภาพ เป็นธรรมชาติ และเป็นกันเอง
    
    คำตอบ:
    """
    response = llm.invoke(prompt).content.strip()
    return {"response": response}

def llm_router_tool(state):
    query = state["question"]
    prompt = f"""
    คุณเป็นผู้ช่วยระบบจัดเส้นทางคำถาม (Router)
    หน้าที่ของคุณคือแยกประเภทคำถามของผู้ใช้แล้วตอบด้วยคำสำคัญเพียงคำเดียวเท่านั้น:
    - ตอบ 'greet' หากเป็นการทักทายทั่วไป (เช่น สวัสดี, สบายดีไหม)
    - ตอบ 'sql' หากเป็นคำถามที่ต้องการค้นหาข้อมูลเฉพาะ เช่น ราคา, ค่าธรรมเนียม, จำนวนที่นั่ง, ความจุ, จำนวนผู้ลงทะเบียนเรียน, หรือถามเรื่องราคาของรหัสวิชานั้นๆ
    - ตอบ 'search' หากเป็นการถามรายละเอียดเกี่ยวกับวิชาว่าเรียนอะไรบ้าง, แนะนำวิชา, หรือต้องการข้อมูลเชิงวิชาการ/เนื้อหารายละเอียดวิชา
    
    คำถาม: "{query}"
    คำตอบ (ตอบคำเดียวกด: greet, sql, search):
    """
    try:
        res = llm.invoke(prompt).content.strip().lower()
        if "sql" in res:
            return "sql"
        if "greet" in res:
            return "greet"
        return "search"
    except Exception:
        return "search"

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
    "search": "vector_search",
    "sql": "extract_code",
    "greet": "generate_answer"
})

# เช็คความเกี่ยวข้องของข้อมูล หากไม่เกี่ยวหรือไม่เพียงพอ ให้ไป Web Search
graph.add_conditional_edges("vector_search", check_relevance, {
    "relevant": "generate_answer",
    "not_relevant": "web_search"
})

graph.add_edge("web_search", "generate_answer")
graph.add_edge("extract_code", "sql_lookup")
graph.add_edge("sql_lookup", "generate_answer")
graph.add_edge("generate_answer", END)

app = graph.compile()