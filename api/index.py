from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import uvicorn

# เพิ่มเส้นทางเพื่อให้หาไฟล์ในโฟลเดอร์เดียวกันเจอ
sys.path.append(os.path.dirname(__file__))

try:
    from agent import app as agent_app
except ImportError:
    from api.agent import app as agent_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # เรียกใช้ LangGraph logic
        result = agent_app.invoke({"question": request.message})
        return {"response": result.get("response", "No response from AI")}
    except Exception as e:
        print(f"Error in chat_endpoint: {e}")
        return {"response": f"ขออภัย เกิดข้อผิดพลาดด้านเทคนิค: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
