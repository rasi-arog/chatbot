import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { HeartPulse, Building2, Activity, Stethoscope, Send, Plus, MessageSquare, MapPin, Pill, X, Menu, Mic, MicOff, ImagePlus, Paperclip, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

const API = "";

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

function BotMessage({ msg, onImageClick }) {
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
      <div className="bot-msg alert-msg" style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
        <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
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

  if (msg.type === "image_verification") {
    const results = msg.data?.results;
    if (results) {
      return (
        <div className="bot-msg structured">
          <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <ImagePlus size={14} /> Image Verification
          </div>
          {results.map((r, i) => {
            const ok = r.data?.is_medical;
            const isQuotaError = r.data?.is_medical === null;
            return (
              <div key={i} style={{ marginTop: "8px", paddingTop: i > 0 ? "8px" : 0, borderTop: i > 0 ? "1px solid #e2dcca" : "none" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "#554e44", marginBottom: "4px", cursor: r.previewUrl ? "pointer" : "default" }} onClick={() => r.previewUrl && onImageClick(r.previewUrl)}>
                  <Paperclip size={12} /> {r.filename}
                </div>
                <p style={{ margin: "0 0 6px", fontSize: "13px", color: "#554e44" }}>{r.message}</p>
                {!isQuotaError && (
                  <span className="doctor-badge" style={{ background: ok ? "#3e8166" : "#c0392b", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                    {ok ? <><CheckCircle size={14} /> Medical Image</> : <><XCircle size={14} /> Not Medical</>}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      );
    }
    // fallback for history loaded single results
    const ok = msg.data?.is_medical;
    const isQuotaError = msg.data?.is_medical === null;
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <ImagePlus size={14} /> Image Verification
        </div>
        <p>{msg.message}</p>
        {!isQuotaError && (
          <span className="doctor-badge" style={{ background: ok ? "#3e8166" : "#c0392b", display: "inline-flex", alignItems: "center", gap: "6px" }}>
            {ok ? <><CheckCircle size={14} /> Medical Image</> : <><XCircle size={14} /> Not Medical</>}
          </span>
        )}
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
  const [transcribing, setTranscribing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [listening, setListening] = useState(false);
  const [pendingImages, setPendingImages] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const chatEndRef = useRef(null);
  const micBtnRef = useRef(null);
  const sendMessageRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const fileInputRef = useRef(null);

  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    const newImgs = files.map(file => ({ file, preview: URL.createObjectURL(file) }));
    setPendingImages(prev => [...prev, ...newImgs]);
    e.target.value = "";
  };

  const removeImage = (index) => {
    setPendingImages(prev => {
      URL.revokeObjectURL(prev[index].preview);
      return prev.filter((_, i) => i !== index);
    });
  };

  const startListening = useCallback(async () => {
    if (mediaRecorderRef.current) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, "audio.webm");
        mediaRecorderRef.current = null;
        try {
          const res = await fetch("/transcribe", { method: "POST", body: formData });
          const data = await res.json();
          if (data.text) setInput(data.text);
        } catch (err) { console.error("[Whisper] error:", err); }
        finally { setTranscribing(false); }
      };
      mediaRecorder.start();
      setListening(true);
    } catch (err) { console.error("[MIC] error:", err); }
  }, []);

  const stopListening = useCallback(() => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current?.stream?.getTracks().forEach(t => t.stop());
    setListening(false);
    setTranscribing(true);
    // don't auto-send — user clicks Send
  }, []);

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

  const loadSessions = async (retries = 3) => {
    for (let i = 0; i < retries; i++) {
      try {
        const res = await axios.get(`${API}/chat/sessions/1`);
        setSessions(res.data.sessions);
        return;
      } catch {
        if (i < retries - 1) await new Promise(r => setTimeout(r, 2000));
      }
    }
  };

  const loadHistory = async (id) => {
    setSessionId(id);
    try {
      const res = await axios.get(`${API}/chat/history/${id}`);
      if (res.data.messages?.length > 0) {
        const mapped = [];
        let i = 0;
        const msgs = res.data.messages;
        while (i < msgs.length) {
          const m = msgs[i];
          if (m.sender === "client") {
            mapped.push({ sender: "user", type: m.type || "text", message: m.message });
            i++;
          } else if (m.sender === "bot" && m.type === "image_verification") {
            // group consecutive image_verification bot messages into one card
            const group = [];
            while (i < msgs.length && msgs[i].sender === "bot" && msgs[i].type === "image_verification") {
              group.push({
                message: msgs[i].message,
                data: msgs[i].structured_data || {},
              });
              i++;
            }
            mapped.push({
              sender: "bot",
              type: "image_verification",
              message: "",
              data: { results: group },
            });
          } else {
            mapped.push({
              sender: "bot",
              type: m.type || "text",
              message: typeof m.message === "string" ? m.message : "",
              data: m.structured_data || {},
            });
            i++;
          }
        }
        setMessages(mapped);
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
    const hasImages = pendingImages.length > 0;
    if (!msg.trim() && !hasImages) return;

    setInput("");
    const imagesToSend = [...pendingImages];
    setPendingImages([]);
    setLoading(true);

    // convert to data URLs so previews survive after revoking object URLs
    const dataUrls = await Promise.all(imagesToSend.map(img => new Promise(resolve => {
      const reader = new FileReader();
      reader.onload = e => resolve(e.target.result);
      reader.readAsDataURL(img.file);
    })));
    imagesToSend.forEach(img => URL.revokeObjectURL(img.preview));

    if (msg.trim()) setMessages(prev => [...prev, { sender: "user", type: "text", message: msg }]);
    imagesToSend.forEach((img, idx) => {
      setMessages(prev => [...prev, { sender: "user", type: "image_file", message: img.file.name, previewUrl: dataUrls[idx] }]);
    });

    try {
      if (imagesToSend.length > 0) {
        const results = await Promise.all(imagesToSend.map(async (img, idx) => {
          const formData = new FormData();
          formData.append("file", img.file);
          formData.append("user_id", "1");
          formData.append("session_id", sessionId);
          const res = await fetch("/verify-image", { method: "POST", body: formData });
          return { ...await res.json(), filename: img.file.name, previewUrl: dataUrls[idx] };
        }));
        setMessages(prev => [...prev, { sender: "bot", type: "image_verification", message: "", data: { results } }]);
        await loadSessions();
        setSessions(prev => prev.includes(sessionId) ? prev : [sessionId, ...prev]);
      }
      if (msg.trim()) {
        const res = await axios.post(`${API}/chat`, {
          user_id: "1",
          session_id: sessionId,
          message: msg,
          lat: location?.lat ?? null,
          lng: location?.lng ?? null,
        });
        setMessages(prev => [...prev, { sender: "bot", ...res.data }]);
        loadSessions();
      }
    } catch {
      setMessages(prev => [...prev, { sender: "bot", type: "text", message: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  sendMessageRef.current = sendMessage;

  return (
    <div className="app-layout">
      {previewUrl && (
        <div onClick={() => setPreviewUrl(null)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <img src={previewUrl} alt="preview" style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: "12px", boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }} />
        </div>
      )}
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        <button className="sidebar-close-btn" onClick={() => setSidebarOpen(false)}>
          <X size={18} />
        </button>
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
          <button className="hamburger-btn" onClick={() => setSidebarOpen(true)}>
            <Menu size={22} />
          </button>
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
              ? msg.type === "image_file"
                ? <div key={i} className="user-msg" style={{ display: "flex", alignItems: "center", gap: "6px", cursor: msg.previewUrl ? "pointer" : "default" }} onClick={() => msg.previewUrl && setPreviewUrl(msg.previewUrl)}><Paperclip size={14} />{msg.message}</div>
                : <div key={i} className="user-msg">{msg.message}</div>
              : <BotMessage key={i} msg={msg} onImageClick={setPreviewUrl} />
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

        <div className="input-area">
          {pendingImages.length > 0 && (
            <div className="image-preview-strip">
              {pendingImages.map((img, i) => (
                <div key={i} className="preview-thumb">
                  <img src={img.preview} alt="preview" onClick={() => setPreviewUrl(img.preview)} style={{ cursor: "pointer" }} />
                  <button className="remove-img-btn" onClick={() => removeImage(i)}><X size={12} /></button>
                </div>
              ))}
            </div>
          )}
          <div className="input-box">
            <input ref={fileInputRef} type="file" accept="image/*" multiple style={{ display: "none" }} onChange={handleImageSelect} />
            <div className="input-wrapper">
              <button className="attach-btn" onClick={() => fileInputRef.current.click()} title="Attach image">
                <Plus size={18} />
              </button>
              <input
                value={listening ? "" : transcribing ? "" : input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={listening ? "Listening..." : transcribing ? "Transcribing..." : "Ask about health..."}
                disabled={listening || transcribing}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              />
            </div>
            <button
              ref={micBtnRef}
              onClick={() => listening ? stopListening() : startListening()}
              title={listening ? "Click to stop" : "Click to speak"}
              disabled={transcribing}
              style={{ marginLeft: "8px", padding: "0 16px", border: "none", background: listening ? "#c0392b" : "#f0eadd", color: listening ? "white" : "#3e8166", borderRadius: "28px", cursor: transcribing ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.2s", userSelect: "none" }}
            >
              {listening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
            <button onClick={() => sendMessage()} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
              <Send size={18} /> Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
