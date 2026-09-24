"use client";

import { useEffect, useState, useRef } from "react";
import { Badge, Button } from "@/components/ui";
import { toast } from "sonner";

interface Observation {
  participant_id: string;
  label: string;
  behavior: "attentive" | "looking_away" | "head_down";
  head_yaw: number;
  head_pitch: number;
  confidence: number;
}

export default function LiveClassroomPage() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [observations, setObservations] = useState<Observation[]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastNotifiedRef = useRef<Record<string, number>>({});

  useEffect(() => {
    return () => stopCapture();
  }, []);

  const stopCapture = () => {
    setIsCapturing(false);
    setObservations([]);
    
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const startCapture = async () => {
    try {
      // 1. Ask user for screen share permission
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "browser",
        }
      });
      
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // Handle user stopping the share from the browser UI
      stream.getVideoTracks()[0].onended = () => {
        stopCapture();
        toast.info("Screen sharing ended");
      };

      // 2. Connect to WebSocket
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws";
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsCapturing(true);
        toast.success("Live analysis started");

        // 3. Start taking snapshots and sending to backend
        captureIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN && videoRef.current && canvasRef.current) {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            
            // Only capture if video has dimensions
            if (video.videoWidth > 0 && video.videoHeight > 0) {
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
              const ctx = canvas.getContext("2d");
              if (ctx) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                // Compress to 50% JPEG to keep payload small
                const base64 = canvas.toDataURL("image/jpeg", 0.5);
                ws.send(base64);
              }
            }
          }
        }, 500); // 2 FPS
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "observations" && Array.isArray(payload.data)) {
            setObservations(payload.data);
            
            const now = Date.now();
            payload.data.forEach((obs: Observation) => {
              if (obs.behavior !== "attentive") {
                const lastTime = lastNotifiedRef.current[obs.label] || 0;
                // Throttle toast notifications
                if (now - lastTime > 10000) {
                  toast.warning(`${obs.label} is ${obs.behavior.replace("_", " ")}`);
                  lastNotifiedRef.current[obs.label] = now;
                }
              }
            });
          }
        } catch (err) {
          console.error("Failed to parse websocket message", err);
        }
      };

      ws.onclose = () => {
        if (isCapturing) {
          toast.error("Lost connection to server");
          stopCapture();
        }
      };

      wsRef.current = ws;

    } catch (err) {
      console.error("Failed to start capture", err);
      toast.error("Permission denied or capture failed");
    }
  };

  return (
    <div className="layout-content" style={{ maxWidth: "1200px", margin: "0 auto" }}>
      
      {/* Hidden canvas for processing */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "flex-start", 
        marginBottom: "var(--spacing-8)",
        paddingBottom: "var(--spacing-4)",
        borderBottom: "1px solid var(--color-border-default)"
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
            <h1 className="text-2xl" style={{ fontWeight: 600, letterSpacing: "-0.02em" }}>Live Monitoring</h1>
            {isCapturing && (
              <span style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                padding: "4px 10px", borderRadius: "100px",
                backgroundColor: "rgba(224, 36, 36, 0.1)", color: "var(--color-danger)",
                fontSize: "12px", fontWeight: 600, textTransform: "uppercase"
              }}>
                <span style={{
                  width: "8px", height: "8px", borderRadius: "50%",
                  backgroundColor: "var(--color-danger)",
                  animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite"
                }} />
                Live Analysis
              </span>
            )}
          </div>
          <p className="text-sm mt-2" style={{ color: "var(--color-fg-muted)", maxWidth: "600px" }}>
            Securely capture your Google Meet tab directly from your browser to analyze student attention.
          </p>
        </div>
        <Button 
          variant={isCapturing ? "danger" : "primary"}
          onClick={isCapturing ? stopCapture : startCapture}
          style={{ transition: "all 0.2s ease" }}
        >
          {isCapturing ? "Stop Capture" : "Select Google Meet Tab"}
        </Button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 3fr", gap: "var(--spacing-6)" }}>
        {/* Sidebar Video Preview */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-4)" }}>
          <h3 className="text-sm" style={{ fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase" }}>Capture Preview</h3>
          <div style={{
            width: "100%", aspectRatio: "16/9", 
            backgroundColor: "var(--color-bg-subtle)", 
            borderRadius: "var(--radius-lg)", overflow: "hidden",
            border: "1px solid var(--color-border-default)"
          }}>
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted 
              style={{ width: "100%", height: "100%", objectFit: "contain", display: isCapturing ? "block" : "none" }} 
            />
            {!isCapturing && (
              <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-fg-muted)" }}>
                No video feed
              </div>
            )}
          </div>
        </div>

        {/* Observations Grid */}
        <div>
          <h3 className="text-sm" style={{ fontWeight: 600, color: "var(--color-fg-muted)", textTransform: "uppercase", marginBottom: "var(--spacing-4)" }}>Student Status</h3>
          
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
            gap: "var(--spacing-5)"
          }}>
            {observations.map((obs) => {
              const isDistracted = obs.behavior !== "attentive";
              const statusColor = isDistracted ? "var(--color-danger)" : "var(--color-success)";
              const statusBg = isDistracted ? "rgba(224, 36, 36, 0.05)" : "rgba(16, 185, 129, 0.05)";

              return (
                <div key={obs.participant_id} className="card" style={{ 
                  display: "flex", flexDirection: "column", gap: "var(--spacing-4)",
                  transition: "transform 0.2s ease, box-shadow 0.2s ease",
                  borderTop: `3px solid ${statusColor}`,
                  backgroundColor: statusBg
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600, fontSize: "1.1rem" }}>{obs.label}</span>
                    <span style={{ 
                      color: statusColor, fontSize: "0.85rem", fontWeight: 600, 
                      textTransform: "uppercase", letterSpacing: "0.05em" 
                    }}>
                      {obs.behavior.replace("_", " ")}
                    </span>
                  </div>
                  
                  <div style={{ 
                    display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-4)", 
                    paddingTop: "var(--spacing-3)", borderTop: "1px solid var(--color-border-subtle)" 
                  }}>
                    <div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-fg-muted)", marginBottom: "4px" }}>YAW</div>
                      <div style={{ fontFamily: "monospace", fontSize: "1.1rem" }}>
                        {obs.head_yaw > 0 ? "+" : ""}{obs.head_yaw.toFixed(1)}°
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "0.75rem", color: "var(--color-fg-muted)", marginBottom: "4px" }}>PITCH</div>
                      <div style={{ fontFamily: "monospace", fontSize: "1.1rem" }}>
                        {obs.head_pitch > 0 ? "+" : ""}{obs.head_pitch.toFixed(1)}°
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {isCapturing && observations.length === 0 && (
            <div style={{ 
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              padding: "var(--spacing-12) var(--spacing-4)",
              backgroundColor: "var(--color-bg-subtle)", borderRadius: "var(--radius-lg)",
              border: "1px dashed var(--color-border-default)", color: "var(--color-fg-muted)" 
            }}>
              <h3 className="text-lg" style={{ color: "var(--color-fg-default)", fontWeight: 500 }}>Scanning...</h3>
              <p className="mt-2 text-center" style={{ maxWidth: "400px" }}>
                Analyzing the video feed for faces.
              </p>
            </div>
          )}

          {!isCapturing && observations.length === 0 && (
            <div style={{ 
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              padding: "var(--spacing-12) var(--spacing-4)",
              color: "var(--color-fg-muted)" 
            }}>
              <p>Click "Select Google Meet Tab" to share your browser tab.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
