# 🤖 AI Agent TIDB (Next.js + FastAPI + DaisyUI)

ระบบผู้ช่วยอัจฉริยะวิเคราะห์และแนะนำรายวิชา โดยใช้พลังของ **LangGraph**, **TiDB Cloud (Vector Search)** และ **Groq Cloud (Llama 3.1)** พร้อมดีไซน์สุดพรีเมียมด้วย **DaisyUI**

## 🌟 จุดเด่น (Highlights)
- 🎨 **Modern UI**: ใช้ DaisyUI พร้อมธีม `cupcake` ที่สวยสะอาดตาและอ่านง่าย
- ⚡ **Ultra Fast**: ตอบสนองไวด้วย Groq Inference Engine และ FastAPI
- 📊 **Hybrid Data**: ค้นหาได้ทั้งเชิงความหมาย (Vector) และข้อมูลเชิงลึก (SQL)
- 📱 **Responsive**: รองรับการใช้งานทั้งบนมือถือและคอมพิวเตอร์

## ☁️ ทำไมต้อง TiDB Cloud?
ในโปรเจกต์นี้เราเลือกใช้ **TiDB Cloud (Serverless)** เพราะความสามารถที่เป็นเอกลักษณ์:
- **MySQL Compatible**: ใช้งานได้เหมือน MySQL ที่เราคุ้นเคย 100% เชื่อมต่อง่ายผ่าน SQLAlchemy
- **Built-in Vector Search**: มีระบบจัดเก็บและค้นหา Vector ในตัว ทำให้เราไม่ต้องแยกฐานข้อมูลระหว่างข้อมูลทั่วไป (SQL) และข้อมูล AI (Vector)
- **Scalability**: เป็น Distributed SQL ที่ขยายตัวได้อัตโนมัติ รองรับข้อมูลมหาศาล
- **Cost-Efficiency**: รูปแบบ Serverless ทำให้เริ่มต้นใช้งานได้ฟรีและจ่ายตามการใช้งานจริง

## 🛠 Tech Stack
- **Frontend**: Next.js 14, React, Tailwind CSS v4, DaisyUI
- **Backend**: FastAPI (Python 3.12)
- **Agent Orchestration**: LangGraph
- **Models**: Llama 3.1 8B (via Groq), BGE-m3 (via Hugging Face)
- **Database**: TiDB Cloud (Serverless)

## 🚀 การติดตั้งและใช้งาน

### 1. ตั้งค่า Environment Variables (.env)
```env
TIDB_CONNECTION_STRING=mysql://...
GROQ_API_KEY=gsk_...
HF_TOKEN=hf_...
TIDB_SSL_CA_CONTENT="-----BEGIN CERTIFICATE-----..."
```

### 2. ติดตั้งและเริ่ม Backend
```bash
uv pip install -r requirements.txt
uv run api/index.py
```

### 3. ติดตั้งและเริ่ม Frontend
```bash
yarn install
yarn dev
```

## 📂 โครงสร้างโปรเจกต์
- `/api`: โค้ดส่วน Backend และ AI Agent
- `/app`: โค้ดส่วน Frontend (Next.js)
- `/public`: ไฟล์สื่อและรูปภาพต่างๆ

---
Developed with ❤️ by Your Name
