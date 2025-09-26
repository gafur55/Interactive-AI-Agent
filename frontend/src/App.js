import React, { useState, useEffect } from 'react';

const App = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Hello! I\'m DJ Nova. Tap me to start talking!',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');


const [mediaRecorder, setMediaRecorder] = useState(null);

const handleAvatarClick = async () => {
  if (isRecording) {
    // Stop recording
    mediaRecorder.stop();
    setIsRecording(false);
    return;
  }

  // Start recording
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const audioChunks = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    recorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');

      const res = await fetch('http://localhost:8000/stt', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      // Add transcription to chat
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: data.text,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Send transcription to GPT
      const resChat = await fetch("http://localhost:8000/chat", {
        method: "POST",
        body: new URLSearchParams({ prompt: data.text }),
      });
      const chatData = await resChat.json();

      const aiResponse = {
        id: Date.now() + 1,
        role: "assistant",
        content: chatData.reply,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiResponse]);

    };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  } catch (error) {
    console.error('Error recording audio:', error);
    setIsRecording(false);
  }
};

const handleSendMessage = async () => {
  if (!inputMessage.trim()) return;

  const userMessage = {
    id: Date.now(),
    role: 'user',
    content: inputMessage,
    timestamp: new Date(),
  };

  setMessages((prev) => [...prev, userMessage]);
  setInputMessage('');

  try {
    // Call backend /chat
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ prompt: inputMessage }),
    });

    const data = await res.json();

    const aiResponse = {
      id: Date.now() + 1,
      role: "assistant",
      content: data.reply || "Sorry, I couldn’t generate a reply.",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, aiResponse]);
  } catch (err) {
    console.error("Chat error:", err);
  }
};


  // Handle enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  // Clear chat
  const clearChat = () => {
    setMessages([
      {
        id: 1,
        role: 'assistant',
        content: 'Hello! I\'m DJ Nova. Tap me to start talking!',
        timestamp: new Date()
      }
    ]);
  };

  return (
    <div className="app">
      {/* Main Content */}
      <div className={`main-content ${isChatOpen ? 'chat-open' : ''}`}>
        
        {/* Avatar Section */}
        <div className="avatar-container">
          <div 
            className={`avatar ${isRecording ? 'recording' : ''}`}
            onClick={handleAvatarClick}
          >
            🎧
            {isRecording && <div className="recording-pulse"></div>}
          </div>
        </div>

        {/* Voice Status */}
        <div className={`voice-status ${isRecording ? 'listening' : ''}`}>
          {isRecording ? (
            <>🎤 Listening... Speak now!</>
          ) : (
            <>🎵 Tap the avatar to start talking!</>
          )}
        </div>
      </div>

      {/* Chat Toggle Button */}
      <div 
        className="chat-toggle"
        onClick={() => setIsChatOpen(!isChatOpen)}
      >
        💬
      </div>

      {/* Chat Sidebar */}
      <div className={`chat-sidebar ${isChatOpen ? 'open' : ''}`}>
        <div className="chat-header">
          <h3>🎵 Chat with DJ Nova</h3>
          <button 
            className="close-btn"
            onClick={() => setIsChatOpen(false)}
          >
            ×
          </button>
        </div>

        <div className="chat-messages">
          {messages.map((message) => (
            <div 
              key={message.id} 
              className={`message ${message.role}`}
            >
              {message.role === 'assistant' && '🎵 '}{message.content}
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
          <button onClick={handleSendMessage} className="send-btn">
            ➤
          </button>
        </div>

        <div className="chat-stats">
          <p>Messages: {messages.length}</p>
          <p>Status: 🟢 Online</p>
          <button onClick={clearChat} className="clear-btn">
            🗑️ Clear Chat
          </button>
        </div>
      </div>

      {/* Floating Musical Notes */}
      <div className="floating-notes">
        <span className="note note-1">🎵</span>
        <span className="note note-2">🎶</span>
        <span className="note note-3">🎼</span>
        <span className="note note-4">🎺</span>
        <span className="note note-5">🎸</span>
      </div>

      <style jsx>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        .app {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
          min-height: 100vh;
          color: white;
          overflow-x: hidden;
          position: relative;
        }

        .main-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          transition: margin-right 0.3s ease;
          padding: 2rem;
        }

        .main-content.chat-open {
          margin-right: 400px;
        }

        .avatar-container {
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 2rem;
        }

        .avatar {
          width: 80vw;
          height: 80vw;
          max-width: 500px;
          max-height: 500px;
          background: linear-gradient(45deg, #667eea, #764ba2);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: min(15vw, 150px);
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
          position: relative;
          user-select: none;
        }

        .avatar:hover {
          transform: scale(1.05);
          box-shadow: 0 30px 80px rgba(102, 126, 234, 0.4);
        }

        .avatar.recording {
          animation: pulse 1.5s ease-in-out infinite;
        }

        .recording-pulse {
          position: absolute;
          top: -8px;
          left: -8px;
          right: -8px;
          bottom: -8px;
          border: 4px solid #4ade80;
          border-radius: 50%;
          animation: pulse-border 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }

        @keyframes pulse-border {
          0% {
            transform: scale(1);
            opacity: 1;
          }
          100% {
            transform: scale(1.2);
            opacity: 0;
          }
        }

        .voice-status {
          background: rgba(74, 222, 128, 0.9);
          color: white;
          padding: 15px 30px;
          border-radius: 30px;
          font-size: 1.1rem;
          font-weight: 500;
          backdrop-filter: blur(10px);
          animation: bounce 2s ease-in-out infinite;
          text-align: center;
          box-shadow: 0 4px 20px rgba(74, 222, 128, 0.3);
        }

        .voice-status.listening {
          background: rgba(239, 68, 68, 0.9);
          animation: pulse-status 1s ease-in-out infinite;
        }

        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }

        @keyframes pulse-status {
          0%, 100% { 
            transform: scale(1);
            opacity: 1;
          }
          50% { 
            transform: scale(1.05);
            opacity: 0.8;
          }
        }

        .chat-toggle {
          position: fixed;
          top: 50%;
          right: 0;
          transform: translateY(-50%);
          background: rgba(102, 126, 234, 0.9);
          color: white;
          border: none;
          border-radius: 30px 0 0 30px;
          width: 60px;
          height: 120px;
          cursor: pointer;
          font-size: 24px;
          transition: all 0.3s ease;
          box-shadow: -4px 0 20px rgba(102, 126, 234, 0.4);
          backdrop-filter: blur(10px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1001;
          user-select: none;
        }

        .chat-toggle:hover {
          width: 80px;
          background: #667eea;
          box-shadow: -6px 0 25px rgba(102, 126, 234, 0.6);
          transform: translateY(-50%) translateX(-10px);
        }

        .chat-sidebar {
          position: fixed;
          top: 0;
          right: -400px;
          width: 400px;
          height: 100vh;
          background: rgba(26, 26, 46, 0.95);
          backdrop-filter: blur(20px);
          transition: right 0.3s ease;
          z-index: 1000;
          border-left: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          flex-direction: column;
        }

        .chat-sidebar.open {
          right: 0;
        }

        .chat-header {
          padding: 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: rgba(102, 126, 234, 0.1);
        }

        .chat-header h3 {
          margin: 0;
          font-size: 1.2rem;
        }

        .close-btn {
          background: none;
          border: none;
          color: white;
          font-size: 24px;
          cursor: pointer;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s ease;
        }

        .close-btn:hover {
          background: rgba(255, 255, 255, 0.1);
        }

        .chat-messages {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .message {
          padding: 12px 16px;
          border-radius: 18px;
          font-size: 0.9rem;
          line-height: 1.4;
          animation: slideIn 0.3s ease;
          max-width: 80%;
        }

        .message.user {
          background: linear-gradient(45deg, #667eea, #764ba2);
          color: white;
          align-self: flex-end;
          border-bottom-right-radius: 5px;
        }

        .message.assistant {
          background: rgba(255, 255, 255, 0.1);
          color: white;
          align-self: flex-start;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-bottom-left-radius: 5px;
        }

        @keyframes slideIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .chat-input-container {
          padding: 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          gap: 10px;
        }

        .chat-input {
          flex: 1;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 25px;
          padding: 12px 20px;
          color: white;
          font-size: 0.9rem;
          outline: none;
          transition: border-color 0.3s ease;
        }

        .chat-input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .chat-input:focus {
          border-color: #667eea;
        }

        .send-btn {
          background: #667eea;
          border: none;
          color: white;
          width: 45px;
          height: 45px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          font-size: 16px;
        }

        .send-btn:hover {
          background: #5a67d8;
          transform: scale(1.05);
        }

        .chat-stats {
          padding: 15px 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.7);
        }

        .chat-stats p {
          margin: 5px 0;
        }

        .clear-btn {
          background: rgba(239, 68, 68, 0.8);
          border: none;
          color: white;
          padding: 8px 16px;
          border-radius: 15px;
          cursor: pointer;
          font-size: 0.8rem;
          margin-top: 10px;
          transition: background 0.3s ease;
        }

        .clear-btn:hover {
          background: rgba(239, 68, 68, 1);
        }

        .floating-notes {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 1;
        }

        .note {
          position: absolute;
          font-size: 2rem;
          opacity: 0.3;
          animation: float 6s ease-in-out infinite;
        }

        .note-1 { top: 20%; left: 10%; animation-delay: 0s; }
        .note-2 { top: 60%; right: 15%; animation-delay: 2s; }
        .note-3 { top: 30%; right: 25%; animation-delay: 4s; }
        .note-4 { top: 70%; left: 20%; animation-delay: 3s; }
        .note-5 { top: 40%; left: 80%; animation-delay: 1s; }

        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          33% { transform: translateY(-20px) rotate(5deg); }
          66% { transform: translateY(10px) rotate(-3deg); }
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .main-content.chat-open {
            margin-right: 0;
          }
          
          .chat-sidebar {
            width: 100vw;
            right: -100vw;
          }
          
          .avatar {
            width: 85vw;
            height: 85vw;
            font-size: min(20vw, 120px);
          }
          
          .chat-toggle {
            width: 50px;
            height: 100px;
            font-size: 20px;
          }
          
          .voice-status {
            font-size: 1rem;
            padding: 12px 24px;
          }
        }
      `}</style>
    </div>
  );
};

export default App;