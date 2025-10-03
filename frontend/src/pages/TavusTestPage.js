import React from "react";
import { CVIProvider } from "../components/cvi/components/cvi-provider";
import { Conversation } from "../components/cvi/components/conversation";

const TavusTestPage = () => {
  const conversationUrl = "https://tavus.daily.co/c2b4933c773aa403"; // From your backend response

  return (
    <CVIProvider>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <h2>🎥 Tavus Test Page</h2>
        <Conversation
          conversationUrl={conversationUrl}
          style={{ width: "100%", height: "600px", maxWidth: "1000px" }}
        />
      </div>
    </CVIProvider>
  );
};

export default TavusTestPage;
