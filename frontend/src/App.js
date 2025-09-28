// App.js
import React, { useState } from "react";
import avatarPng from "./assets/avatar.png";

const API_BASE = "http://localhost:8000";
// Paste your Talking Photo "Copy Avatar ID" here:
const TALKING_PHOTO_ID = "7f5acbb81e684f6c94e645f12206648d";

export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      content: "Hello! I'm DJ Nova. Tap me to start talking!",
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");

  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");

  // --- Helpers ---
  const latestAssistantText = () => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].content?.trim()) {
        return messages[i].content;
      }
    }
    return "";
  };

  const playAudioBlob = async (blob) => {
    const url = URL.createObjectURL(blob);
    if (currentAudio) {
      try {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      } catch {}
    }
    const audio = new Audio(url);
    audio.onended = () => setCurrentAudio(null);
    try {
      await audio.play();
    } catch {}
    setCurrentAudio(audio);
  };

  // --- Record mic -> STT -> Chat -> TTS -> HeyGen (auto) ---
  const handleAvatarClick = async () => {
    // Stop current TTS if playing
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
    }

    // Stop recording if already recording
    if (isRecording && mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      return;
    }

    // Start recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        try {
          setIsBusy(true);
          setError("");

          // 1) STT
          const audioBlob = new Blob(chunks, { type: "audio/wav" });
          const fd = new FormData();
          fd.append("file", audioBlob, "recording.wav");

          const sttRes = await fetch(`${API_BASE}/stt`, { method: "POST", body: fd });
          const sttJson = await sttRes.json();

          const userText = sttJson.text || "";
          const userMsg = { id: Date.now(), role: "user", content: userText, timestamp: new Date() };
          setMessages((prev) => [...prev, userMsg]);

          // 2) Chat
          const chatRes = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ prompt: userText }),
          });
          const chatJson = await chatRes.json();

          const aiText = chatJson.reply || "Sorry, I couldn’t generate a reply.";
          const aiMsg = { id: Date.now() + 1, role: "assistant", content: aiText, timestamp: new Date() };
          setMessages((prev) => [...prev, aiMsg]);

          // // 3) TTS (play assistant message)
          // if (aiText) {
          //   const ttsRes = await fetch(`${API_BASE}/tts`, {
          //     method: "POST",
          //     headers: { "Content-Type": "application/x-www-form-urlencoded" },
          //     body: new URLSearchParams({ text: aiText }),
          //   });
          //   if (!ttsRes.ok) {
          //     console.error("TTS error:", await ttsRes.text());
          //   } else {
          //     const audioBlob2 = await ttsRes.blob();
          //     await playAudioBlob(audioBlob2);
          //   }
          // }

          // 4) HeyGen render & download (auto)
          if (aiText) {
            try {
              const hfd = new FormData();
              hfd.append("input_text", aiText);
              hfd.append("talking_photo_id", TALKING_PHOTO_ID); // your avatar
              const suggestedName = `vivian_${Date.now()}.mp4`;
              hfd.append("filename", suggestedName);

              const hres = await fetch(`${API_BASE}/heygen/generate_and_download`, {
                method: "POST",
                body: hfd,
              });

              const ct = hres.headers.get("content-type") || "";
              if (!hres.ok || ct.includes("application/json")) {
                let detail = "";
                try {
                  const j = await hres.json();
                  detail = j.error || JSON.stringify(j).slice(0, 400);
                } catch {}
                throw new Error(`HeyGen error ${hres.status}: ${detail || "Unknown error"}`);
              }

              const blob = await hres.blob();
              let downloadName = suggestedName;
              const dispo = hres.headers.get("Content-Disposition");
              if (dispo) {
                const m = /filename="?([^"]+)"?/i.exec(dispo);
                if (m && m[1]) downloadName = m[1];
              }

              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = downloadName;
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            } catch (e) {
              console.error("HeyGen auto-download failed:", e);
              setError(e?.message || "HeyGen video failed.");
            }
          }
        } catch (err) {
          console.error("Voice flow error:", err);
          setError(err?.message || "Something went wrong in voice flow.");
        } finally {
          setIsBusy(false);
        }
      };

      recorder.start();
      setIsRecording(true);
      setMediaRecorder(recorder);
    } catch (err) {
      console.error("Recording error:", err);
      setError(err?.message || "Could not access microphone.");
    }
  };

  // --- Type -> Chat -> TTS -> HeyGen (auto) ---
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMsg = { id: Date.now(), role: "user", content: inputMessage, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);

    const prompt = inputMessage;
    setInputMessage("");

    try {
      setIsBusy(true);
      setError("");

      // Chat
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ prompt }),
      });
      const data = await res.json();

      const aiText = data.reply || "Sorry, I couldn’t generate a reply.";
      const aiMsg = { id: Date.now() + 1, role: "assistant", content: aiText, timestamp: new Date() };
      setMessages((prev) => [...prev, aiMsg]);

      // TTS
      if (aiText) {
        const ttsRes = await fetch(`${API_BASE}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ text: aiText }),
        });

        if (ttsRes.ok) {
          const audioBlob = await ttsRes.blob();
          await playAudioBlob(audioBlob);
        } else {
          console.error("TTS error:", await ttsRes.text());
        }
      }

      // HeyGen render & download (auto)
      if (aiText) {
        try {
          const hfd = new FormData();
          hfd.append("input_text", aiText);
          hfd.append("talking_photo_id", TALKING_PHOTO_ID); // your avatar
          const suggestedName = `vivian_${Date.now()}.mp4`;
          hfd.append("filename", suggestedName);

          const hres = await fetch(`${API_BASE}/heygen/generate_and_download`, {
            method: "POST",
            body: hfd,
          });

          const ct = hres.headers.get("content-type") || "";
          if (!hres.ok || ct.includes("application/json")) {
            let detail = "";
            try {
              const j = await hres.json();
              detail = j.error || JSON.stringify(j).slice(0, 400);
            } catch {}
            throw new Error(`HeyGen error ${hres.status}: ${detail || "Unknown error"}`);
          }

          const blob = await hres.blob();
          let downloadName = suggestedName;
          const dispo = hres.headers.get("Content-Disposition");
          if (dispo) {
            const m = /filename="?([^"]+)"?/i.exec(dispo);
            if (m && m[1]) downloadName = m[1];
          }

          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = downloadName;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);
        } catch (e) {
          console.error("HeyGen auto-download failed:", e);
          setError(e?.message || "HeyGen video failed.");
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
      setError(err?.message || "Chat failed.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") handleSendMessage();
  };

  const clearChat = () => {
    setMessages([
      {
        id: 1,
        role: "assistant",
        content: "Hello! I'm DJ Nova. Tap me to start talking!",
        timestamp: new Date(),
      },
    ]);
    setError("");
  };

  return (
    <div className="app">
      {/* Main Content */}
      <div className={`main-content ${isChatOpen ? "chat-open" : ""}`}>
        {/* Avatar Section (no mouth sync) */}
        <div className="avatar-container" style={{ position: "relative" }}>
          <div onClick={handleAvatarClick} style={{ cursor: "pointer" }}>
            <img
              src={avatarPng}
              alt="avatar"
              style={{
                width: 420,
                height: 420,
                borderRadius: 12,
                objectFit: "cover",
                display: "block",
                boxShadow: "0 20px 60px rgba(0,0,0,.35)",
                userSelect: "none",
              }}
              draggable={false}
            />
          </div>
        </div>

        {/* Voice Status */}
        <div className={`voice-status ${isRecording ? "listening" : ""}`}>
          {isRecording ? <>🎤 Listening... Speak now!</> : <>🎵 Tap the avatar to start talking!</>}
        </div>

        {error && (
          <div style={{ marginTop: 10, color: "#ffb3b3" }}>
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* Chat Toggle Button */}
      <div className="chat-toggle" onClick={() => setIsChatOpen(!isChatOpen)}>
        💬
      </div>

      {/* Chat Sidebar */}
      <div className={`chat-sidebar ${isChatOpen ? "open" : ""}`}>
        <div className="chat-header">
          <h3>🎵 Chat with DJ Nova</h3>
          <button className="close-btn" onClick={() => setIsChatOpen(false)}>
            ×
          </button>
        </div>

        <div className="chat-messages">
          {messages.map((m) => (
            <div key={m.id} className={`message ${m.role}`}>
              {m.role === "assistant" && "🎵 "}
              {m.content}
            </div>
          ))}
        </div>

        <div className="chat-input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="chat-input"
          />
        <button onClick={handleSendMessage} className="send-btn" disabled={isBusy}>
            ➤
          </button>
        </div>

        <div className="chat-stats">
          <p>Messages: {messages.length}</p>
          <p>Status: {isBusy ? "🟡 Working" : "🟢 Online"}</p>
          <button onClick={clearChat} className="clear-btn">
            🗑️ Clear Chat
          </button>
        </div>
      </div>

      {/* Styles */}
      <style jsx>{`
        * { margin: 0; padding: 0; box-sizing: border-box; }
        .app {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
          min-height: 100vh; color: white; overflow-x: hidden; position: relative;
        }
        .main-content { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; transition: margin-right 0.3s ease; padding: 2rem; }
        .main-content.chat-open { margin-right: 400px; }
        .avatar-container { display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; }
        .voice-status { background: rgba(74, 222, 128, 0.9); color: white; padding: 12px 24px; border-radius: 30px; font-size: 1rem; font-weight: 500; backdrop-filter: blur(10px); animation: bounce 2s ease-in-out infinite; text-align: center; box-shadow: 0 4px 20px rgba(74, 222, 128, 0.3); }
        .voice-status.listening { background: rgba(239, 68, 68, 0.9); animation: pulse-status 1s ease-in-out infinite; }
        @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
        @keyframes pulse-status { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.05); opacity: 0.8; } }
        .chat-toggle {
          position: fixed; top: 50%; right: 0; transform: translateY(-50%);
          background: rgba(102, 126, 234, 0.9); color: white; border: none; border-radius: 30px 0 0 30px;
          width: 60px; height: 120px; cursor: pointer; font-size: 24px; transition: all 0.3s ease;
          box-shadow: -4px 0 20px rgba(102, 126, 234, 0.4); backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; z-index: 1001; user-select: none;
        }
        .chat-toggle:hover { width: 80px; background: #667eea; box-shadow: -6px 0 25px rgba(102, 126, 234, 0.6); transform: translateY(-50%) translateX(-10px); }
        .chat-sidebar { position: fixed; top: 0; right: -400px; width: 400px; height: 100vh; background: rgba(26, 26, 46, 0.95); backdrop-filter: blur(20px); transition: right 0.3s ease; z-index: 1000; border-left: 1px solid rgba(255, 255, 255, 0.1); display: flex; flex-direction: column; }
        .chat-sidebar.open { right: 0; }
        .chat-header { padding: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: space-between; align-items: center; background: rgba(102, 126, 234, 0.1); }
        .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 16px; border-radius: 18px; font-size: 0.9rem; line-height: 1.4; animation: slideIn 0.3s ease; max-width: 80%; }
        .message.user { background: linear-gradient(45deg, #667eea, #764ba2); color: white; align-self: flex-end; border-bottom-right-radius: 5px; }
        .message.assistant { background: rgba(255, 255, 255, 0.1); color: white; align-self: flex-start; border: 1px solid rgba(255, 255, 255, 0.1); border-bottom-left-radius: 5px; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .chat-input-container { padding: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); display: flex; gap: 10px; }
        .chat-input { flex: 1; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 25px; padding: 12px 20px; color: white; font-size: 0.9rem; outline: none; transition: border-color 0.3s ease; }
        .chat-input::placeholder { color: rgba(255, 255, 255, 0.5); }
        .chat-input:focus { border-color: #667eea; }
        .send-btn { background: #667eea; border: none; color: white; padding: 10px 16px; border-radius: 10px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s ease; font-size: 14px; font-weight: 600; }
        .send-btn:hover { background: #5a67d8; transform: translateY(-1px); }
        .clear-btn { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,0.3); padding: 8px 12px; border-radius: 10px; cursor: pointer; }
        .chat-stats { padding: 15px 20px; border-top: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); }
        @media (max-width: 768px) {
          .main-content.chat-open { margin-right: 0; }
          .chat-sidebar { width: 100vw; right: -100vw; }
        }
      `}</style>
    </div>
  );
}
