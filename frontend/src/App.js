// App.js
import React, { useEffect, useRef, useState } from "react";
import avatarPng from "./assets/avatar.png";

const API_BASE = "http://localhost:8000";
const TALKING_PHOTO_ID = "af5820d3e6bb42609e4782cc89db0aee"; // <- your talking photo ID

export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, role: "assistant", content: "Hello! I'm DJ Nova. Tap me to start talking!", timestamp: new Date() },
  ]);
  const [inputMessage, setInputMessage] = useState("");

  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState("");

  // live avatar state
  const [videoSrc, setVideoSrc] = useState("");
  const [videoMuted, setVideoMuted] = useState(false);
  const [isVideoLive, setIsVideoLive] = useState(false);

  const pollRef = useRef(null);
  const videoRef = useRef(null);

  useEffect(() => () => pollRef.current && clearInterval(pollRef.current), []);

  // autoplay video (audio first, then muted fallback)
  useEffect(() => {
    if (!videoSrc) return;
    const v = videoRef.current;
    if (!v) return;

    const tryPlay = async () => {
      try {
        v.muted = false;
        setVideoMuted(false);
        await v.play();
      } catch {
        try {
          v.muted = true;
          setVideoMuted(true);
          await v.play();
        } catch {
          /* user interaction may be required */
        }
      }
    };
    const t = setTimeout(() => tryPlay(), 50);
    return () => clearTimeout(t);
  }, [videoSrc]);

  const safeJson = async (res) => { try { return await res.json(); } catch { return null; } };

  const playAudioBlob = async (blob) => {
    const url = URL.createObjectURL(blob);
    if (currentAudio) { try { currentAudio.pause(); currentAudio.currentTime = 0; } catch {} }
    const audio = new Audio(url);
    audio.onended = () => setCurrentAudio(null);
    try { await audio.play(); } catch {}
    setCurrentAudio(audio);
  };

  const resetTile = () => {
    setVideoSrc("");
    setVideoMuted(false);
    setIsVideoLive(false);
    setError("");
  };

  // ---------------- HeyGen: create job -> poll -> stream ----------------
  const startHeyGenRender = async (text) => {
    try {
      setError("");
      setVideoSrc("");
      setIsVideoLive(false);

      const fd = new FormData();
      fd.append("input_text", text);
      fd.append("talking_photo_id", TALKING_PHOTO_ID);

      const genRes = await fetch(`${API_BASE}/heygen/generate`, { method: "POST", body: fd });
      if (!genRes.ok) {
        const j = await safeJson(genRes);
        throw new Error(j?.error || `Generate failed (${genRes.status})`);
      }
      const { video_id } = await genRes.json();
      if (!video_id) throw new Error("No video_id returned");

      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const sRes = await fetch(`${API_BASE}/heygen/status?video_id=${encodeURIComponent(video_id)}`);
          const sJson = await sRes.json();
          const st = sJson?.data?.status;
          if (!st) return;
          if (st === "completed") {
            setVideoSrc(`${API_BASE}/heygen/stream?video_id=${encodeURIComponent(video_id)}`);
            clearInterval(pollRef.current);
            pollRef.current = null;
          } else if (st === "failed") {
            const msg = sJson?.data?.error || "Unknown generation failure";
            throw new Error(msg);
          }
        } catch (e) {
          console.error("Status poll error:", e);
          setError(e?.message || "HeyGen status failed.");
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }, 2500);
    } catch (e) {
      console.error("startHeyGenRender error:", e);
      setError(e?.message || "HeyGen render failed.");
    }
  };

  // ---------- shared record flow ----------
  const runRecordFlow = async (audioChunks) => {
    try {
      setIsBusy(true); setError("");

      // STT
      const fd = new FormData();
      fd.append("file", new Blob(audioChunks, { type: "audio/wav" }), "recording.wav");
      const sttRes = await fetch(`${API_BASE}/stt`, { method: "POST", body: fd });
      const stt = await sttRes.json();
      const userText = stt.text || "";
      setMessages((m) => [...m, { id: Date.now(), role: "user", content: userText, timestamp: new Date() }]);

      // Chat
      const chatRes = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ prompt: userText }),
      });
      const chat = await chatRes.json();
      const aiText = chat.reply || "Sorry, I couldn’t generate a reply.";
      setMessages((m) => [...m, { id: Date.now() + 1, role: "assistant", content: aiText, timestamp: new Date() }]);

      // Optional: TTS
      // const ttsRes = await fetch(`${API_BASE}/tts`, {
      //   method: "POST",
      //   headers: { "Content-Type": "application/x-www-form-urlencoded" },
      //   body: new URLSearchParams({ text: aiText }),
      // });
      // if (ttsRes.ok) playAudioBlob(await ttsRes.blob());

      if (aiText) await startHeyGenRender(aiText);
    } catch (err) {
      console.error("Voice flow error:", err);
      setError(err?.message || "Something went wrong in voice flow.");
    } finally {
      setIsBusy(false);
    }
  };

  // ---------- Avatar click (kept): unmute video if showing; otherwise toggle mic ----------
  const handleAvatarClick = async () => {
    // If a video is up and might be paused by autoplay policy, use click to unmute/play it.
    if (videoSrc) {
      const v = videoRef.current;
      if (v) {
        try { v.muted = false; setVideoMuted(false); await v.play(); } catch {}
      }
      return;
    }
    // else: behave like mic toggle
    await toggleMic();
  };

  // ---------- NEW: mic button toggle ----------
  const toggleMic = async () => {
    // stop current TTS if playing
    if (currentAudio) { currentAudio.pause(); currentAudio.currentTime = 0; setCurrentAudio(null); }

    // stop recording if already running
    if (isRecording && mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      return;
    }

    // start a new recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        await runRecordFlow(chunks);
      };
      recorder.start();
      setIsRecording(true);
      setMediaRecorder(recorder);
    } catch (err) {
      console.error("Recording error:", err);
      setError(err?.message || "Could not access microphone.");
    }
  };

  // ---------- Typed path ----------
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    const prompt = inputMessage;
    setInputMessage("");
    setMessages((m) => [...m, { id: Date.now(), role: "user", content: prompt, timestamp: new Date() }]);
    try {
      setIsBusy(true); setError("");
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ prompt }),
      });
      const data = await res.json();
      const aiText = data.reply || "Sorry, I couldn’t generate a reply.";
      setMessages((m) => [...m, { id: Date.now() + 1, role: "assistant", content: aiText, timestamp: new Date() }]);
      await startHeyGenRender(aiText);
    } catch (err) {
      console.error("Chat error:", err);
      setError(err?.message || "Chat failed.");
    } finally {
      setIsBusy(false);
    }
  };

  // video events
  const onVideoPlaying = () => setIsVideoLive(true);
  const onVideoWaiting  = () => setIsVideoLive(false);
  const onVideoEndedOrError = () => resetTile();

  const handleKeyPress = (e) => { if (e.key === "Enter") handleSendMessage(); };

  const clearChat = () => {
    resetTile();
    setMessages([{ id: 1, role: "assistant", content: "Hello! I'm DJ Nova. Tap me to start talking!", timestamp: new Date() }]);
  };

  return (
    <div className="app">
      <div className={`main-content ${isChatOpen ? "chat-open" : ""}`}>

        {/* AVATAR TILE */}
        <div className="avatar-box" onClick={handleAvatarClick}>
          {/* Video below */}
          {videoSrc && (
            <video
              key={videoSrc}
              ref={videoRef}
              src={videoSrc}
              autoPlay
              playsInline
              muted={videoMuted}
              preload="auto"
              onPlaying={onVideoPlaying}
              onWaiting={onVideoWaiting}
              onEnded={onVideoEndedOrError}
              onError={onVideoEndedOrError}
              className={`avatar-media ${isVideoLive ? "video-visible" : "video-hidden"}`}
            />
          )}
          {/* Cover image on top until video actually plays */}
          <img
            src={avatarPng}
            alt="avatar"
            className={`avatar-media cover ${isVideoLive ? "cover-hide" : "cover-show"}`}
            draggable={false}
          />
        </div>

        {/* NEW: Mic button under the avatar */}
        <div className="mic-row" aria-live="polite">
          <button
            className={`mic-btn ${isRecording ? "recording" : ""}`}
            onClick={toggleMic}
            disabled={isBusy}
          >
            {isRecording ? "● Listening… Tap to stop" : "🎤 Tap to talk"}
          </button>
        </div>

        {error && <div style={{ marginTop: 12, color: "#ffb3b3" }}>⚠️ {error}</div>}
      </div>

      {/* Chat Toggle */}
      <div className="chat-toggle" onClick={() => setIsChatOpen(!isChatOpen)}>💬</div>

      {/* Chat Sidebar */}
      <div className={`chat-sidebar ${isChatOpen ? "open" : ""}`}>
        <div className="chat-header">
          <h3>🎵 Chat with DJ Nova</h3>
          <button className="close-btn" onClick={() => setIsChatOpen(false)}>×</button>
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
            className="chat-input"
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
          />
          <button className="send-btn" onClick={handleSendMessage} disabled={isBusy}>➤</button>
          <button className="clear-btn" onClick={clearChat}>🗑️ Clear</button>
        </div>
      </div>

      {/* Styles */}
      <style jsx>{`
        *{margin:0;padding:0;box-sizing:border-box}
        .app{font-family:system-ui,-apple-system,Segoe UI,Roboto; background:linear-gradient(135deg,#1a1a2e,#16213e 50%,#0f3460); min-height:100vh; color:#fff}
        .main-content{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:2rem}
        .chat-open{margin-right:400px}

        .avatar-box{
          position:relative;
          width:420px; height:420px;
          border-radius:12px; overflow:hidden;
          box-shadow:0 20px 60px rgba(0,0,0,.35);
          background:rgba(255,255,255,.04);
          cursor:pointer;
        }
        .avatar-media{
          width:100%; height:100%;
          object-fit:cover; display:block;
          background:#000;
          position:absolute; inset:0;
        }
        .video-hidden{opacity:0; transition:opacity .18s ease-out; pointer-events:none;}
        .video-visible{opacity:1; transition:opacity .18s ease-out;}
        .cover-show{opacity:1; transition:opacity .18s ease-in;}
        .cover-hide{opacity:0; transition:opacity .18s ease-in; pointer-events:none;}

        .mic-row{margin-top:12px}
        .mic-btn{
          background:#22c55e; color:#0b111e;
          border:none; padding:10px 18px; border-radius:999px;
          font-weight:800; letter-spacing:.2px; cursor:pointer;
          box-shadow:0 8px 24px rgba(34,197,94,.25);
          transition:transform .08s ease, box-shadow .2s ease, background .2s ease;
        }
        .mic-btn:hover{transform:translateY(-1px); box-shadow:0 10px 30px rgba(34,197,94,.35)}
        .mic-btn:active{transform:translateY(0)}
        .mic-btn.recording{
          background:#ef4444; color:#fff;
          box-shadow:0 0 0 0 rgba(239,68,68,.6);
          animation:pulse 1s infinite;
        }
        @keyframes pulse{
          0%{box-shadow:0 0 0 0 rgba(239,68,68,.6)}
          70%{box-shadow:0 0 0 14px rgba(239,68,68,0)}
          100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}
        }

        .chat-toggle{position:fixed;top:50%;right:0;transform:translateY(-50%);
          background:rgba(102,126,234,.9);color:#fff;border-radius:30px 0 0 30px;
          width:60px;height:120px;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:-4px 0 20px rgba(102,126,234,.4)}

        .chat-sidebar{position:fixed;top:0;right:-400px;width:400px;height:100vh;background:rgba(26,26,46,.95);
          transition:right .3s;display:flex;flex-direction:column;border-left:1px solid rgba(255,255,255,.1)}
        .chat-sidebar.open{right:0}
        .chat-header{padding:20px;border-bottom:1px solid rgba(255,255,255,.1);display:flex;justify-content:space-between;align-items:center}
        .chat-messages{flex:1;padding:20px;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
        .message{padding:10px 14px;border-radius:14px;background:rgba(255,255,255,.08)}
        .message.user{background:linear-gradient(45deg,#667eea,#764ba2)}
        .chat-input-container{padding:16px;border-top:1px solid rgba(255,255,255,.1);display:flex;gap:10px}
        .chat-input{flex:1;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:10px;padding:10px 12px;color:#fff}
        .send-btn{background:#667eea;border:none;color:#fff;padding:10px 16px;border-radius:10px;cursor:pointer;font-weight:700}
        .clear-btn{background:transparent;color:#fff;border:1px solid rgba(255,255,255,.3);padding:10px 12px;border-radius:10px;cursor:pointer}
        @media (max-width:768px){.chat-sidebar{width:100vw;right:-100vw}.main-content.chat-open{margin-right:0}}
      `}</style>
    </div>
  );
}
