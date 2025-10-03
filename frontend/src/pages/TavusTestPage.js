import React from "react";
import { Conversation } from "../components/cvi/components/conversation";

const TavusTestPage = () => {
  const handleLeave = () => {
    console.log("Conversation ended");
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      <h2>🎥 Tavus Test Page</h2>
      <Conversation
        conversationUrl="https://api.tavus.io/cvi/conversation/YOUR_SESSION_ID"
        onLeave={handleLeave}
      />
    </div>
  );
};

export default TavusTestPage;
