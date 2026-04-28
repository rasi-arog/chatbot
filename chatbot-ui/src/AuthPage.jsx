import { useState } from "react";
import axios from "axios";
import { HeartPulse } from "lucide-react";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await axios.post(`${API}/${mode}`, { email, password });
      if (mode === "login") {
        localStorage.setItem("token", res.data.token);
        localStorage.setItem("user_email", res.data.email);
        onAuth(res.data.email);
      } else {
        setMode("login");
        setError("Registered! Please log in.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #f7f3e8 0%, #e8efe7 100%)" }}>
      <div style={{ background: "#fefdf9", borderRadius: "24px", padding: "40px", width: "100%", maxWidth: "380px", boxShadow: "0 12px 40px rgba(0,0,0,0.08)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "28px" }}>
          <HeartPulse size={28} color="#3e8166" />
          <span style={{ fontSize: "22px", fontWeight: 800, color: "#3e3831" }}>Health Assistant</span>
        </div>
        <h2 style={{ margin: "0 0 20px", fontSize: "18px", fontWeight: 700, color: "#3e3831" }}>
          {mode === "login" ? "Sign In" : "Create Account"}
        </h2>
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            style={{ padding: "14px 16px", borderRadius: "14px", border: "1.5px solid #e2dcca", fontSize: "15px", fontFamily: "inherit", outline: "none", background: "#fcfbf5", color: "#3e3831" }}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            style={{ padding: "14px 16px", borderRadius: "14px", border: "1.5px solid #e2dcca", fontSize: "15px", fontFamily: "inherit", outline: "none", background: "#fcfbf5", color: "#3e3831" }}
          />
          {error && <div style={{ fontSize: "13px", color: error.includes("Registered") ? "#3e8166" : "#c0392b" }}>{error}</div>}
          <button type="submit" disabled={loading} style={{ padding: "14px", borderRadius: "14px", border: "none", background: "#3e8166", color: "white", fontSize: "15px", fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Register"}
          </button>
        </form>
        <div style={{ marginTop: "16px", fontSize: "14px", color: "#928b7e", textAlign: "center" }}>
          {mode === "login" ? "No account? " : "Have an account? "}
          <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
            style={{ background: "none", border: "none", color: "#3e8166", fontWeight: 600, cursor: "pointer", fontSize: "14px", fontFamily: "inherit" }}>
            {mode === "login" ? "Register" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}
