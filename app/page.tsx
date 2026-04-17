"use client";
import React, { useState, useEffect, useRef } from 'react';

export default function DaisyChat() {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'สวัสดีครับ ยินดีต้อนรับ! มีอะไรให้ผมช่วยหาข้อมูลไหมครับ?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userText = input;
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', text: data.response }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'ai', text: 'เกิดข้อผิดพลาดในการเชื่อมต่อครับ' }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-screen bg-base-200" data-theme="cupcake">
      {/* Navbar / Header */}
      <div className="navbar bg-base-100 shadow-lg px-8 py-6">
        <div className="flex-1">
          <a className="btn btn-ghost text-4xl font-black text-primary">🎓 AI Agent TIDB</a>
        </div>
        <div className="flex-none hidden lg:block">
          <span className="badge badge-primary badge-lg p-4 font-bold">TiDB CLOUD</span>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-10 md:px-20 lg:px-60 space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={`chat ${m.role === 'user' ? 'chat-end' : 'chat-start'}`}>
            <div className="chat-image avatar">
              <div className="w-16 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                <img src={m.role === 'user' ? "https://api.dicebear.com/7.x/avataaars/svg?seed=user" : "https://api.dicebear.com/7.x/bottts/svg?seed=ai"} />
              </div>
            </div>
            <div className="chat-header opacity-50 text-lg mb-1">
              {m.role === 'user' ? 'คุณ' : 'AI Assistant'}
            </div>
            <div className={`chat-bubble text-2xl p-6 leading-relaxed shadow-md ${m.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-accent'}`}>
              {m.text}
            </div>
            <div className="chat-footer opacity-50 mt-1">ส่งแล้ว</div>
          </div>
        ))}
        {loading && (
          <div className="chat chat-start">
            <div className="chat-bubble chat-bubble-accent animate-pulse text-xl">AI กำลังประมวลผล...</div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Footer / Input Group */}
      <div className="p-10 bg-base-100 border-t border-base-300">
        <div className="flex gap-4 max-w-7xl mx-auto">
          <input
            type="text"
            placeholder="พิมพ์คำถามที่นี่..."
            className="input input-bordered input-primary flex-1 h-24 text-3xl px-10 rounded-3xl"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="btn btn-primary h-24 px-12 text-3xl font-black rounded-3xl shadow-xl hover:scale-105 transition-transform"
          >
            ส่ง
          </button>
        </div>
      </div>
    </div>
  );
}
