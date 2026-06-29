import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.vectorstores import TiDBVectorStore
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_core.documents import Document

load_dotenv()

# ใช้ Embedding ตัวเดียวกับ agent.py
embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
tidb_connection_string = os.getenv("TIDB_CONNECTION_STRING")

def get_tidb_vector_store() -> TiDBVectorStore:
    return TiDBVectorStore(
        connection_string=tidb_connection_string,
        embedding_function=embeddings,
        table_name="langchain_agent_memory",
        distance_strategy="cosine"
    )

def ingest_courses_to_memory():
    # ลบตารางเดิมทิ้ง (เพื่อรีเซ็ตขนาด Vector จาก 1024 เป็น 384)
    try:
        engine = create_engine(tidb_connection_string)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS langchain_agent_memory"))
            conn.commit()
        print("Table dropped to reset dimensions.")
    except Exception as e:
        print(f"Cleanup error: {e}")

    vector_store = get_tidb_vector_store()
    
    docs = [
        Document(page_content="CS101 วิชา 'ปัญญาประดิษฐ์' เรียนรู้พื้นฐานของ AI, Machine Learning และ Deep Learning โดยใช้ Python, TensorFlow และ Scikit-Learn", metadata={"course_code": "CS101"}),
        Document(page_content="CS102 วิชา 'พัฒนาเว็บไซต์' สอนการสร้างเว็บไซต์ตั้งแต่ HTML, CSS ไปจนถึง JavaScript, React, Node.js และ REST API", metadata={"course_code": "CS102"}),
        Document(page_content="CS103 วิชา 'วิทยาการข้อมูล' เจาะลึกการวิเคราะห์ข้อมูลด้วย Python, Pandas, Numpy และเบื้องต้นของ Machine Learning", metadata={"course_code": "CS103"}),
        Document(page_content="CS104 วิชา 'พัฒนาแอปมือถือ' พัฒนาแอปบน Android และ iOS ด้วย Flutter และ Dart ครอบคลุม UI, State management และการเชื่อมต่อ backend", metadata={"course_code": "CS104"}),
        Document(page_content="CS105 วิชา 'ความมั่นคงไซเบอร์เบื้องต้น' เรียนรู้พื้นฐานด้าน cybersecurity เช่น การเข้ารหัส, Malware, Phishing และแนวทางป้องกัน", metadata={"course_code": "CS105"}),
        Document(page_content="CS106 วิชา 'การประมวลผลบนคลาวด์' แนะนำระบบ Cloud เช่น AWS, GCP รวมถึงแนวคิด IaaS, PaaS และ SaaS อย่างเป็นระบบ", metadata={"course_code": "CS106"}),
        Document(page_content="CS107 วิชา 'อินเทอร์เน็ตของสรรพสิ่ง (IoT)' เรียนรู้การเชื่อมต่ออุปกรณ์ เช่น Arduino และ ESP32 กับอินเทอร์เน็ต พร้อมเก็บข้อมูลบนคลาวด์", metadata={"course_code": "CS107"}),
        Document(page_content="CS108 วิชา 'เทคโนโลยีบล็อกเชน' เข้าใจโครงสร้าง Blockchain และฝึกเขียน Smart Contract ด้วยภาษา Solidity", metadata={"course_code": "CS108"}),
        Document(page_content="CS109 วิชา 'จริยธรรมในปัญญาประดิษฐ์' พิจารณาแง่มุมของ Bias, Fairness และ Privacy ในระบบ AI และการประยุกต์ใช้อย่างมีจริยธรรม", metadata={"course_code": "CS109"}),
        Document(page_content="CS110 วิชา 'การออกแบบ UX/UI' สอนแนวคิดในการออกแบบประสบการณ์ผู้ใช้ (UX) และอินเทอร์เฟซ (UI) โดยใช้เครื่องมืออย่าง Figma และ Adobe XD", metadata={"course_code": "CS110"}),
        Document(page_content="CS111 วิชา 'วิศวกรรมข้อมูล (Data Engineering)' เน้นการสร้างและจัดการ Data Pipeline การใช้ SQL ขั้นสูง, Apache Airflow และการวางโครงสร้าง Data Warehouse", metadata={"course_code": "CS111"}),
        Document(page_content="CS112 วิชา 'พื้นฐาน DevOps' เรียนรู้การทำ CI/CD, การใช้งาน Docker Containers และการจัดการ Cluster ด้วย Kubernetes สำหรับระบบที่ขยายตัวได้", metadata={"course_code": "CS112"}),
        Document(page_content="CS113 วิชา 'ภาษา SQL สำหรับการวิเคราะห์' เจาะลึกการดึงข้อมูลและจัดการฐานข้อมูลขนาดใหญ่ (Big Data) ด้วย PostgreSQL และ Google BigQuery", metadata={"course_code": "CS113"}),
        Document(page_content="CS114 วิชา 'การเขียนโปรแกรม Go (Golang)' พัฒนา Backend Service ที่มีประสิทธิภาพสูง รองรับการทำงานแบบ Concurrency และ Microservices", metadata={"course_code": "CS114"}),
        Document(page_content="CS115 วิชา 'ระบบการจัดการความปลอดภัย (ISO 27001)' ศึกษามาตรฐานความมั่นคงปลอดภัยสารสนเทศระดับสากลและการบริหารจัดการความเสี่ยงในองค์กร", metadata={"course_code": "CS115"}),
        Document(page_content="CS116 วิชา 'การวิเคราะห์ข้อมูลด้วย Power BI' การสร้าง Data Visualization และ Dashboard อัจฉริยะเพื่อเปลี่ยนข้อมูลให้เป็นกลยุทธ์ทางธุรกิจ", metadata={"course_code": "CS116"}),
        Document(page_content="CS117 วิชา 'การพัฒนาเกมด้วย Unity' สร้างเกม 2D และ 3D ของตัวเองด้วยโปรแกรม Unity พร้อมฝึกเขียนสคริปต์ควบคุมด้วยภาษา C#", metadata={"course_code": "CS117"}),
        Document(page_content="CS118 วิชา 'พื้นฐาน Quantum Computing' ทำความเข้าใจปรากฏการณ์ควอนตัมบิต (Qubits) และการเขียนโปรแกรมบนระบบจำลอง IBM Quantum", metadata={"course_code": "CS118"}),
        Document(page_content="CS119 วิชา 'การตลาดดิจิทัลเชิงเทคนิค' สำหรับนักพัฒนา เน้นการทำ SEO, การติดตั้ง Google Analytics และการทำ Conversion Tracking", metadata={"course_code": "CS119"}),
        Document(page_content="CS120 วิชา 'สถาปัตยกรรม Microservices' การออกแบบระบบ Software ขนาดใหญ่ที่แยกส่วนกันทำงาน และสื่อสารผ่าน gRPC หรือ Message Broker", metadata={"course_code": "CS120"}),
    ]

    vector_store.add_documents(docs)
    print(f"Added {len(docs)} documents with new 384-dim vectors.")

if __name__ == "__main__":
    ingest_courses_to_memory()
