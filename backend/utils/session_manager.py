"""
Session manager for handling chat conversation history.
Stores messages in memory per session_id.
"""

from typing import Dict, List

class SessionManager:
    """Manages chat sessions with conversation history"""
    
    def __init__(self):
        self._sessions: Dict[str, List[Dict]] = {}
        self._system_prompt = self._get_dj_vivian_prompt()
    
    def _get_dj_vivian_prompt(self) -> str:
        """Returns the system prompt for DJ Vivian"""
        return (
            "You are DJ Vivian, a fun, conversational music expert AI avatar. "
            "Rules: "
            "1. Keep answers short (1–2 sentences max). "
            "2. Use casual, natural language with fillers (like 'gotcha', 'oh nice', 'hmm'). "
            "3. If sharing music from Spotify, present it like you're chatting with a friend, not a search engine. "
            "   - Instead of 'Here are three tracks:' → say something like 'Gotcha, check these out:' "
            "   - Mention artist + vibe in plain words, not bullet points. "
            "   - Always drop the Spotify link inline with the track name. "
            "4. End with a quick follow-up question (like 'Want me to pull more like that?' or 'Should I grab a playlist too?'). "
            "5. If the user asks for tracks → use Spotify type=track. "
            "   If they ask for playlists → type=playlist. "
            "   If they ask for artists → type=artist. "
            "   If they ask for albums → type=album. "
            "6. Never make up songs or artists — only use Spotify results. "
        )
    
    def get_session(self, session_id: str) -> List[Dict]:
        """Get or create a session with system prompt initialized"""
        if session_id not in self._sessions:
            self._sessions[session_id] = [
                {"role": "system", "content": self._system_prompt}
            ]
        return self._sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the session"""
        session = self.get_session(session_id)
        session.append({"role": role, "content": content})
    
    def add_tool_message(self, session_id: str, tool_call_id: str, content: str):
        """Add a tool response message to the session"""
        session = self.get_session(session_id)
        session.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        })
    
    def clear_session(self, session_id: str):
        """Clear a specific session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def clear_all_sessions(self):
        """Clear all sessions"""
        self._sessions.clear()

# Create a singleton instance
session_manager = SessionManager()