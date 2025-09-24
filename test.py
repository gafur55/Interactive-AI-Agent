import streamlit as st
import time
import random
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="AI Music Avatar",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for minimal, clean design
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* Main app styling */
    .main {
        padding: 0;
        margin: 0;
    }
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        height: 100vh;
        overflow: hidden;
    }
    
    /* Avatar container - takes up most of the screen */
    .avatar-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100%;
        position: relative;
    }
    
    .avatar-image {
        width: 80vw;
        height: 80vh;
        max-width: 600px;
        max-height: 600px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: min(15vw, 200px);
        color: white;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .avatar-image:hover {
        transform: scale(1.05);
        box-shadow: 0 30px 80px rgba(102, 126, 234, 0.4);
    }
    
    /* Voice recording indicator */
    .recording-indicator {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        border-radius: 50%;
        border: 8px solid #4ade80;
        animation: pulse-border 1.5s ease-in-out infinite;
        pointer-events: none;
    }
    
    @keyframes pulse-border {
        0% { 
            transform: scale(1);
            opacity: 1;
            border-width: 8px;
        }
        50% { 
            transform: scale(1.1);
            opacity: 0.7;
            border-width: 4px;
        }
        100% { 
            transform: scale(1.2);
            opacity: 0;
            border-width: 2px;
        }
    }
    
    /* Chat toggle button container */
    .chat-toggle-container {
        position: fixed;
        top: 50%;
        right: 0;
        transform: translateY(-50%);
        z-index: 1001;
    }
    
    /* Chat toggle button */
    .chat-toggle {
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
        user-select: none;
    }
    
    .chat-toggle:hover {
        width: 80px;
        background: #667eea;
        box-shadow: -6px 0 25px rgba(102, 126, 234, 0.6);
        transform: translateX(-10px);
    }
    
    /* Voice status text */
    .voice-status {
        position: fixed;
        bottom: 50px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(74, 222, 128, 0.9);
        color: white;
        padding: 15px 30px;
        border-radius: 30px;
        font-size: 1.1rem;
        font-weight: 500;
        backdrop-filter: blur(10px);
        animation: bounce 2s ease-in-out infinite;
        z-index: 1000;
        text-align: center;
    }
    
    .voice-status.listening {
        background: rgba(239, 68, 68, 0.9);
        animation: pulse 1s ease-in-out infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateX(-50%) translateY(0); }
        50% { transform: translateX(-50%) translateY(-10px); }
    }
    
    @keyframes pulse {
        0%, 100% { 
            transform: translateX(-50%) scale(1);
            opacity: 1;
        }
        50% { 
            transform: translateX(-50%) scale(1.05);
            opacity: 0.8;
        }
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(26, 26, 46, 0.95) !important;
        backdrop-filter: blur(20px) !important;
        border-left: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 5px 18px;
        margin: 8px 0;
        margin-left: 20%;
        text-align: right;
        animation: slideInRight 0.3s ease;
    }
    
    .assistant-message {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 5px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 8px 0;
        margin-right: 20%;
        animation: slideInLeft 0.3s ease;
    }
    
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    /* Hide scrollbar but keep functionality */
    .css-1d391kg::-webkit-scrollbar {
        width: 6px;
    }
    
    .css-1d391kg::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
    }
    
    .css-1d391kg::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.5);
        border-radius: 3px;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 25px !important;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        width: 100% !important;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .avatar-image {
            width: 85vw;
            height: 85vw;
            font-size: min(20vw, 150px);
        }
        
        .chat-toggle {
            top: 50%;
            right: 10px;
            width: 50px;
            height: 100px;
            font-size: 20px;
        }
        
        .voice-status {
            bottom: 30px;
            font-size: 1rem;
            padding: 12px 24px;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm DJ Nova. Tap me to start talking!", "timestamp": datetime.now()}
    ]

if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False

if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False

# Sample responses
music_responses = [
    "Great taste! I love that genre. Tell me more about what you're looking for!",
    "That's awesome! I have some perfect recommendations for you.",
    "Interesting choice! I can help you discover some amazing artists in that style.",
    "Perfect! Let me think of some tracks that would blow your mind.",
    "I totally get that vibe! I know exactly what you'd love.",
    "That's one of my favorite genres too! I have so many suggestions.",
    "Excellent! I can't wait to share some hidden gems with you.",
    "You have great taste! I know some artists that will amaze you."
]

# Chat toggle button
if st.button("💬", key="chat_toggle", help="Open Chat"):
    st.session_state.show_chat = not st.session_state.show_chat
    st.rerun()

# JavaScript for the chat toggle button positioning
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const button = document.querySelector('[data-testid="stButton"] button');
    if (button) {
        button.className = 'chat-toggle';
    }
});
</script>
""", unsafe_allow_html=True)

# Main avatar
avatar_clicked = st.button(
    "🎧", 
    key="avatar_button",
    help="Click to start voice recording"
)

# Add custom styling to make the avatar button look like our design
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const avatarButton = document.querySelector('[key="avatar_button"]');
    if (avatarButton) {
        avatarButton.className = 'avatar-image';
    }
});
</script>
""", unsafe_allow_html=True)

# Create the main avatar display
st.markdown("""
<div class="avatar-container">
    <div class="avatar-image" onclick="startRecording()">
        🎧
        <div class="recording-indicator" id="recordingIndicator" style="display: none;"></div>
    </div>
</div>

<script>
function startRecording() {
    // This would trigger the Streamlit button click
    document.querySelector('[data-testid="stButton"]:last-of-type button').click();
}
</script>
""", unsafe_allow_html=True)

# Handle avatar click
if avatar_clicked:
    st.session_state.is_recording = True
    st.rerun()

# Recording state handling
if st.session_state.is_recording:
    # Show recording indicator
    st.markdown("""
    <div class="voice-status listening">
        🎤 Listening... Speak now!
    </div>
    <script>
    document.getElementById('recordingIndicator').style.display = 'block';
    </script>
    """, unsafe_allow_html=True)
    
    # Simulate recording for 3 seconds
    time.sleep(3)
    st.session_state.is_recording = False
    
    # Add simulated voice message and response
    st.session_state.messages.append({
        "role": "user",
        "content": "Hey, I love indie rock music!",
        "timestamp": datetime.now()
    })
    
    response = random.choice(music_responses)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now()
    })
    
    st.rerun()

else:
    # Show default status
    st.markdown("""
    <div class="voice-status">
        🎵 Tap the avatar to start talking!
    </div>
    """, unsafe_allow_html=True)

# Chat sidebar (only show if toggled)
if st.session_state.show_chat:
    with st.sidebar:
        st.markdown("### 🎵 Chat with DJ Nova")
        st.markdown("---")
        
        # Display messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-message">🎵 {message["content"]}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Text input for typing (optional)
        def send_text_message():
            if st.session_state.text_input:
                st.session_state.messages.append({
                    "role": "user",
                    "content": st.session_state.text_input,
                    "timestamp": datetime.now()
                })
                
                response = random.choice(music_responses)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now()
                })
                
                st.session_state.text_input = ""
        
        st.text_input(
            "Or type a message:",
            key="text_input",
            on_change=send_text_message,
            placeholder="Type here..."
        )
        
        st.markdown(f"**Messages:** {len(st.session_state.messages)}")
        
        if st.button("Clear Chat"):
            st.session_state.messages = [
                {"role": "assistant", "content": "Hello! I'm DJ Nova. Tap me to start talking!", "timestamp": datetime.now()}
            ]
            st.rerun()

# Custom CSS to hide the fallback button and style mobile
st.markdown("""
<style>
[data-testid="stButton"] {
    display: none !important;
}

@media (max-width: 768px) {
    .chat-toggle-container {
        right: 0;
    }
    
    .chat-toggle {
        width: 50px;
        height: 100px;
        font-size: 20px;
    }
    
    .chat-toggle:hover {
        width: 60px;
        transform: translateX(-5px);
    }
}
</style>
""", unsafe_allow_html=True)
