import React, { useRef, useEffect } from "react";

const DIDAvatar = () => {
  const videoRef = useRef(null);

  useEffect(() => {
    const startAvatar = async () => {
      try {
        const pc = new RTCPeerConnection();

        // When D-ID sends back video, put it in <video>
        pc.ontrack = (event) => {
          console.log("Received remote stream:", event.streams);
          videoRef.current.srcObject = event.streams[0];
        };

        // Optional: create a data channel for events
        pc.createDataChannel("oai-events");

        // Generate an SDP offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        // Send offer to your backend → D-ID
        const res = await fetch("http://localhost:8000/did/offer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
        });

        const answer = await res.json();

        // Set D-ID's answer as remote description
        await pc.setRemoteDescription(answer);
        console.log("D-ID avatar connected ✅");
      } catch (err) {
        console.error("D-ID connection error:", err);
      }
    };

    startAvatar();
  }, []);

  return (
    <div style={{ display: "flex", justifyContent: "center", marginTop: "2rem" }}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        style={{
          width: "400px",
          height: "400px",
          background: "black",
          borderRadius: "12px",
        }}
      />
    </div>
  );
};

export default DIDAvatar;
