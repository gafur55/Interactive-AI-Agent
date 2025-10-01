import React, { useState, useRef, useEffect } from "react";
import bacground_video from "./assets/bacground_video.mp4";


const API_BASE = "http://localhost:8000"; // https://dj-vivian.onrender.com or http://localhost:8000
const SESSION_ID = Math.random().toString(36).slice(2);


export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "assistant",
      content: "Hello! I'm DJ Vivian. Tap me to start talking!",
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [isBusy, setIsBusy] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [error, setError] = useState("");

  // ✅ Refs to track state without recreating interval
  const isRecordingRef = useRef(isRecording);
  const isBusyRef = useRef(isBusy);
  const isAudioPlayingRef = useRef(isAudioPlaying);
  const currentAudioRef = useRef(currentAudio);

  // ✅ Keep refs in sync with state
  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    isBusyRef.current = isBusy;
  }, [isBusy]);

  useEffect(() => {
    isAudioPlayingRef.current = isAudioPlaying;
  }, [isAudioPlaying]);

  useEffect(() => {
    currentAudioRef.current = currentAudio;
  }, [currentAudio]);

  function addMessage(role, content) {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now() + Math.random(),
        role,
        content,
        timestamp: new Date(),
      },
    ]);
  }

  // --- Background video: mute/unmute only (never pause) ---
  const bgVideoRef = useRef(null);
  const muteBg = () => { const v = bgVideoRef.current; if (v) v.muted = true; };
  const unmuteBg = () => { const v = bgVideoRef.current; if (v) { v.muted = false; v.play().catch(() => {}); } };

  // Set lower default volume on first render
  useEffect(() => {
    if (bgVideoRef.current) {
      bgVideoRef.current.volume = 0.05;
    }
  }, []);

  // ✅ FIXED: Interval only created once, checks all activity states
  useEffect(() => {
    const interval = setInterval(() => {
      // ✅ Only run if user is completely idle
      if (!isRecordingRef.current && !isBusyRef.current && !isAudioPlayingRef.current && !currentAudioRef.current) {
        console.log("✅ Timer fired - user is idle, checking in");
        callMyMethod();
      } else {
        console.log("⏸️ Timer skipped - user is active:", {
          recording: isRecordingRef.current,
          busy: isBusyRef.current,
          audioPlaying: isAudioPlayingRef.current,
          currentAudio: !!currentAudioRef.current
        });
      }
    }, 300000); // idle time

    return () => clearInterval(interval);
  }, []); // ✅ Empty deps - interval never recreated

  async function callMyMethod() {
    try {
      console.log("callMyMethod started");

      // ✅ Set busy state at the START
      setIsBusy(true);

      // ✅ Double-check before snapshot - user might have started recording
      if (isRecordingRef.current || isAudioPlayingRef.current) {
        console.log("❌ Aborted: User became active before snapshot");
        setIsBusy(false);
        return;
      }

      const snapRes = await fetch(`${API_BASE}/camera/snapshot`);
      if (!snapRes.ok) throw new Error("Failed to capture snapshot");
      const { image_base64 } = await snapRes.json();
      console.log("📸 idle snapshot ok, base64 len:", image_base64?.length || 0);

      // ✅ Check again after snapshot
      if (isRecordingRef.current || isAudioPlayingRef.current) {
        console.log("❌ Aborted: User became active after snapshot");
        setIsBusy(false);
        return;
      }

      const hedoraRes = await fetch(`${API_BASE}/get_hedora_text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64,
          prompt: "Describe the mood of this photo in one paragraph.",
          max_tokens: 256,
        }),
      });

      if (!hedoraRes.ok) throw new Error("Hedora analysis failed");
      const { text: hedoraText } = await hedoraRes.json();
      console.log("📝 hedora text:", hedoraText);

      // ✅ Check again after hedora
      if (isRecordingRef.current || isAudioPlayingRef.current) {
        console.log("❌ Aborted: User became active after hedora");
        setIsBusy(false);
        return;
      }

      const chatRes = await fetch(`${API_BASE}/chat_from_hedora_text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hedora_text: hedoraText }),
      });
      if (!chatRes.ok) throw new Error("Chat conversion failed");
      const { reply } = await chatRes.json();
      console.log("💬 reply:", reply);

      // ✅ Final check before playing audio
      if (isRecordingRef.current || isAudioPlayingRef.current) {
        console.log("❌ Aborted: User became active before TTS");
        setIsBusy(false);
        return;
      }

      addMessage("assistant", reply);

      if (reply) {
        const ttsRes = await fetch(`${API_BASE}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ text: reply }),
        });
        if (ttsRes.ok) {
          const audioBlob = await ttsRes.blob();
          // ✅ One more check right before playing
          if (isRecordingRef.current || isAudioPlayingRef.current) {
            console.log("❌ Aborted: User became active right before audio play");
            setIsBusy(false);
            return;
          }
          await playAudioBlob(audioBlob);
        } else {
          console.error("TTS error:", await ttsRes.text());
          if (!isRecording) unmuteBg();
        }
      } else {
        if (!isRecording) unmuteBg();
      }
    } catch (err) {
      console.error("callMyMethod error:", err);
    } finally {
      // ✅ Always clear busy state
      setIsBusy(false);
    }
  }

  function renderMessage(content) {
    if (!content) return "";
    return content.replace(
      /\(https:\/\/open\.spotify\.com[^\)]+\)/g,
      (match) => {
        const url = match.slice(1, -1);
        return ` (<a href="${url}" target="_blank" rel="noopener noreferrer">open in Spotify</a>)`;
      }
    );
  }

  // ✅ FIXED: Play TTS and track audio playing state
  const playAudioBlob = async (blob) => {
    muteBg();
    setIsAudioPlaying(true); // ✅ Mark audio as playing

    const url = URL.createObjectURL(blob);
    if (currentAudio) {
      try { currentAudio.pause(); currentAudio.currentTime = 0; } catch {}
    }
    const audio = new Audio(url);

    audio.onended = () => {
      setCurrentAudio(null);
      setIsAudioPlaying(false); // ✅ Clear playing state
      if (!isRecording) unmuteBg();
    };

    audio.onerror = () => {
      setIsAudioPlaying(false); // ✅ Clear on error
      if (!isRecording) unmuteBg();
    };

    try {
      await audio.play();
    } catch (err) {
      console.error("Audio play error:", err);
      setIsAudioPlaying(false); // ✅ Clear if play fails
      if (!isRecording) unmuteBg();
    }
    setCurrentAudio(audio);
  };

  // --- mic -> STT -> Chat -> TTS ---
  const handleAvatarClick = async () => {
    muteBg();

    if (currentAudio) {
      try { currentAudio.pause(); currentAudio.currentTime = 0; } catch {}
      setCurrentAudio(null);
      setIsAudioPlaying(false);
    }

    if (isRecording && mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      recorder.onstop = async () => {
        try {
          setIsBusy(true);
          setError("");

          // STT
          const audioBlob = new Blob(chunks, { type: "audio/wav" });
          const fd = new FormData();
          fd.append("file", audioBlob, "recording.wav");

          const sttRes = await fetch(`${API_BASE}/stt`, { method: "POST", body: fd });
          const sttJson = await sttRes.json();

          const userText = sttJson.text || "";
          const userMsg = { id: Date.now(), role: "user", content: userText, timestamp: new Date() };
          setMessages((prev) => [...prev, userMsg]);

          // Chat
          const chatRes = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ prompt: userText, session_id: SESSION_ID }),
          });
          const chatJson = await chatRes.json();

          const aiText = chatJson.reply || "Sorry, I couldn't generate a reply.";
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
              const audioBlob2 = await ttsRes.blob();
              await playAudioBlob(audioBlob2);
            } else {
              console.error("TTS error:", await ttsRes.text());
              if (!isRecording) unmuteBg();
            }
          } else {
            if (!isRecording) unmuteBg();
          }
        } catch (err) {
          console.error("Voice flow error:", err);
          setError(err?.message || "Something went wrong in voice flow.");
          if (!isRecording) unmuteBg();
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
      unmuteBg();
    }
  };

  // --- Type -> Chat -> TTS ---
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    const userMsg = { id: Date.now(), role: "user", content: inputMessage, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);

    const prompt = inputMessage;
    setInputMessage("");

    try {
      setIsBusy(true);
      setError("");

      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ prompt, session_id: SESSION_ID }),
      });
      const data = await res.json();

      const aiText = data.reply || "Sorry, I couldn't generate a reply.";
      const aiMsg = { id: Date.now() + 1, role: "assistant", content: aiText, timestamp: new Date() };
      setMessages((prev) => [...prev, aiMsg]);

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
          if (!isRecording) unmuteBg();
        }
      } else {
        if (!isRecording) unmuteBg();
      }
    } catch (err) {
      console.error("Chat error:", err);
      setError(err?.message || "Chat failed.");
      if (!isRecording) unmuteBg();
    } finally {
      setIsBusy(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") handleSendMessage();
  };

  const clearChat = () => {
    setMessages([
      { id: 1, role: "assistant", content: "Hello! I'm DJ Vivian. Tap me to start talking!", timestamp: new Date() },
    ]);
    setError("");
  };

  return (
    <div className="app">
      <video
        ref={bgVideoRef}
        autoPlay
        loop
        muted={false}
        playsInline
        className="background-video"
      >
        <source src={bacground_video} type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      <div className={`main-content ${isChatOpen ? "chat-open" : ""}`}>
        <button
          className={`talk-btn ${isRecording ? "recording" : ""}`}
          onClick={handleAvatarClick}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          {isRecording ? "● Listening… Tap to stop" : "🎤 Talk"}
        </button>

        {error && <div style={{ marginTop: 10, color: "#ffb3b3" }}>⚠️ {error}</div>}
      </div>

      <div className="chat-toggle" onClick={() => setIsChatOpen(!isChatOpen)}>💬</div>

      <div className={`chat-sidebar ${isChatOpen ? "open" : ""}`}>
        <div className="chat-header">
          <h3>🎵 Chat with DJ Vivian</h3>
          <button className="close-btn" onClick={() => setIsChatOpen(false)}>×</button>
        </div>
        <div className="chat-messages">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`message ${m.role}`}
              dangerouslySetInnerHTML={{
                __html: (m.role === "assistant" ? "🎵 " : "") + renderMessage(m.content),
              }}
            />
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
          <button onClick={handleSendMessage} className="send-btn" disabled={isBusy}>➤</button>
        </div>
        <div className="chat-stats">
          <p>Messages: {messages.length}</p>
          <p>Status: {isBusy ? "🟡 Working" : "🟢 Online"}</p>
          <button onClick={clearChat} className="clear-btn">🗑️ Clear Chat</button>
        </div>
      </div>

      <style jsx>{`
        .background-video {
          position: fixed; top: 0; left: 0; width: 100%; height: 100%;
          object-fit: cover; z-index: -1;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        .app { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-height: 100vh; color: white; overflow-x: hidden; position: relative; }
        .main-content { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; transition: margin-right 0.3s ease; padding: 2rem; }
        .main-content.chat-open { margin-right: 400px; }

        .talk-btn {
          background: rgba(102,126,234,0.85);
          color: #fff;
          font-size: 1.1rem;
          font-weight: 600;
          padding: 14px 36px;
          border: none;
          border-radius: 50px;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 8px 24px rgba(102,126,234,0.4);
          backdrop-filter: blur(6px);
          z-index: 10;
          margin-top: 300px;
        }
        .talk-btn:hover,
        .talk-btn:focus {
          background: rgba(102,126,234,1);
          box-shadow: 0 10px 30px rgba(102,126,234,0.6);
          transform: translateY(-2px) scale(1.03);
          outline: none;
        }
        .talk-btn.recording {
          background: rgba(239,68,68,0.9);
          box-shadow: 0 0 20px rgba(239,68,68,0.7);
          animation: pulse-talk 1.2s infinite;
        }
        @keyframes pulse-talk {
          0% { transform: scale(1); box-shadow: 0 0 15px rgba(239,68,68,0.5);}
          50% { transform: scale(1.06); box-shadow: 0 0 25px rgba(239,68,68,0.8);}
          100% { transform: scale(1); box-shadow: 0 0 15px rgba(239,68,68,0.5);}
        }

        .chat-toggle { position: fixed; top: 50%; right: 0; transform: translateY(-50%);
          background: rgba(102, 126, 234, 0.9); color: white; border: none;
          border-radius: 30px 0 0 30px; width: 60px; height: 120px; cursor: pointer;
          font-size: 24px; transition: all 0.3s ease; box-shadow: -4px 0 20px rgba(102, 126, 234, 0.4);
          backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: center; z-index: 1001;
        }
        .chat-toggle:hover { width: 80px; background: #667eea; box-shadow: -6px 0 25px rgba(102, 126, 234, 0.6);
          transform: translateY(-50%) translateX(-10px); }
        .chat-sidebar { position: fixed; top: 0; right: -400px; width: 400px; height: 100vh;
          background: rgba(26, 26, 46, 0.95); backdrop-filter: blur(20px); transition: right 0.3s ease;
          z-index: 1000; border-left: 1px solid rgba(255, 255, 255, 0.1); display: flex; flex-direction: column; }
        .chat-sidebar.open { right: 0; }
        .chat-header { padding: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          display: flex; justify-content: space-between; align-items: center;
          background: rgba(102, 126, 234, 0.1); }
        .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 16px; border-radius: 18px; font-size: 0.9rem; line-height: 1.4;
          animation: slideIn 0.3s ease; max-width: 80%; }
        .message.user { background: linear-gradient(45deg, #667eea, #764ba2); color: white;
          align-self: flex-end; border-bottom-right-radius: 5px; }
        .message.assistant { background: rgba(255, 255, 255, 0.1); color: white;
          align-self: flex-start; border: 1px solid rgba(255, 255, 255, 0.1); border-bottom-left-radius: 5px; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px);} to { opacity: 1; transform: translateY(0);} }
        .chat-input-container { padding: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1);
          display: flex; gap: 10px; }
        .chat-input { flex: 1; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 25px; padding: 12px 20px; color: white; font-size: 0.9rem; outline: none; transition: border-color 0.3s ease; }
        .chat-input::placeholder { color: rgba(255, 255, 255, 0.5); }
        .chat-input:focus { border-color: #667eea; }
        .send-btn { background: #667eea; border: none; color: white; padding: 10px 16px;
          border-radius: 10px; cursor: pointer; display: inline-flex; align-items: center;
          justify-content: center; transition: all 0.2s ease; font-size: 14px; font-weight: 600; }
        .send-btn:hover { background: #5a67d8; transform: translateY(-1px); }
        .clear-btn { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,0.3);
          padding: 8px 12px; border-radius: 10px; cursor: pointer; }
        .chat-stats { padding: 15px 20px; border-top: 1px solid rgba(255, 255, 255, 0.1);
          font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); }
        @media (max-width: 768px) {
          .main-content.chat-open { margin-right: 0; }
          .chat-sidebar { width: 100vw; right: -100vw; }
        }
      `}</style>
    </div>
  );
}
