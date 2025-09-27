import React, { useRef, useEffect } from "react";

const DIDAvatar = ({ onClick, isRecording = false }) => {
  const videoRef = useRef(null);

  useEffect(() => {
    const startAvatar = async () => {
      try {
        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });

        // Debug peer connection state
        pc.onconnectionstatechange = () => {
          console.log("PeerConnection state:", pc.connectionState);
        };

        // Attach remote video from D-ID
        pc.ontrack = (event) => {
          if (videoRef.current) {
            console.log("✅ Remote track received:", event.streams);
            videoRef.current.srcObject = event.streams[0];
            videoRef.current
              .play()
              .catch((err) => console.warn("Autoplay blocked:", err));
          }
        };

        // Optional data channel
        pc.createDataChannel("oai-events");

        // Step 1: Create an SDP offer (browser → backend)
        const localOffer = await pc.createOffer();
        await pc.setLocalDescription(localOffer);

        const res = await fetch("http://localhost:8000/did/offer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sdp: localOffer.sdp, type: localOffer.type }),
        });

        const data = await res.json();
        console.log("D-ID /did/offer response:", data);

        if (!data.offer || !data.id) {
          console.error("❌ Invalid D-ID response:", data);
          return;
        }
        
        await pc.setRemoteDescription(data.answer);
        
        // Step 2: Apply D-ID’s offer as remote description
        await pc.setRemoteDescription(
          new RTCSessionDescription(data.offer)
        );

        // Step 3: Create browser answer
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        // Step 4: Send answer back to backend → D-ID
        const answerRes = await fetch("http://localhost:8000/did/answer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sdp: answer.sdp,
            type: answer.type,
            stream_id: data.id, // stream id returned from /did/offer
          }),
        });

        const answerData = await answerRes.json();
        console.log("D-ID /did/answer response:", answerData);

        console.log("🎉 D-ID avatar connected and streaming!");
      } catch (err) {
        console.error("D-ID connection error:", err);
      }
    };

    startAvatar();
  }, []);

  const handleKeyDown = (event) => {
    if (!onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <div
      className={`avatar ${isRecording ? "recording" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={handleKeyDown}
    >
      {isRecording && <div className="recording-pulse" aria-hidden="true" />}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: "80%",
          height: "80%",
          background: "black",
          borderRadius: "12px",
        }}
      />
    </div>
  );
};

export default DIDAvatar;
