import { useState } from "react";
import axios from "axios";
import { HeartPulse, Building2, Activity, Stethoscope, Send } from "lucide-react";

export default function App() {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello! How can I assist you with your healthcare today?" }
  ]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input) return;

    const userMsg = { sender: "user", text: input };
    setMessages(prev => [...prev, userMsg]);

    try {
      const res = await axios.post("http://127.0.0.1:8000/chat", {
        user_id: "1",
        session_id: "abc",
        message: input
      });

      let replyData = res.data.reply;
      let replyText = "";
      if (typeof replyData === "string") {
        replyText = replyData;
      } else if (Array.isArray(replyData)) {
        replyText = replyData.map(item => item.text || JSON.stringify(item)).join(" ");
      } else if (typeof replyData === "object" && replyData !== null) {
        replyText = replyData.text || JSON.stringify(replyData);
      } else {
        replyText = String(replyData);
      }

      const botMsg = { sender: "bot", text: replyText };
      setMessages(prev => [...prev, botMsg]);

    } catch (err) {
      console.error(err);
    }

    setInput("");
  };

  return (
    <div className="container">
      <header style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <HeartPulse size={28} color="#3e8166" />
        Health Assistant
      </header>

      <div className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={msg.sender === "user" ? "user-msg" : "bot-msg"}>
            {msg.text}
          </div>
        ))}
      </div>

      <div className="quick-actions">
        <button onClick={() => setInput("Find nearby hospital")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Building2 size={16} /> Hospital
        </button>
        <button onClick={() => setInput("I have fever")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Activity size={16} /> Symptoms
        </button>
        <button onClick={() => setInput("Suggest doctor")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Stethoscope size={16} /> Doctor
        </button>
      </div>

      <div className="input-box">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about health..."
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
          <Send size={18} /> Send
        </button>
      </div>
    </div>
  );
}
