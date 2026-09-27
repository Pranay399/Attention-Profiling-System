import React, { useState, useEffect, useRef } from "react";
import { Video, Camera, StopCircle, Maximize2, Settings } from "lucide-react";
import { motion } from "framer-motion";

const ActiveSession = () => {
  const [isCapturing, setIsCapturing] = useState(false);
  const [wsStatus, setWsStatus] = useState("Disconnected");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const captureIntervalRef = useRef<number | null>(null);
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    // Initialize WebSocket
    const ws = new WebSocket("ws://localhost:8000/api/v1/sessions/1/stream");
    ws.onopen = () => setWsStatus("Connected");
    ws.onclose = () => setWsStatus("Disconnected");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (
        data.type === "attention_alert" ||
        data.type === "participant_state"
      ) {
        setEvents((prev) => [data, ...prev].slice(0, 50)); // Keep last 50 events
      }
    };
    wsRef.current = ws;

    return () => {
      ws.close();
      if (captureIntervalRef.current) clearInterval(captureIntervalRef.current);
    };
  }, []);

  const startCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 10 },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      setIsCapturing(true);

      // Start frame extraction loop
      captureIntervalRef.current = window.setInterval(sendFrame, 100); // ~10 FPS

      // Handle stop from browser UI
      stream.getVideoTracks()[0].onended = stopCapture;
    } catch (err) {
      console.error("Error starting capture:", err);
    }
  };

  const stopCapture = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsCapturing(false);
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
  };

  const sendFrame = () => {
    if (
      !videoRef.current ||
      !canvasRef.current ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (video.videoWidth === 0) return;

    // Set canvas dimensions to downscaled size for performance
    const targetWidth = 640;
    const targetHeight = (targetWidth / video.videoWidth) * video.videoHeight;
    canvas.width = targetWidth;
    canvas.height = targetHeight;

    // Draw and get base64
    ctx?.drawImage(video, 0, 0, targetWidth, targetHeight);
    const base64Data = canvas.toDataURL("image/jpeg", 0.7);

    // Send to backend
    wsRef.current.send(
      JSON.stringify({
        type: "video_frame",
        participant_id: "browser_test_user",
        data: base64Data,
      }),
    );
  };

  return (
    <div
      style={{
        maxWidth: 1400,
        margin: "0 auto",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <header
        style={{
          marginBottom: "1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h1
            className="text-gradient"
            style={{ fontSize: "2rem", marginBottom: "0.5rem" }}
          >
            CS101: Intro to CS
          </h1>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              color: "var(--text-secondary)",
            }}
          >
            <span
              style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}
            >
              <Video size={16} /> Google Meet Integration
            </span>
            <span
              style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}
            >
              <span
                className={`status-dot ${wsStatus === "Connected" ? "active" : ""}`}
              ></span>{" "}
              API: {wsStatus}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", gap: "1rem" }}>
          <button
            className="glass-panel-interactive"
            style={{
              padding: "0.75rem 1.5rem",
              borderRadius: "8px",
              border: "1px solid var(--border-light)",
              background: "var(--bg-tertiary)",
              color: "var(--text-primary)",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontWeight: 600,
            }}
          >
            <Settings size={18} /> Configure
          </button>

          {isCapturing ? (
            <button
              onClick={stopCapture}
              style={{
                padding: "0.75rem 1.5rem",
                borderRadius: "8px",
                border: "none",
                background: "rgba(239, 68, 68, 0.1)",
                color: "var(--error)",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontWeight: 600,
                boxShadow: "0 0 15px var(--error-glow)",
              }}
            >
              <StopCircle size={18} /> Stop Capture
            </button>
          ) : (
            <button
              onClick={startCapture}
              style={{
                padding: "0.75rem 1.5rem",
                borderRadius: "8px",
                border: "none",
                background:
                  "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
                color: "white",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontWeight: 600,
                boxShadow: "0 0 20px var(--accent-glow)",
              }}
            >
              <Camera size={18} /> Request Screen Capture
            </button>
          )}
        </div>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(12, 1fr)",
          gap: "1.5rem",
          flex: 1,
          minHeight: 0,
        }}
      >
        {/* Main Video Area */}
        <div
          className="glass-panel col-span-8"
          style={{
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "1rem 1.5rem",
              borderBottom: "1px solid var(--border-light)",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>
              Meet Video Source
            </h2>
            <Maximize2
              size={16}
              color="var(--text-tertiary)"
              style={{ cursor: "pointer" }}
            />
          </div>

          <div
            style={{
              flex: 1,
              background: "#000",
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <video
              ref={videoRef}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                display: isCapturing ? "block" : "none",
              }}
              muted
            />
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {!isCapturing && (
              <div
                style={{ textAlign: "center", color: "var(--text-tertiary)" }}
              >
                <Camera
                  size={48}
                  style={{ margin: "0 auto 1rem", opacity: 0.5 }}
                />
                <p>Waiting for Screen Capture Authorization</p>
                <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
                  Select the Google Meet tab when prompted.
                </p>
              </div>
            )}

            {isCapturing && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  border: "2px solid var(--success)",
                  borderRadius: "4px",
                  pointerEvents: "none",
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: 16,
                    right: 16,
                    background: "rgba(0,0,0,0.6)",
                    padding: "0.25rem 0.75rem",
                    borderRadius: 4,
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <span className="status-dot active pulse-glow"></span>
                  <span style={{ fontSize: "0.75rem", fontWeight: 600 }}>
                    CAPTURING (10 FPS)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Live Events Feed */}
        <div
          className="glass-panel col-span-4"
          style={{
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "1rem 1.5rem",
              borderBottom: "1px solid var(--border-light)",
            }}
          >
            <h2 style={{ fontSize: "1rem", fontWeight: 600 }}>
              Real-Time Events
            </h2>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
            {isCapturing ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                }}
              >
                {events.length === 0 ? (
                  <div
                    style={{
                      textAlign: "center",
                      color: "var(--text-tertiary)",
                      padding: "2rem 0",
                    }}
                  >
                    Monitoring for attention events...
                  </div>
                ) : (
                  events.map((evt, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ x: 20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      className="glass-panel"
                      style={{ padding: "0.75rem", fontSize: "0.875rem" }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "0.25rem",
                        }}
                      >
                        <span
                          style={{
                            color:
                              evt.type === "attention_alert"
                                ? "var(--warning)"
                                : "var(--text-secondary)",
                            fontWeight: 600,
                          }}
                        >
                          {evt.type === "attention_alert"
                            ? "Attention Alert"
                            : "State Update"}
                        </span>
                        <span style={{ color: "var(--text-tertiary)" }}>
                          {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                        </span>
                      </div>
                      <div>
                        {evt.type === "attention_alert"
                          ? `Student ${evt.participant_id} - ${evt.event_type}`
                          : `Student ${evt.participant_id} state: ${evt.current_state}`}
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "var(--text-tertiary)",
                }}
              >
                Waiting for capture to start...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActiveSession;
