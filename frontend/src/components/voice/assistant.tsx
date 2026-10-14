"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/providers/auth-provider";
import { Mic } from "lucide-react";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { actionSchema, capabilitiesSchema, replySchema, safeVoiceRoute, transcriptionSchema, type VoiceReply } from "@/lib/voice";
import { useAI } from "@/lib/ai";

export function VoiceAssistant() {
  const { session, user } = useAuth();
  const status = useAI("/api/v1/voice/status", capabilitiesSchema);
  const [text, setText] = useState("");
  const [language, setLanguage] = useState<"en" | "fr" | "auto">("en");
  const [notice, setNotice] = useState("Microphone permission required. You can type a command instead.");
  const [failure, setFailure] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [turns, setTurns] = useState<VoiceReply[]>([]);
  const [pending, setPending] = useState<VoiceReply | null>(null);
  const [result, setResult] = useState<zAction | null>(null);
  const [playing, setPlaying] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const bytes = useRef(0);
  const sessionId = useRef<string | null>(null);
  const active = useRef(false);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const recordTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  function invalidate() { generation.current++; }
  function stopPlayback(clear = false) {
    if (audio.current) { audio.current.pause(); audio.current.currentTime = 0; }
    setPlaying(false);
    if (clear) { if (audioUrl.current) URL.revokeObjectURL(audioUrl.current); audioUrl.current = null; audio.current = null; setAudioReady(false); }
  }
  function releaseMicrophone() { if (recordTimer.current) clearTimeout(recordTimer.current); stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; }
  function cancelRecording() {
    generation.current++; controller.current?.abort();
    if (recorder.current?.state === "recording") { recorder.current.onstop = null; recorder.current.stop(); }
    releaseMicrophone(); chunks.current = []; setRecording(false); active.current = false; setBusy(false); setNotice("Recording cancelled. Audio was not submitted.");
  }
  useEffect(() => {
    const key = "codemate-voice-session-" + user?.id;
    sessionId.current = sessionStorage.getItem(key);
    if (sessionId.current) session.get("/api/v1/voice/sessions/" + sessionId.current, replySchema.array()).then(setTurns).catch(() => { sessionId.current = null; sessionStorage.removeItem(key); });
    return () => { invalidate(); if (recordTimer.current) clearTimeout(recordTimer.current); controller.current?.abort(); if (recorder.current?.state === "recording") { recorder.current.onstop = null; recorder.current.stop(); } stream.current?.getTracks().forEach(track => track.stop()); audio.current?.pause(); if (audioUrl.current) URL.revokeObjectURL(audioUrl.current); };
  }, [session, user?.id]);
  useEffect(() => { if (pending) dialog.current?.showModal(); else dialog.current?.close(); }, [pending]);
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => setSeconds(value => value + 1), 1000);
    return () => clearInterval(timer);
  }, [recording]);
  async function record() {
    if (active.current) return;
    active.current = true; const current = ++generation.current;
    stopPlayback(true); setBusy(true); setFailure(""); setNotice("Requesting microphone permission...");
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") throw new Error("Browser recording is unavailable. Use typed commands.");
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (current !== generation.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find(type => MediaRecorder.isTypeSupported(type));
      if (!mime) throw new Error("No supported recording format. Use typed commands.");
      const capture = new MediaRecorder(media, { mimeType: mime }); recorder.current = capture; chunks.current = []; bytes.current = 0;
      capture.ondataavailable = event => {
        bytes.current += event.data.size;
        if (bytes.current > (status.data?.max_upload_bytes || 8388608)) { cancelRecording(); setFailure("Recording is too large. Record a shorter command."); return; }
        if (event.data.size) chunks.current.push(event.data);
      };
      capture.onerror = () => { cancelRecording(); setFailure("Recording failed. Check microphone permissions or use typed commands."); };
      capture.onstop = async () => {
        releaseMicrophone(); setRecording(false);
        if (current !== generation.current) return;
        setBusy(true); setNotice("Transcribing locally..."); controller.current = new AbortController();
        try {
          const blob = new Blob(chunks.current, { type: mime }); chunks.current = [];
          const response = await session.uploadAudio(blob, language, transcriptionSchema, controller.current.signal);
          if (current !== generation.current) return;
          setText(response.text); setNotice("Transcription ready. Review and edit it before sending.");
        } catch (error) { if (current === generation.current) setFailure(apiErrorMessage(error)); }
        finally { if (current === generation.current) { setBusy(false); active.current = false; } }
      };
      recordTimer.current = setTimeout(() => { if (capture.state === "recording") { capture.stop(); setRecording(false); releaseMicrophone(); } }, (status.data?.max_recording_seconds || 30) * 1000);
      capture.start(500); setBusy(false); setSeconds(0); setRecording(true); setNotice("Recording... Press Stop to transcribe or Cancel to discard.");
    } catch (error) { releaseMicrophone(); active.current = false; setBusy(false); if (current !== generation.current) return; setFailure(error instanceof DOMException && error.name === "NotAllowedError" ? "Microphone permission denied. Allow microphone access in browser settings or type a command." : error instanceof Error ? error.message : "Microphone unavailable."); }
  }
  async function send() {
    if (active.current || !text.trim()) return;
    active.current = true; setBusy(true); stopPlayback(true); setFailure(""); setResult(null); setNotice("Understanding your request and fetching authorized data...");
    try {
      const reply = await session.post("/api/v1/auth/voice/command", replySchema, { text: text.trim(), request_id: crypto.randomUUID(), session_id: sessionId.current });
      sessionId.current = reply.session_id; sessionStorage.setItem("codemate-voice-session-" + user?.id, reply.session_id);
      setTurns(previous => [...previous, reply].slice(-20));
      setNotice(reply.confirmation_required ? "Confirmation required. No investigation has started." : "Request completed.");
      if (reply.confirmation_required) setPending(reply);
    } catch (error) { setFailure(apiErrorMessage(error)); }
    finally { setBusy(false); active.current = false; }
  }
  async function confirm(cancel = false) {
    if (active.current || !pending) return;
    active.current = true; setBusy(true); setFailure(""); setNotice(cancel ? "Cancelling pending action..." : "Starting investigation...");
    try {
      const response = await session.post(cancel ? "/api/v1/auth/voice/cancel" : "/api/v1/auth/voice/confirm", actionSchema, { session_id: pending.session_id, action_id: pending.action_id });
      setResult(response); setPending(null); setNotice(response.message);
    } catch (error) {
      setFailure(apiErrorMessage(error));
      if (error instanceof ApiError && ["VOICE_ACTION_EXPIRED", "VOICE_SESSION_EXPIRED", "VOICE_ACTION_UNAVAILABLE", "VOICE_CONNECTION_CHANGED", "VOICE_TARGET_CHANGED"].includes(error.code || "")) { setPending(null); setNotice("Pending action is unavailable. Select the workflow again."); }
    }
    finally { active.current = false; setBusy(false); }
  }
  async function speak() {
    if (active.current || !turns.length) return;
    active.current = true; setBusy(true); setFailure(""); stopPlayback(true); setNotice("Generating voice response...");
    try {
      const latest = turns[turns.length - 1];
      const blob = await session.post<Blob>("/api/v1/auth/voice/speech", undefined, { session_id: latest.session_id, turn_id: latest.turn_id });
      audioUrl.current = URL.createObjectURL(blob); audio.current = new Audio(audioUrl.current); audio.current.onended = () => setPlaying(false); setAudioReady(true); setNotice("Voice response ready. Press Play.");
    } catch (error) { setFailure(apiErrorMessage(error)); }
    finally { active.current = false; setBusy(false); }
  }
  async function play() { try { await audio.current?.play(); setPlaying(true); } catch { setFailure("Playback was blocked. Press Play again or check browser audio permissions."); } }
  function fresh() { sessionId.current = null; sessionStorage.removeItem("codemate-voice-session-" + user?.id); setTurns([]); setResult(null); setText(""); setNotice("New conversation ready."); stopPlayback(true); }
  return <div className="ai-page voice-page">
    <div className="page-heading"><div><span className="eyebrow">LOCAL VOICE WORKSPACE</span><h1>Voice Agent</h1><p>Speak or type, review your request, and use authorized CodeMate tools.</p></div></div>
    <section className="card voice-card"><h2>Local services</h2>
      {status.isPending ? <p>Checking services...</p> : status.isError ? <p role="alert">{apiErrorMessage(status.error)}</p> : <><p>Speech model: {status.data?.stt_installed ? "Installed" : "Unavailable"} | Piper voice: {status.data?.tts_installed ? "Installed" : "Unavailable"} | Ollama: {status.data?.ollama_available ? "Ready" : "Unavailable"}</p><p>{status.data?.message}</p></>}
      <button className="button secondary" disabled={status.isFetching} onClick={() => void status.refetch()}>Check services</button>
      <p>Speech is processed locally. Raw audio is not stored. GitHub commands require network access. Models need an initial download. This agent cannot modify repositories or deploy code.</p>
    </section>
    <section className="card voice-card"><h2>Your command</h2><label>Transcription language <select aria-label="Transcription language" value={language} disabled={busy || recording} onChange={event => setLanguage(event.target.value as typeof language)}><option value="en">English</option><option value="fr">French</option><option value="auto">Auto</option></select></label>
      <div className="github-toolbar"><button className="button primary voice-microphone" disabled={busy || recording || pending !== null} onClick={() => void record()}><Mic aria-hidden="true" size={20} />Start recording</button><button className="button secondary" disabled={!recording} onClick={() => { recorder.current?.stop(); setRecording(false); releaseMicrophone(); }}>Stop recording</button><button className="button secondary" disabled={!recording && notice !== "Transcribing locally..." && notice !== "Requesting microphone permission..."} onClick={cancelRecording}>Cancel recording</button><span>{recording ? "Recording: " + seconds + " seconds" : "Microphone idle"}</span></div>
      <label className="voice-transcript">Editable transcription or typed command<textarea maxLength={1000} value={text} disabled={busy} onChange={event => setText(event.target.value)} placeholder="CodeMate, open my GitHub repositories." /></label>
      <div className="github-toolbar"><button className="button primary" disabled={busy || recording || !text.trim() || pending !== null} onClick={() => void send()}>Send text command</button><button className="button secondary" disabled={busy || recording || pending !== null} onClick={fresh}>New conversation</button></div>
      <p role="status" aria-live="polite" aria-atomic="true">{notice}</p>{failure && <p role="alert">{failure}</p>}
    </section>
    <section className="card voice-card"><h2>Assistant response</h2>{!turns.length && <p>Try opening a page, listing repositories, checking a pipeline, or asking what the agent can do.</p>}
      {turns.map(turn => { const route = safeVoiceRoute(turn.route); return <article key={turn.turn_id} className="voice-turn"><p>{turn.message}</p>{turn.target && <p>{turn.target.owner}/{turn.target.repo} | Run {turn.target.workflow_run_id} | {turn.target.status} | {turn.target.conclusion}</p>}{route && <Link href={route}>Open relevant page</Link>}{turn.choices.map(choice => <button className="button secondary" key={choice} disabled={busy} onClick={() => setText("Select repository " + choice)}>{choice}</button>)}</article>; })}
      {result && <p>{result.message} {safeVoiceRoute(result.route) && <Link href={safeVoiceRoute(result.route)!}>Open investigation report</Link>}</p>}
      <div className="github-toolbar"><button className="button secondary" disabled={busy || recording || !turns.length || !status.data?.tts_installed} onClick={() => void speak()}>Generate voice response</button><button className="button secondary" disabled={!audioReady || playing} onClick={() => void play()}>Play</button><button className="button secondary" disabled={!playing} onClick={() => { audio.current?.pause(); setPlaying(false); }}>Pause</button><button className="button secondary" disabled={!audioReady} onClick={() => stopPlayback()}>Stop playback</button><button className="button secondary" disabled={!audioReady} onClick={() => { stopPlayback(); void play(); }}>Replay</button></div>
    </section>
    <dialog ref={dialog} className="github-dialog" aria-labelledby="voice-confirm-title" onCancel={event => { event.preventDefault(); if (!busy) void confirm(true); }}><h2 id="voice-confirm-title">Confirm investigation</h2><p>{pending?.message}</p><p>{pending?.target?.owner}/{pending?.target?.repo} | Run {pending?.target?.workflow_run_id} | {pending?.target?.status} | {pending?.target?.conclusion}</p><p>Only clicking Confirm can start this investigation. Voice-only yes is insufficient.</p>{failure && <p role="alert">{failure}</p>}<button className="button primary" disabled={busy} onClick={() => void confirm()}>Confirm</button><button className="button secondary" disabled={busy} onClick={() => void confirm(true)}>Cancel confirmation</button></dialog>
  </div>;
}
type zAction = { message: string; route: string | null };
