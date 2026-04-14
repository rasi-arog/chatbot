import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { HeartPulse, Building2, Activity, Stethoscope, Send, Plus, MessageSquare, MapPin, Pill, X } from "lucide-react";

const API = "http://127.0.0.1:8000";

function HospitalCard({ hospital }) {
  return (
    <div className="hospital-card">
      <div className="hospital-name" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <Building2 size={16} /> {hospital.name}
      </div>
      <div className="hospital-meta-row">
        {hospital.vicinity && (
          <span className="hospital-meta"><MapPin size={12} /> {hospital.vicinity}</span>
        )}
        {hospital.distance_km && (
          <span className="hospital-meta distance">{hospital.distance_km} km away</span>
        )}
      </div>
      {hospital.maps_link && (
        <a href={hospital.maps_link} target="_blank" rel="noreferrer" className="maps-link" style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <MapPin size={14} /> Open in Maps
        </a>
      )}
    </div>
  );
}

function BotMessage({ msg }) {
  if (msg.type === "hospital_list") {
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Building2 size={14} /> Nearby Hospitals
        </div>
        <p>{msg.message}</p>
        <div className="card-grid">
          {msg.data?.hospitals?.map((h, i) => <HospitalCard key={i} hospital={h} />)}
        </div>
      </div>
    );
  }

  if (msg.type === "doctor_suggestion") {
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Stethoscope size={14} /> Doctor Suggestion
        </div>
        <p>{msg.message}</p>
        <div className="doctor-badge">{msg.data?.doctor_type}</div>
      </div>
    );
  }

  if (msg.type === "alert") {
    return (
      <div className="bot-msg alert-msg">
        {msg.message}
      </div>
    );
  }

  if (msg.type === "health_advice") {
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Pill size={14} /> Health Advice
        </div>
        <p>{msg.message}</p>
      </div>
    );
  }

  // plain text fallback — handle any unexpected shape
  const text = typeof msg.message === "string"
    ? msg.message
    : typeof msg.text === "string"
    ? msg.text
    : JSON.stringify(msg.message ?? msg);
  return <div className="bot-msg">{text}</div>;
}

export default function App() {
  const [messages, setMessages] = useState([
    { sender: "bot", type: "text", message: "Hello! How can I assist you with your healthcare today?" }
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [sessions, setSessions] = useState([]);
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const requestLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => {
        console.warn("Geolocation denied:", err.message);
        setLocation(null);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  useEffect(() => {
    requestLocation();
    loadSessions();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const res = await axios.get(`${API}/chat/sessions/1`);
      setSessions(res.data.sessions);
    } catch {}
  };

  const loadHistory = async (id) => {
    setSessionId(id);
    try {
      const res = await axios.get(`${API}/chat/history/${id}`);
      if (res.data.messages?.length > 0) {
        setMessages(res.data.messages.map(m => {
          if (m.sender === "client") {
            return { sender: "user", type: "text", message: m.message };
          }
          // restore full structured response from saved fields
          return {
            sender: "bot",
            type: m.type || "text",
            message: typeof m.message === "string" ? m.message : "",
            data: m.structured_data || {},
          };
        }));
      }
    } catch {}
  };

  const startNewChat = () => {
    setSessionId(crypto.randomUUID());
    setMessages([{ sender: "bot", type: "text", message: "Hello! How can I assist you with your healthcare today?" }]);
  };

  const deleteSession = async (id, e) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this chat history?")) {
      try {
        await axios.delete(`${API}/chat/session/${id}`);
        setSessions(prev => prev.filter(s => s !== id));
        if (sessionId === id) {
          startNewChat();
        }
      } catch {
        alert("Failed to delete chat.");
      }
    }
  };

  const sendMessage = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;

    setMessages(prev => [...prev, { sender: "user", type: "text", message: msg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API}/chat`, {
        user_id: "1",
        session_id: sessionId,
        message: msg,
        lat: location?.lat ?? null,
        lng: location?.lng ?? null,
      });

      // res.data is the structured response: { type, message, data }
      setMessages(prev => [...prev, { sender: "bot", ...res.data }]);
      loadSessions();
    } catch {
      setMessages(prev => [...prev, { sender: "bot", type: "text", message: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <button className="new-chat-btn" onClick={startNewChat}>
          <Plus size={18} /> New Chat
        </button>
        <div className="sidebar-header">Recent Chats</div>
        {sessions.map((id, index) => (
          <div
            key={id}
            className={`session-item ${id === sessionId ? "active" : ""}`}
            onClick={() => loadHistory(id)}
          >
            <div className="session-item-content">
              <MessageSquare size={14} style={{ display: "inline", marginRight: "8px", flexShrink: 0 }} />
              <span className="session-title">Chat {sessions.length - index}</span>
            </div>
            <button
              onClick={(e) => deleteSession(id, e)}
              className="delete-chat-btn"
              title="Delete Chat"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </aside>

      <div className="container">
        <header style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <HeartPulse size={28} color="#3e8166" />
          Health Assistant
          {location && (
            <span className="location-badge">
              <MapPin size={12} /> Location active
            </span>
          )}
        </header>

        <div className="chat-box">
          {messages.map((msg, i) =>
            msg.sender === "user"
              ? <div key={i} className="user-msg">{msg.message}</div>
              : <BotMessage key={i} msg={msg} />
          )}
          {loading && <div className="bot-msg typing">Thinking...</div>}
          <div ref={chatEndRef} />
        </div>

        <div className="quick-actions">
          <button onClick={() => {
            if (!location) {
              requestLocation();
              return;
            }
            sendMessage("Find nearby hospital");
          }} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Building2 size={16} /> Hospital
          </button>
          <button onClick={() => sendMessage("I have fever")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Activity size={16} /> Symptoms
          </button>
          <button onClick={() => sendMessage("Suggest doctor for headache")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Stethoscope size={16} /> Doctor
          </button>
        </div>

        <div className="input-box">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about health..."
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button onClick={() => sendMessage()} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
            <Send size={18} /> Send
          </button>
        </div>
      </div>
    </div>
  );
}
