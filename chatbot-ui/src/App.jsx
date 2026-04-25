import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { HeartPulse, Building2, Activity, Stethoscope, Send, Plus, MessageSquare, MapPin, Pill, X, Menu, Mic, MicOff, ImagePlus, Paperclip, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

const API = "";

function HospitalCard({ hospital }) {
  const typeLabel = hospital.type === "clinic" ? "Clinic" : "Hospital";
  return (
    <div className="hospital-card">
      <div className="hospital-name" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <Building2 size={16} /> {hospital.name}
      </div>
      <div className="hospital-meta-row">
        <span className="hospital-type-badge">{typeLabel}</span>
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

function parseMedicines(text) {
  const medicines = [];
  const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
  let current = null;
  for (const line of lines) {
    if (line.startsWith("•") && !line.startsWith("→")) {
      if (current) medicines.push(current);
      current = { name: line.slice(1).trim(), usedFor: "", guidance: "" };
    } else if (current && line.startsWith("→ Used for:")) {
      current.usedFor = line.replace("→ Used for:", "").trim();
    } else if (current && line.startsWith("→ General use:")) {
      current.guidance = line.replace("→ General use:", "").trim();
    } else if (current && line.startsWith("→")) {
      // fallback for any other → line
      if (!current.usedFor) current.usedFor = line.slice(1).trim();
      else current.guidance = line.slice(1).trim();
    }
  }
  if (current) medicines.push(current);
  return medicines;
}

function PrescriptionTable({ text }) {
  const medicines = parseMedicines(text);
  if (!medicines.length) return <FormattedMessage text={text} />;
  const header = text.split("\n").find(l => l.trim().startsWith("🧾"));
  const disclaimer = text.split("\n").find(l => l.trim().startsWith("⚠"));
  return (
    <div>
      {header && <div style={{ fontWeight: 700, marginBottom: "10px", color: "#3e3831" }}>{header.trim()}</div>}
      <div className="table-responsive">
        <table className="medicine-table">
          <thead>
            <tr>
              <th>#</th>
            <th>Medicine</th>
            <th>Used For</th>
            <th>General Use</th>
          </tr>
        </thead>
        <tbody>
          {medicines.map((m, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <td style={{ fontWeight: 600 }}>{m.name}</td>
              <td>{m.usedFor}</td>
              <td>{m.guidance}</td>
            </tr>
          ))}
        </tbody>
        </table>
      </div>
      {disclaimer && <div style={{ marginTop: "10px", fontSize: "12px", color: "#928b7e", fontStyle: "italic" }}>{disclaimer.trim()}</div>}
    </div>
  );
}

function FormattedMessage({ text }) {
  if (!text) return null;
  let display = text;
  if (typeof text === "string" && text.trimStart().startsWith("{")) {
    try {
      const parsed = JSON.parse(text.trim());
      if (parsed.message) display = parsed.message;
    } catch {}
  }
  return (
    <div style={{ fontSize: "14px", lineHeight: "1.7", color: "#3e3831" }}>
      {display.split("\n").map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} style={{ height: "6px" }} />;
        if (trimmed.startsWith("→")) return (
          <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "2px", paddingLeft: "16px", color: "#554e44", fontSize: "13px" }}>
            <span style={{ color: "#a8a092", flexShrink: 0 }}>→</span>
            <span>{trimmed.slice(1).trim()}</span>
          </div>
        );
        if (trimmed.startsWith("•")) return (
          <div key={i} style={{ display: "flex", gap: "8px", marginTop: "8px", marginBottom: "2px", fontWeight: 600 }}>
            <span style={{ color: "#3e8166", flexShrink: 0 }}>•</span>
            <span>{trimmed.slice(1).trim()}</span>
          </div>
        );
        if (trimmed.startsWith("⚠")) return (
          <div key={i} style={{ marginTop: "10px", fontSize: "12px", color: "#928b7e", fontStyle: "italic" }}>{trimmed}</div>
        );
        if (trimmed.startsWith("💊") || trimmed.startsWith("🧾") || trimmed.startsWith("💡") || trimmed.startsWith("🩺")) return (
          <div key={i} style={{ fontWeight: 700, marginTop: "10px", marginBottom: "4px", color: "#3e3831" }}>{trimmed}</div>
        );
        return <div key={i}>{trimmed}</div>;
      })}
    </div>
  );
}

function BotMessage({ msg, onImageClick, onChipClick }) {
  if (msg.type === "hospital_list") {
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Building2 size={14} /> Nearby Hospitals
        </div>
        <FormattedMessage text={msg.message} />
        <div className="card-grid">
          {msg.data?.hospitals?.map((h, i) => <HospitalCard key={i} hospital={h} />)}
        </div>
      </div>
    );
  }

  if (msg.type === "doctor_suggestion") {
    return (
      <div className="bot-msg structured">
        <div style={{ margin: "0 0 10px", fontSize: "15px" }}>Based on your symptoms, you may consult a <strong>{msg.data?.doctor_type}</strong>.</div>
        <div className="doctor-badge">{msg.data?.doctor_type}</div>
        <div className="follow-up-chips">
          <button className="chip chip-primary" onClick={() => onChipClick("Find nearby hospital")}><Building2 size={13} /> Nearby Hospitals</button>
          <button className="chip" onClick={() => onChipClick("symptoms")}><Activity size={13} /> Check Another Symptom</button>
        </div>
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
        <FormattedMessage text={msg.message} />
        <div className="follow-up-chips">
          <button className="chip chip-primary" onClick={() => onChipClick("Find nearby hospital")}><Building2 size={13} /> Nearby Hospitals</button>
          <button className="chip" onClick={() => onChipClick("symptoms")}><Activity size={13} /> Check Another Symptom</button>
        </div>
      </div>
    );
  }

  if (msg.type === "image_verification" || msg.type === "image_analysis") {
    const results = msg.data?.results;
    if (results) {
      return (
        <div className="bot-msg structured">
          <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <ImagePlus size={14} /> {msg.type === "image_analysis" ? "Image Analysis" : "Image Verification"}
          </div>
          {results.map((r, i) => {
            const ok = r.data?.is_medical;
            const isQuotaError = r.data?.is_medical === null;
            return (
              <div key={i} style={{ marginTop: "8px", paddingTop: i > 0 ? "8px" : 0, borderTop: i > 0 ? "1px solid #e2dcca" : "none" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: "#554e44", marginBottom: "4px", cursor: r.previewUrl ? "pointer" : "default" }} onClick={() => r.previewUrl && onImageClick(r.previewUrl)}>
                  <Paperclip size={12} /> {r.filename}
                </div>
                {r.data?.image_type === "prescription" ? <PrescriptionTable text={r.message} /> : <FormattedMessage text={r.message} />}
                {!isQuotaError && msg.type !== "image_analysis" && (
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
    const isAnalysis = msg.type === "image_analysis";
    return (
      <div className="bot-msg structured">
        <div className="structured-label" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <ImagePlus size={14} /> {isAnalysis ? "Image Analysis" : "Image Verification"}
        </div>
        {msg.data?.image_type === "prescription" ? <PrescriptionTable text={msg.message} /> : <FormattedMessage text={msg.message} />}
        {!isQuotaError && !isAnalysis && (
          <span className="doctor-badge" style={{ background: ok ? "#3e8166" : "#c0392b", display: "inline-flex", alignItems: "center", gap: "6px" }}>
            {ok ? <><CheckCircle size={14} /> Medical Image</> : <><XCircle size={14} /> Not Medical</>}
          </span>
        )}
      </div>
    );
  }

  // plain text fallback — handle any unexpected shape
  let text = typeof msg.message === "string"
    ? msg.message
    : typeof msg.text === "string"
    ? msg.text
    : JSON.stringify(msg.message ?? msg);
  // Unwrap if LLM returned raw JSON as message
  if (text.trimStart().startsWith("{")) {
    try {
      const parsed = JSON.parse(text.trim());
      if (parsed.message) text = parsed.message;
    } catch {}
  }
  return <div className="bot-msg"><FormattedMessage text={text} /></div>;
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
  const [mode, setMode] = useState(null); // 'symptoms' | 'specialist'
  const [lastSymptom, setLastSymptom] = useState(null);
  const [hospitalShown, setHospitalShown] = useState(false);
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
      console.log("[MIC] Requesting microphone...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("[MIC] Got stream:", stream);
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4") ? "audio/mp4"
        : "";
      console.log("[MIC] Using mimeType:", mimeType || "(browser default)");
      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      console.log("[MIC] MediaRecorder created, actual mimeType:", mediaRecorder.mimeType);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => {
        console.log("[MIC] ondataavailable size:", e.data.size);
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mediaRecorder.onstop = async () => {
        console.log("[MIC] onstop fired, chunks:", chunksRef.current.length);
        const blob = new Blob(chunksRef.current, { type: mediaRecorder.mimeType || "audio/webm" });
        console.log("[MIC] Blob size:", blob.size, "type:", blob.type);
        const ext = (mediaRecorder.mimeType || "").includes("mp4") ? "audio.mp4" : "audio.webm";
        const formData = new FormData();
        formData.append("file", blob, ext);
        mediaRecorderRef.current = null;
        stream.getTracks().forEach(t => t.stop());
        try {
          console.log("[MIC] Sending to /transcribe...");
          const res = await fetch("/transcribe", { method: "POST", body: formData });
          console.log("[MIC] /transcribe status:", res.status);
          const data = await res.json();
          console.log("[MIC] Transcription result:", data);
          if (data.text) setInput(data.text);
        } catch (err) { console.error("[MIC] fetch error:", err); }
        finally { setTranscribing(false); }
      };
      mediaRecorder.onerror = (e) => console.error("[MIC] MediaRecorder error:", e.error);
      mediaRecorder.start(250);
      console.log("[MIC] Recording started, state:", mediaRecorder.state);
      setListening(true);
    } catch (err) { console.error("[MIC] getUserMedia error:", err); }
  }, []);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.requestData();
      mediaRecorderRef.current.stop();
    }
    setListening(false);
    setTranscribing(true);
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
          } else if (m.sender === "bot" && (m.type === "image_verification" || m.type === "image_analysis")) {
            // group consecutive image bot messages into one card
            const groupType = m.type;
            const group = [];
            while (i < msgs.length && msgs[i].sender === "bot" && msgs[i].type === groupType) {
              group.push({
                message: msgs[i].message,
                data: msgs[i].structured_data || {},
              });
              i++;
            }
            mapped.push({
              sender: "bot",
              type: groupType,
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

  const GREETINGS = ["hi", "hello", "hey", "yo", "sup", "howdy"];
  const INVALID_SYMPTOM_WORDS = ["hi", "hello", "hey", "yo", "sup", "im", "i am", "my name", "name is", "test", "ok", "okay", "thanks", "thank you"];

  const isValidSymptom = (text) => {
    const lower = text.toLowerCase().trim();
    return !INVALID_SYMPTOM_WORDS.some(w => lower === w || (lower.startsWith(w + " ") && lower.split(" ").length < 3));
  };

  const formatMessage = (raw) => {
    if (mode === "symptoms") return `I have these symptoms: ${raw}`;
    if (mode === "specialist") return lastSymptom ? `Suggest a specialist doctor for: ${lastSymptom}` : `Suggest a specialist doctor for: ${raw}`;
    return raw;
  };

  const sendMessage = async (text) => {
    const raw = (text ?? input).trim();
    const hasImages = pendingImages.length > 0;
    if (!raw && !hasImages) return;

    // Local greeting — skip API
    if (!text && !mode && GREETINGS.includes(raw.toLowerCase())) {
      setInput("");
      setMessages(prev => [...prev,
        { sender: "user", type: "text", message: raw },
        { sender: "bot", type: "text", message: "Hi! I can help with symptoms, finding a specialist, or locating nearby hospitals. What do you need?" }
      ]);
      return;
    }

    // Validate symptom input
    if (mode === "symptoms" && !text && !isValidSymptom(raw)) {
      setMessages(prev => [...prev, { sender: "bot", type: "text", message: "That doesn't look like a symptom. Please describe what you're feeling — e.g. fever, headache, chest pain." }]);
      return;
    }

    const msg = text ? raw : formatMessage(raw);
    if (!msg.trim() && !hasImages) return;

    if (mode === "symptoms" && !text) { setLastSymptom(raw); setHospitalShown(false); }
    setMode(null);
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
        const botReply = res.data;
        setMessages(prev => [...prev, { sender: "bot", ...botReply }]);
        // Auto-fetch hospitals once per symptom flow
        if (botReply.type === "doctor_suggestion" && location && !hospitalShown) {
          setHospitalShown(true);
          const hospRes = await axios.post(`${API}/chat`, {
            user_id: "1",
            session_id: sessionId,
            message: "Find nearby hospital",
            lat: location.lat,
            lng: location.lng,
          });
          setMessages(prev => [...prev,
            { sender: "bot", ...hospRes.data },
            { sender: "bot", type: "text", message: "Need anything else? You can check another symptom or ask me anything." }
          ]);
        }
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
              <MapPin size={12} /> <span className="location-text">Location active</span>
            </span>
          )}
        </header>

        <div className="chat-box">
          {messages.map((msg, i) =>
            msg.sender === "user"
              ? msg.type === "image_file"
                ? <div key={i} className="user-msg" style={{ display: "flex", alignItems: "center", gap: "6px", cursor: msg.previewUrl ? "pointer" : "default" }} onClick={() => msg.previewUrl && setPreviewUrl(msg.previewUrl)}><Paperclip size={14} />{msg.message}</div>
                : <div key={i} className="user-msg">{msg.message}</div>
              : <BotMessage key={i} msg={msg} onImageClick={setPreviewUrl} onChipClick={(action) => {
                  if (action === "symptoms") {
                    setMode("symptoms");
                  } else if (action === "specialist") {
                    if (lastSymptom) { sendMessage(`Suggest a specialist doctor for: ${lastSymptom}`); }
                    else { setMode("specialist"); }
                  } else {
                    sendMessage(action);
                  }
                }} />
          )}
          {loading && <div className="bot-msg typing">Thinking...</div>}
          <div ref={chatEndRef} />
        </div>

        <div className="quick-actions">
          <button onClick={() => {
            if (!location) { requestLocation(); return; }
            sendMessage("Find nearby hospital");
          }} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Building2 size={16} /> Hospital
          </button>
          <button onClick={() => setMode("symptoms")} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Activity size={16} /> Check Symptoms
          </button>
          <button onClick={() => {
            if (lastSymptom) { sendMessage(`Suggest a specialist doctor for: ${lastSymptom}`); }
            else { setMode("specialist"); }
          }} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Stethoscope size={16} /> Find Specialist
          </button>
          <button onClick={() => setMode(null)} style={{ display: mode ? "flex" : "none", alignItems: "center", gap: "6px", background: "#fff0f0", color: "#c0392b", borderColor: "#e57373" }}>
            <X size={14} /> Cancel
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
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  listening ? "Listening..."
                  : transcribing ? "Transcribing..."
                  : mode === "symptoms" ? "Describe your symptoms (e.g. fever, headache)..."
                  : mode === "specialist" ? "What condition do you need a specialist for?"
                  : "Ask about health..."
                }
                disabled={listening || transcribing}
                onKeyDown={(e) => { if (e.key === "Enter") sendMessage(); }}
              />
            </div>
            <button
              ref={micBtnRef}
              className={`mic-btn${listening ? " mic-active" : ""}`}
              onClick={() => listening ? stopListening() : startListening()}
              title={listening ? "Click to stop" : "Click to speak"}
              disabled={transcribing}
            >
              {listening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
            <button className="send-btn" onClick={() => sendMessage()} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
              <Send size={18} /> <span className="send-text">Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
