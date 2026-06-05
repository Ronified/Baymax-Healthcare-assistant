import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Heart, Activity, Compass, Droplet, Moon, Eye, EyeOff, 
  AlertTriangle, Volume2, VolumeX, Mic, Send, X, ChevronDown, 
  FileText, Sparkles, User, RefreshCw, Square, Check
} from 'lucide-react';

// ==========================================================================
// 1. FLOATING HOLO-MESH CANVAS BACKGROUND (120FPS FLUID)
// ==========================================================================
function HoloBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const particles = [];
    const particleCount = 45;
    let mouseX = null;
    let mouseY = null;

    // Initialize particles
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 1.5 + 1
      });
    }

    const handleMouseMove = (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    const handleMouseLeave = () => {
      mouseX = null;
      mouseY = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    let frameId;
    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      ctx.lineWidth = 0.5;
      for (let i = 0; i < particleCount; i++) {
        const p1 = particles[i];
        
        // Drift towards mouse
        if (mouseX !== null && mouseY !== null) {
          const dx = mouseX - p1.x;
          const dy = mouseY - p1.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 160) {
            p1.x += (dx / dist) * 0.12;
            p1.y += (dy / dist) * 0.12;
          }
        }

        p1.x += p1.vx;
        p1.y += p1.vy;

        // Wrapping boundaries
        if (p1.x < 0) p1.x = width;
        if (p1.x > width) p1.x = 0;
        if (p1.y < 0) p1.y = height;
        if (p1.y > height) p1.y = 0;

        ctx.fillStyle = "rgba(0, 255, 171, 0.12)";
        ctx.beginPath();
        ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2);
        ctx.fill();

        for (let j = i + 1; j < particleCount; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 95) {
            const alpha = (1 - dist / 95) * 0.12;
            ctx.strokeStyle = `rgba(0, 229, 255, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }
      frameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return <canvas ref={canvasRef} id="holo-mesh-canvas" />;
}

// ==========================================================================
// 2. DYNAMIC ECG CANVAS MONITOR COMPONENT
// ==========================================================================
function EcgMonitor({ bpm, spo2, playHeartbeatClick }) {
  const canvasRef = useRef(null);
  const beatProgressRef = useRef(-1);
  const lastBeatTimeRef = useRef(performance.now());

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const canvasWidth = canvas.width = 400;
    const canvasHeight = canvas.height = 75;

    const ecgPoints = [];
    for (let i = 0; i < canvasWidth; i++) {
      ecgPoints.push(canvasHeight / 2);
    }

    const ecgTemplate = [
      0, 0, 0, 0, 0,
      -1.5, -3.5, -1.5, 0, 0,         // P wave
      0, 1.8,                         // Q wave
      -26, 8.5,                       // R peak & S plunge
      0, 0,                           // S-T segment
      -3.5, -5.5, -3.5, -1.5, 0,      // T wave
      0, 0, 0, 0, 0                   // Flat resting
    ];

    let frameId;
    const render = () => {
      ctx.fillStyle = "rgba(4, 8, 20, 0.16)"; // Soft scroll trails
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);

      // Draw background grid lines
      ctx.strokeStyle = "rgba(0, 255, 171, 0.04)";
      ctx.lineWidth = 0.5;
      for (let i = 0; i < canvasWidth; i += 20) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvasHeight);
        ctx.stroke();
      }
      for (let j = 0; j < canvasHeight; j += 15) {
        ctx.beginPath();
        ctx.moveTo(0, j);
        ctx.lineTo(canvasWidth, j);
        ctx.stroke();
      }

      const now = performance.now();
      const beatInterval = 60000 / bpm; // Beat spacing in ms

      if (now - lastBeatTimeRef.current > beatInterval) {
        lastBeatTimeRef.current = now;
        beatProgressRef.current = 0;
        playHeartbeatClick();
      }

      let targetY = canvasHeight / 2;
      if (beatProgressRef.current >= 0 && beatProgressRef.current < ecgTemplate.length) {
        const ampMultiplier = bpm > 110 ? 1.25 : 1.0;
        targetY += ecgTemplate[beatProgressRef.current] * ampMultiplier;
        beatProgressRef.current++;
      } else {
        beatProgressRef.current = -1;
      }

      ecgPoints.push(targetY);
      ecgPoints.shift();

      // Set wave color based on SpO2 alerts
      let waveColor = "#00ffab";
      if (spo2 < 90) {
        waveColor = Math.floor(now / 150) % 2 === 0 ? "#ff3366" : "rgba(255, 51, 102, 0.2)";
      } else if (spo2 < 95) {
        waveColor = "#ffb300";
      }

      ctx.strokeStyle = waveColor;
      ctx.lineWidth = 2.0;
      ctx.shadowColor = waveColor;
      ctx.shadowBlur = 6;
      ctx.beginPath();

      for (let idx = 0; idx < ecgPoints.length; idx++) {
        if (idx === 0) {
          ctx.moveTo(idx, ecgPoints[idx]);
        } else {
          ctx.lineTo(idx, ecgPoints[idx]);
        }
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      frameId = requestAnimationFrame(render);
    };

    frameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [bpm, spo2, playHeartbeatClick]);

  return <canvas ref={canvasRef} id="ecg-canvas" />;
}

// ==========================================================================
// 3. CENTRAL APP COMPONENT
// ==========================================================================
export default function App() {
  // Sound Context Ref
  const audioCtxRef = useRef(null);
  const panicIntervalRef = useRef(null);

  // Vitals State
  const [bpm, setBpm] = useState(72);
  const [spo2, setSpo2] = useState(98);
  const [steps, setSteps] = useState(4200);
  const [sleep, setSleep] = useState(6.5);
  const [syncTime, setSyncTime] = useState("Never");
  const [isSyncing, setIsSyncing] = useState(false);
  const [isOverrideOpen, setIsOverrideOpen] = useState(false);

  // Consultation State
  const [messages, setMessages] = useState([
    {
      role: 'baymax',
      text: "Hello, I am Baymax, your personal healthcare companion. I was alerted to a need for medical attention. Please select a body scan region or describe your symptoms below. I am not a doctor and cannot diagnose.",
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [speakOnComplete, setSpeakOnComplete] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [activeRegion, setActiveRegion] = useState("india");
  const [emergNumbers, setEmergNumbers] = useState({ police: "112", ambulance: "108", note: "" });

  // Camera & Emotion Scanner State
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [emotion, setEmotion] = useState("N/A");
  const [faceBox, setFaceBox] = useState(null);

  // Body Map Targets
  const [selectedBodyPart, setSelectedBodyPart] = useState("None");
  const [reticlePos, setReticlePos] = useState({ x: 50, y: 110, visible: false });

  // Insights / Database Lookups
  const [trials, setTrials] = useState([]);
  const [fdaAlert, setFdaAlert] = useState(null);

  // Panic overlay
  const [isPanicActive, setIsPanicActive] = useState(false);

  // Refs
  const videoRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const chatEndRef = useRef(null);
  const cameraIntervalRef = useRef(null);
  const ttsUtteranceRef = useRef(null);
  const recognitionRef = useRef(null);
  const sseReaderRef = useRef(null);

  const BODY_PART_COORDS = {
    "Head": { x: 50, y: 25 },
    "Throat": { x: 50, y: 41 },
    "Chest": { x: 50, y: 80 },
    "Abdomen": { x: 50, y: 132 },
    "Arms": { x: 23, y: 80 },
    "Legs": { x: 44, y: 180 }
  };

  const BODY_PART_SYMPTOMS = {
    "Head": "I have a severe headache and visual blurriness.",
    "Throat": "My throat is extremely sore and it hurts to swallow.",
    "Chest": "I am experiencing heavy chest pain and mild shortness of breath.",
    "Abdomen": "I have sharp abdominal cramps and nausea.",
    "Arms": "I have joint pain in my wrists and shoulders.",
    "Legs": "My knees are swollen and painful when walking."
  };

  // ==========================================================================
  // Web Audio Synth Triggers
  // ==========================================================================
  const initAudio = () => {
    if (!audioCtxRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new AudioContextClass();
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
  };

  const playBeep = (freq, duration, type = "sine", gainVal = 0.05) => {
    try {
      initAudio();
      const ctx = audioCtxRef.current;
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();
      
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gainNode.gain.setValueAtTime(gainVal, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration - 0.01);
      
      osc.connect(gainNode);
      gainNode.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn("Synth warning:", e);
    }
  };

  const playSyncChirp = () => {
    playBeep(980, 0.08, "triangle", 0.08);
    setTimeout(() => playBeep(1318, 0.12, "triangle", 0.08), 70);
  };

  const playWarningChirp = () => {
    playBeep(440, 0.14, "sine", 0.1);
    setTimeout(() => playBeep(440, 0.14, "sine", 0.1), 180);
  };

  const playPanicSweep = () => {
    const ctx = audioCtxRef.current;
    if (!ctx) return;
    try {
      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(150, ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(320, ctx.currentTime + 0.3);
      gainNode.gain.setValueAtTime(0.08, ctx.currentTime);
      gainNode.gain.linearRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.connect(gainNode);
      gainNode.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch (e) {}
  };

  const playHeartbeatClick = () => {
    // Soft double thump synced with ECG drawing
    playBeep(65, 0.05, "sine", 0.1);
    setTimeout(() => playBeep(52, 0.06, "sine", 0.06), 90);
  };

  // ==========================================================================
  // Browser Speech Synthesis
  // ==========================================================================
  const speak = (text) => {
    if (!speakOnComplete || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#_`\-\n]/g, " ").replace(/\s+/g, " ");
    
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 0.95; 
    utterance.pitch = 0.88; 

    const voices = window.speechSynthesis.getVoices();
    const baymaxVoice = voices.find(v => v.name.includes("Google US English") || v.name.includes("Natural") || v.lang.startsWith("en"));
    if (baymaxVoice) {
      utterance.voice = baymaxVoice;
    }

    const faceEl = document.getElementById("baymax-face");
    const moodEl = document.getElementById("companion-mood");

    utterance.onstart = () => {
      if (faceEl) faceEl.classList.add("face-talking");
      if (moodEl) moodEl.innerText = "STATUS: TALKING";
    };

    utterance.onend = () => {
      if (faceEl) faceEl.classList.remove("face-talking");
      if (moodEl) moodEl.innerText = "STATUS: ACTIVE // WAITING";
    };

    utterance.onerror = () => {
      if (faceEl) faceEl.classList.remove("face-talking");
    };

    ttsUtteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  // Speak welcome on load
  useEffect(() => {
    const welcome = "Hello, I am Baymax, your personal healthcare companion. I was alerted to a need for medical attention. Please select a body scan region or describe your symptoms.";
    const timer = setTimeout(() => {
      speak(welcome);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  // ==========================================================================
  // Browser Speech Recognition
  // ==========================================================================
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.lang = 'en-US';
      rec.interimResults = false;

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        
        // Append user block
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages(prev => [...prev, { role: 'user', text: transcript, time: timeStr }]);
        submitUserMessage(transcript);
      };

      rec.onerror = (e) => {
        console.error("Speech Recognition Error:", e);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const toggleSpeechRecognition = () => {
    initAudio();
    playBeep(660, 0.05, "triangle", 0.03);

    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      window.speechSynthesis.cancel();
      recognitionRef.current?.start();
    }
  };

  // ==========================================================================
  // Wearable Vitals Sync
  // ==========================================================================
  const syncWearable = () => {
    setIsSyncing(true);
    playSyncChirp();

    fetch("/api/wearable")
      .then(res => res.json())
      .then(data => {
        setTimeout(() => {
          setBpm(data.heart_rate);
          setSpo2(data.spo2);
          setSteps(data.steps_today);
          setSleep(data.sleep_hours);
          setSyncTime(new Date(data.last_sync).toLocaleTimeString());
          setIsSyncing(false);
          playSyncChirp();
        }, 1000);
      })
      .catch(err => {
        console.error("Wearable sync failed:", err);
        setIsSyncing(false);
      });
  };

  // Sync once on boot
  useEffect(() => {
    syncWearable();
  }, []);

  // ==========================================================================
  // Region Selector / Emergency Dispatch
  // ==========================================================================
  const fetchEmergencyNumbers = (selRegion) => {
    fetch(`/api/emergency?region=${selRegion}`)
      .then(res => res.json())
      .then(data => {
        setEmergNumbers({
          police: data.police,
          ambulance: data.ambulance,
          note: data.note
        });
      })
      .catch(e => console.warn(e));
  };

  useEffect(() => {
    fetchEmergencyNumbers(activeRegion);
  }, [activeRegion]);

  // Handle emergency panic sweep loop
  useEffect(() => {
    if (isPanicActive) {
      playPanicSweep();
      panicIntervalRef.current = setInterval(playPanicSweep, 800);
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const alertUtterance = new SpeechSynthesisUtterance("Warning. Emergency protocol activated. Please contact local emergency services immediately.");
        alertUtterance.rate = 0.9;
        window.speechSynthesis.speak(alertUtterance);
      }
    } else {
      if (panicIntervalRef.current) {
        clearInterval(panicIntervalRef.current);
      }
      window.speechSynthesis.cancel();
    }

    return () => {
      if (panicIntervalRef.current) {
        clearInterval(panicIntervalRef.current);
      }
    };
  }, [isPanicActive]);

  const dismissPanic = () => {
    setIsPanicActive(false);
    playBeep(480, 0.08, "triangle", 0.05);
  };

  // ==========================================================================
  // Webcam & Camera Snapshot Poll
  // ==========================================================================
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240 }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraActive(true);
      
      const faceEl = document.getElementById("baymax-face");
      const moodEl = document.getElementById("companion-mood");
      if (faceEl) faceEl.classList.add("face-scanning");
      if (moodEl) moodEl.innerText = "STATUS: SCANNING PATIENT";

      // Setup drawing overlays
      if (overlayCanvasRef.current) {
        overlayCanvasRef.current.width = videoRef.current.clientWidth || 320;
        overlayCanvasRef.current.height = videoRef.current.clientHeight || 240;
      }

      cameraIntervalRef.current = setInterval(evaluateWebcamSnapshot, 2500);
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, {
        role: 'system',
        text: "System Alert: Webcam permissions denied. Mood scanner offline.",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    }
  };

  const stopCamera = () => {
    const stream = videoRef.current?.srcObject;
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
    setEmotion("N/A");
    setFaceBox(null);
    clearInterval(cameraIntervalRef.current);

    const faceEl = document.getElementById("baymax-face");
    const moodEl = document.getElementById("companion-mood");
    if (faceEl) faceEl.classList.remove("face-scanning");
    if (moodEl) moodEl.innerText = "STATUS: ACTIVE // WAITING";

    const canvas = overlayCanvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  const evaluateWebcamSnapshot = () => {
    const video = videoRef.current;
    if (!video || video.readyState !== video.HAVE_ENOUGH_DATA) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64Data = canvas.toDataURL("image/jpeg");

    fetch("/api/detect-emotion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64Data })
    })
      .then(res => res.json())
      .then(data => {
        const overlayCanvas = overlayCanvasRef.current;
        if (!overlayCanvas) return;
        const octx = overlayCanvas.getContext('2d');
        octx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (data.emotion && data.emotion !== "none" && data.emotion !== "no_frame") {
          const label = data.emotion.toUpperCase();
          const score = (data.score * 100).toFixed(0);
          setEmotion(`${label} (${score}%)`);

          if (data.face_box) {
            const box = data.face_box;
            const scaleX = overlayCanvas.width / video.videoWidth;
            const scaleY = overlayCanvas.height / video.videoHeight;
            
            // Draw reticle
            octx.strokeStyle = "#00e5ff";
            octx.lineWidth = 2;
            octx.strokeRect(box[0] * scaleX, box[1] * scaleY, box[2] * scaleX, box[3] * scaleY);
            
            octx.fillStyle = "#00e5ff";
            octx.font = "10px Plus Jakarta Sans";
            octx.fillText(`${label} ${score}%`, box[0] * scaleX, (box[1] * scaleY) - 5);
          }
        } else {
          setEmotion("NEUTRAL (100%)");
        }
      })
      .catch(e => console.warn("Emotion evaluate error:", e));
  };

  useEffect(() => {
    return () => {
      clearInterval(cameraIntervalRef.current);
    };
  }, []);

  // ==========================================================================
  // Interactive Body Scanner SVG target click
  // ==========================================================================
  const handleBodyPartClick = (part) => {
    playBeep(1100, 0.06, "sine", 0.05);
    setSelectedBodyPart(part);
    
    const coord = BODY_PART_COORDS[part];
    if (coord) {
      setReticlePos({ x: coord.x, y: coord.y, visible: true });
    }

    if (BODY_PART_SYMPTOMS[part]) {
      setInputText(BODY_PART_SYMPTOMS[part]);
    }
  };

  // ==========================================================================
  // Chat Operations & SSE Streaming completions
  // ==========================================================================
  const appendMessage = (role, text) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { role, text, time: timeStr }]);
  };

  const handleSend = () => {
    const text = inputText.trim();
    if (!text || isGenerating) return;

    playBeep(880, 0.05, "triangle", 0.03);
    setInputText("");
    appendMessage("user", text);
    submitUserMessage(text);
  };

  const handleCancelGeneration = () => {
    playBeep(220, 0.1, "triangle", 0.05);
    if (sseReaderRef.current) {
      sseReaderRef.current.cancel();
      setIsGenerating(false);
      appendMessage("system", "Transmission aborted by patient override.");
      window.speechSynthesis.cancel();
    }
  };

  const submitUserMessage = (userText) => {
    setIsGenerating(true);
    
    // Vitals warning updater
    const updateWarnings = (newSpo2) => {
      const card = document.querySelector(".wearable-card");
      if (card) {
        if (newSpo2 < 90) card.className = "card wearable-card danger-sp";
        else if (newSpo2 < 95) card.className = "card wearable-card warning-sp";
        else card.className = "card wearable-card";
      }
    };

    // A. Context-aware overrides
    const lower = userText.toLowerCase();
    if (lower.match(/\b(racing|chest pain|heart beat|scared|panicking|palpitation|running|jogging|marathon|stress)\b/)) {
      setBpm(135);
      playBeep(380, 0.1, "sine", 0.08);
      setTimeout(() => playBeep(380, 0.1, "sine", 0.08), 150);
      const moodEl = document.getElementById("companion-mood");
      if (moodEl) moodEl.innerText = "WARNING: BIOMETRICS ELEVATED";
      appendMessage("system", "⚠️ Patient vitals anomaly detected (Heart Rate spike). Context-aware override sync active.");
    } else if (lower.match(/\b(fever|hot|sweating|cold|chills)\b/)) {
      setSpo2(93);
      playWarningChirp();
      const moodEl = document.getElementById("companion-mood");
      if (moodEl) moodEl.innerText = "WARNING: PATIENT INSTABILITY";
      setTimeout(() => updateWarnings(93), 200);
      appendMessage("system", "⚠️ Patient vitals anomaly detected (SpO2 drop). Context-aware override sync active.");
    }

    // B. Symptom & drug lookup API
    fetch("/api/analyze-symptoms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: userText })
    })
      .then(res => res.json())
      .then(data => {
        // Update database panels
        if (data.clinical_trials && data.clinical_trials.length > 0) {
          setTrials(data.clinical_trials);
        } else {
          setTrials([]);
        }

        if (data.drug_facts && data.drug_facts.name) {
          setFdaAlert(data.drug_facts);
        } else {
          setFdaAlert(null);
        }

        // Trigger Panic Overlay if emergency detected
        if (data.emergency && data.emergency.is_emergency) {
          setIsPanicActive(true);
        }
      })
      .catch(err => console.error("Symptom evaluation issue:", err));

    // C. Ollama completion SSE stream
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: userText })
    })
      .then(res => {
        if (!res.body) throw new Error("SSE Stream connection failed.");
        
        // Append empty baseline message to compile stream chunk-by-chunk
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setMessages(prev => [...prev, { role: 'baymax', text: "", time: timeStr }]);

        const reader = res.body.getReader();
        sseReaderRef.current = reader;
        const decoder = new TextDecoder();
        let accumulated = "";

        const read = () => {
          reader.read().then(({ done, value }) => {
            if (done) {
              setIsGenerating(false);
              speak(accumulated);
              return;
            }

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n");
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const dataStr = line.slice(6).trim();
                if (dataStr === "[DONE]") {
                  setIsGenerating(false);
                  speak(accumulated);
                  return;
                }
                try {
                  const parsed = JSON.parse(dataStr);
                  if (parsed.text) {
                    accumulated += parsed.text;
                    
                    // Update the last element in state array
                    setMessages(prev => {
                      const updated = [...prev];
                      if (updated.length > 0) {
                        updated[updated.length - 1].text = accumulated;
                      }
                      return updated;
                    });
                  }
                } catch(e) {}
              }
            }
            read();
          }).catch(err => {
            console.error(err);
            setIsGenerating(false);
          });
        };
        read();
      })
      .catch(err => {
        console.error(err);
        appendMessage("system", `Database communication failure: ${err.message}`);
        setIsGenerating(false);
      });
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Formatter for simple markdown links
  const formatMarkdown = (text) => {
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/`(.*?)`/g, "<code>$1</code>");
    return html;
  };

  return (
    <>
      {/* 120fps Holo Mesh grid */}
      <HoloBackground />

      <div className="app-container">
        
        {/* HEADER */}
        <header className="app-header">
          <div className="header-logo">
            <div className="logo-circle"></div>
            <h1>BAYMAX <span className="header-subtitle">// PERSONAL HEALTH COMPANION</span></h1>
          </div>
          <div className="header-controls">
            <div className="status-indicator">
              <span className="status-dot green" id="ollama-dot"></span>
              <span className="status-text" id="ollama-text">Ollama: ONLINE</span>
            </div>
            <div className="region-selector">
              <label>REGION:</label>
              <select value={activeRegion} onChange={(e) => setActiveRegion(e.target.value)}>
                <option value="india">INDIA (112/108)</option>
                <option value="us_uk">US/UK (911/999)</option>
                <option value="global">GLOBAL (112)</option>
              </select>
            </div>
          </div>
        </header>

        {/* MAIN HUD GRID */}
        <div className="hud-grid">
          
          {/* LEFT COLUMN */}
          <aside className="grid-panel panel-left">
            
            {/* Hologram Link */}
            <div className="card face-card">
              <div className="card-header">
                <span className="card-tag">// COMPANION HUBLINK</span>
                <h3>BAYMAX TELEMETRY</h3>
              </div>
              <div className="baymax-face-container">
                <div className="hologram-hud">
                  <div className="hud-ring ring-outer"></div>
                  <div className="hud-ring ring-middle"></div>
                  <div className="hud-ring ring-inner"></div>
                  <svg viewBox="0 0 200 80" className="baymax-face-svg" id="baymax-face">
                    <circle cx="50" cy="40" r="10" className="baymax-eye" id="left-eye"/>
                    <line x1="50" y1="40" x2="150" y2="40" className="baymax-eye-line"/>
                    <circle cx="150" cy="40" r="10" className="baymax-eye" id="right-eye"/>
                  </svg>
                </div>
                <div className="companion-status" id="companion-mood">STATUS: ACTIVE // WAITING</div>
              </div>
            </div>

            {/* Canvas ECG heartbeat */}
            <div className="card ecg-card">
              <div className="card-header">
                <span className="card-tag">// CARDIAC MONITOR</span>
                <h3>ECG HEARTWAVE</h3>
              </div>
              <div className="ecg-container">
                <EcgMonitor bpm={bpm} spo2={spo2} playHeartbeatClick={playHeartbeatClick} />
                <div className="ecg-metrics">
                  <span className="metric-label">SYS RATE:</span>
                  <span className="metric-val" id="ecg-bpm">{bpm} BPM</span>
                </div>
              </div>
            </div>

            {/* Interactive Body Scanner */}
            <div className="card body-card">
              <div className="card-header">
                <span className="card-tag">// TARGET ANALYSIS</span>
                <h3>BODY MAP SCANNER</h3>
              </div>
              <div className="body-scanner-container">
                <div className="laser-scanner-line"></div>
                
                {/* Dynamic Lock reticle snapping using Framer Motion */}
                <AnimatePresence>
                  {reticlePos.visible && (
                    <motion.div 
                      key={selectedBodyPart}
                      className="body-scanner-reticle"
                      initial={{ opacity: 0, scale: 2 }}
                      animate={{ 
                        opacity: 0.85, 
                        scale: 1,
                        x: (reticlePos.x * 1.8) - 15, // Map grid scale to SVG dimensions
                        y: (reticlePos.y * 0.9) - 15
                      }}
                      exit={{ opacity: 0, scale: 0.5 }}
                      transition={{ type: "spring", damping: 18, stiffness: 220 }}
                      style={{
                        position: 'absolute',
                        width: '30px',
                        height: '30px',
                        border: '1.5px dashed #00e5ff',
                        borderRadius: '50%',
                        top: 0,
                        left: 0,
                        pointerEvents: 'none',
                        zIndex: 20
                      }}
                    />
                  )}
                </AnimatePresence>

                <svg viewBox="0 0 100 220" className="body-map-svg">
                  <circle 
                    cx="50" cy="25" r="12" 
                    className={`body-part ${selectedBodyPart === 'Head' ? 'active' : ''}`} 
                    onClick={() => handleBodyPartClick("Head")}
                  />
                  <text x="50" y="27" className="body-part-label">HEAD</text>
                  
                  <rect 
                    x="47" y="38" width="6" height="8" 
                    className={`body-part ${selectedBodyPart === 'Throat' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Throat")}
                  />
                  
                  <path 
                    d="M 32 48 L 68 48 L 60 115 L 40 115 Z" 
                    className={`body-part ${selectedBodyPart === 'Chest' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Chest")}
                  />
                  <text x="50" y="80" className="body-part-label">CHEST</text>
                  
                  <path 
                    d="M 40 116 L 60 116 L 56 150 L 44 150 Z" 
                    className={`body-part ${selectedBodyPart === 'Abdomen' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Abdomen")}
                  />
                  <text x="50" y="135" className="body-part-label">ABDOMEN</text>
                  
                  <path 
                    d="M 30 48 L 18 110 L 25 110 L 34 60 Z" 
                    className={`body-part ${selectedBodyPart === 'Arms' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Arms")}
                  />
                  <path 
                    d="M 70 48 L 82 110 L 75 110 L 66 60 Z" 
                    className={`body-part ${selectedBodyPart === 'Arms' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Arms")}
                  />
                  
                  <path 
                    d="M 43 151 L 40 215 L 47 215 L 49 151 Z" 
                    className={`body-part ${selectedBodyPart === 'Legs' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Legs")}
                  />
                  <path 
                    d="M 57 151 L 60 215 L 53 215 L 51 151 Z" 
                    className={`body-part ${selectedBodyPart === 'Legs' ? 'active' : ''}`}
                    onClick={() => handleBodyPartClick("Legs")}
                  />
                </svg>
                <div className="body-scan-info">
                  <p>Tap wireframe sections to target diagnostic scans</p>
                  <span id="selected-part-display">Target: {selectedBodyPart.toUpperCase()}</span>
                </div>
              </div>
            </div>
          </aside>

          {/* CENTER PANEL */}
          <main className="grid-panel panel-center">
            <div className="card terminal-card">
              <div className="card-header">
                <span className="card-tag">// COMPANION INTERFACE</span>
                <h3>BAYMAX DIAGNOSTIC TERMINAL</h3>
              </div>
              
              {/* Chat window with fluid Framer Motion slide-up */}
              <div className="chat-log">
                <AnimatePresence initial={false}>
                  {messages.map((msg, i) => (
                    <motion.div 
                      key={i}
                      className={`message message-${msg.role}`}
                      initial={{ opacity: 0, y: 12, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ type: "spring", stiffness: 240, damping: 22 }}
                    >
                      <span className="message-meta">
                        {msg.role === 'user' ? `PATIENT // ${msg.time}` : 
                         msg.role === 'system' ? `SYSTEM GLITCH // ${msg.time}` : `BAYMAX COMPANION // ${msg.time}`}
                      </span>
                      <div className="message-text" dangerouslySetInnerHTML={{ __html: formatMarkdown(msg.text) }} />
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={chatEndRef} />
              </div>

              <div className="chat-status-bar">
                <div className={`speech-status ${isGenerating || isListening ? 'active' : ''}`}>
                  <span className="speech-icon">●</span> 
                  <span>{isListening ? 'LISTENING TO MICROPHONE...' : isGenerating ? 'TRANSMITTING SSE CHUNKS...' : 'SYSTEM STANDBY'}</span>
                </div>
                {isGenerating && (
                  <button onClick={handleCancelGeneration} className="btn btn-danger btn-sm">
                    <Square size={11} fill="white" /> CANCEL
                  </button>
                )}
              </div>

              {/* Tag shortcuts */}
              <div className="symptom-tag-container">
                <button className="symptom-tag" onClick={() => { appendMessage("user", "Chest Pain"); submitUserMessage("Chest Pain"); }}>🫀 Chest Pain</button>
                <button className="symptom-tag" onClick={() => { appendMessage("user", "Fever & Cough"); submitUserMessage("Fever & Cough"); }}>🌡️ Fever & Cough</button>
                <button className="symptom-tag" onClick={() => { appendMessage("user", "Migraine Headache"); submitUserMessage("Migraine & headache"); }}>🤕 Migraine</button>
                <button className="symptom-tag" onClick={() => { appendMessage("user", "Metformin Facts"); submitUserMessage("Metformin facts"); }}>💊 Metformin Info</button>
                <button className="symptom-tag" onClick={() => { appendMessage("user", "Aspirin Warnings"); submitUserMessage("Aspirin warnings"); }}>💊 Aspirin Warnings</button>
              </div>

              {/* Controls footer */}
              <div className="chat-input-area">
                <input 
                  type="text" 
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask Baymax about symptoms or drug brands..." 
                  disabled={isGenerating}
                />
                <button 
                  onClick={toggleSpeechRecognition} 
                  className={`btn btn-secondary ${isListening ? 'btn-danger' : ''}`}
                  title="Voice dictation"
                >
                  <Mic size={15} /> {isListening ? 'STOP' : 'SPEAK'}
                </button>
                <button onClick={handleSend} className="btn btn-primary" disabled={isGenerating}>
                  <Send size={15} /> SEND
                </button>
              </div>
            </div>
          </main>

          {/* RIGHT COLUMN */}
          <aside className="grid-panel panel-right">
            
            {/* Webcam / Emotion evaluations */}
            <div className="card camera-card">
              <div className="card-header">
                <span className="card-tag">// COMPUTER VISION</span>
                <h3>FACIAL EMOTION SCANNER</h3>
              </div>
              <div className="camera-stream-container">
                <video ref={videoRef} autoPlay playsInline muted id="webcam-video" className={isCameraActive ? '' : 'hidden'}></video>
                <canvas ref={overlayCanvasRef} id="camera-overlay" className={isCameraActive ? '' : 'hidden'}></canvas>
                <div className="scanlines"></div>
                {!isCameraActive && (
                  <div className="camera-placeholder">
                    <span className="placeholder-icon">📷</span>
                    <span>PATIENT CAMERA OFFLINE</span>
                  </div>
                )}
              </div>
              <div className="camera-controls">
                <button 
                  className={`btn btn-secondary btn-sm ${isCameraActive ? 'btn-danger' : ''}`}
                  onClick={() => isCameraActive ? stopCamera() : startCamera()}
                >
                  {isCameraActive ? 'DEACTIVATE MOOD CAMERA' : 'ACTIVATE MOOD CAMERA'}
                </button>
                <span className="emotion-badge">MOOD: {emotion}</span>
              </div>
            </div>

            {/* Wearable Sync + Manual controls */}
            <div className="card wearable-card">
              <div className="card-header">
                <span className="card-tag">// BIOSIGNS GATEWAY</span>
                <h3>HEALTH BAND GATEWAY</h3>
              </div>
              <div className="wearable-grid">
                <div className="wearable-stat">
                  <span className="stat-icon pulse">❤️</span>
                  <div className="stat-info">
                    <span className="stat-val">{bpm} BPM</span>
                    <span className="stat-lbl">HEART RATE</span>
                  </div>
                </div>
                <div className="wearable-stat">
                  <span className="stat-icon">💧</span>
                  <div className="stat-info">
                    <span className="stat-val">{spo2} %</span>
                    <span className="stat-lbl">SPO2 LEVEL</span>
                  </div>
                </div>
                <div className="wearable-stat">
                  <span className="stat-icon">🏃</span>
                  <div className="stat-info">
                    <span className="stat-val">{steps.toLocaleString()}</span>
                    <span className="stat-lbl">STEPS TODAY</span>
                  </div>
                </div>
                <div className="wearable-stat">
                  <span className="stat-icon">🌙</span>
                  <div className="stat-info">
                    <span className="stat-val">{sleep} HRS</span>
                    <span className="stat-lbl">SLEEP SYNC</span>
                  </div>
                </div>
              </div>

              {/* Slider overrides */}
              <div className="vitals-override-panel">
                <div 
                  className={`override-header ${isOverrideOpen ? 'open' : ''}`}
                  onClick={() => {
                    initAudio();
                    playBeep(780, 0.05, "triangle", 0.03);
                    setIsOverrideOpen(!isOverrideOpen);
                  }}
                >
                  <span>🛠️ MANUAL VITALS CONTROLLER</span>
                  <span className="chevron">▼</span>
                </div>
                <motion.div 
                  className="override-controls"
                  initial={false}
                  animate={{ height: isOverrideOpen ? 'auto' : 0, opacity: isOverrideOpen ? 1 : 0 }}
                  transition={{ type: "spring", damping: 20, stiffness: 220 }}
                  style={{ overflow: 'hidden' }}
                >
                  <div className="slider-group" style={{ marginBottom: '10px' }}>
                    <label>
                      <span>HEART RATE:</span>
                      <span>{bpm} BPM</span>
                    </label>
                    <input 
                      type="range" 
                      min="40" max="180" 
                      value={bpm} 
                      onChange={(e) => setBpm(parseInt(e.target.value))}
                      className="vitals-slider"
                    />
                  </div>
                  <div className="slider-group">
                    <label>
                      <span>SPO2 LEVEL:</span>
                      <span>{spo2} %</span>
                    </label>
                    <input 
                      type="range" 
                      min="80" max="100" 
                      value={spo2} 
                      onChange={(e) => {
                        const val = parseInt(e.target.value);
                        setSpo2(val);
                        
                        // Handle warning chirps on drag
                        if (val < 90) playWarningChirp();
                        else if (val < 95) playBeep(330, 0.1, "sine", 0.08);
                      }}
                      className="vitals-slider"
                    />
                  </div>
                </motion.div>
              </div>

              <div className="wearable-sync-bar">
                <button className="btn btn-secondary btn-block" onClick={syncWearable} disabled={isSyncing}>
                  <RefreshCw size={13} className={isSyncing ? 'anim-spin' : ''} /> {isSyncing ? 'SYNCING BIOSIGNS...' : 'SYNC HEALTH BAND'}
                </button>
                <span className="sync-time">Sync: {syncTime}</span>
              </div>
            </div>

            {/* Medical Evidence search */}
            <div className="card insights-card">
              <div className="card-header">
                <span className="card-tag">// CLINICAL REGISTRIES</span>
                <h3>DATABASE RESEARCH INSIGHTS</h3>
              </div>
              <div className="insights-body">
                {trials.length === 0 && !fdaAlert ? (
                  <div className="empty-insights">
                    Ask Baymax questions about symptoms or drug generic components to cross-reference ClinicalTrials.gov and OpenFDA labeling warnings.
                  </div>
                ) : (
                  <div className="insights-content">
                    {/* FDA Details */}
                    {fdaAlert && (
                      <motion.div 
                        className="insight-section"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ type: "spring", damping: 20 }}
                      >
                        <h4 className="insight-subtitle">💊 OpenFDA Drug Facts</h4>
                        <div className="fda-details">
                          <p><strong>Brand:</strong> {fdaAlert.brand_name}</p>
                          <p><strong>Generic:</strong> {fdaAlert.generic_name}</p>
                          <p><strong>Warnings:</strong> <span className="scroll-p">{fdaAlert.warnings}</span></p>
                          <p><strong>Indications:</strong> <span className="scroll-p">{fdaAlert.indications_and_usage}</span></p>
                        </div>
                      </motion.div>
                    )}

                    {/* Recruiting Clinical Trials */}
                    {trials.length > 0 && (
                      <motion.div 
                        className="insight-section"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ type: "spring", damping: 20 }}
                      >
                        <h4 className="insight-subtitle">🔬 ClinicalTrials.gov Recruits</h4>
                        <ul className="trials-list">
                          {trials.map((trial, index) => (
                            <li key={index}>
                              <a href={trial.link} target="_blank" rel="noreferrer" className="trial-link">
                                {trial.nct_id}
                              </a>: <span>{trial.title}</span>
                              <div className="trial-meta">Status: {trial.status} | Sponsor: {trial.sponsor}</div>
                            </li>
                          ))}
                        </ul>
                      </motion.div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Emergency panel */}
            <div className="card emergency-card">
              <div className="card-header">
                <span className="card-tag">// EMERGENCY DISPATCH</span>
                <h3>CRITICAL SERVICES</h3>
              </div>
              <div className="emergency-body">
                <div className="emergency-numbers">
                  <div className="emerg-col">
                    <span className="emerg-label">AMBULANCE</span>
                    <span className="emerg-val">{emergNumbers.ambulance}</span>
                  </div>
                  <div className="emerg-col">
                    <span className="emerg-label">POLICE / ALL</span>
                    <span className="emerg-val">{emergNumbers.police}</span>
                  </div>
                </div>
                <button onClick={() => setIsPanicActive(true)} className="btn btn-danger btn-block pulsing">
                  TRIGGER PANIC ALERT
                </button>
              </div>
            </div>

          </aside>
        </div>
      </div>

      {/* Emergency Modal overlay */}
      <AnimatePresence>
        {isPanicActive && (
          <motion.div 
            className="panic-overlay active"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div 
              className="panic-content"
              initial={{ scale: 0.9, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 15 }}
              transition={{ type: "spring", damping: 22, stiffness: 250 }}
            >
              <div className="panic-logo">⚠️</div>
              <h2>EMERGENCY ANOMALY DETECTED</h2>
              <p>Biometric scans or patient alerts suggest immediate medical danger. If you are alone, call local emergency numbers immediately.</p>
              <div className="panic-numbers-large">
                <div>AMBULANCE: <span>{emergNumbers.ambulance}</span></div>
                <div>POLICE / ALL: <span>{emergNumbers.police}</span></div>
              </div>
              <button className="btn btn-secondary" onClick={dismissPanic}>
                DISMISS ALERT
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
