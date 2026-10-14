import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VoiceAssistant } from "@/components/voice/assistant";
import { safeVoiceRoute } from "@/lib/voice";
import { ApiError } from "@/lib/api/client";
const { post, get, uploadAudio } = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn(), uploadAudio: vi.fn() }));
vi.mock("@/providers/auth-provider", () => { const session = { post, get, uploadAudio }; return { useAuth: () => ({ session, user: { id: "voice-user" } }) }; });
vi.mock("@/lib/ai", () => ({ useAI: () => ({ isPending: false, isError: false, isFetching: false, refetch: vi.fn(), data: { enabled: true, stt_installed: true, tts_installed: true, ollama_available: true, max_recording_seconds: 1, max_upload_bytes: 1024, message: "Local processing" } }) }));
const sid = "3c337168-8a43-4f3e-bbaf-cf055ec41101";
const reply = { session_id: sid, turn_id: sid, intent: "navigate", message: "Open your dashboard.", route: "/dashboard", confirmation_required: false, action_id: null, target: null, choices: [] };
const confirmation = { ...reply, intent: "analyze", message: "Confirm this exact investigation.", route: null, confirmation_required: true, action_id: sid, target: { owner: "octocat", repo: "secure-demo", installation_id: 10, workflow_run_id: 701, status: "completed", conclusion: "failure", connection_id: sid } };
let stopTrack: ReturnType<typeof vi.fn>;
class Recorder {
  static isTypeSupported() { return true; }
  state = "inactive";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; this.ondataavailable?.({ data: new Blob(["audio"], { type: "audio/webm" }) }); this.onstop?.(); }
}
beforeEach(() => {
  sessionStorage.clear(); post.mockReset().mockResolvedValue(reply); get.mockReset().mockResolvedValue([]); uploadAudio.mockReset().mockResolvedValue({ text: "Open my profile", language: "en" });
  stopTrack = vi.fn(); Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) } });
  vi.stubGlobal("MediaRecorder", Recorder);
  URL.createObjectURL = vi.fn().mockReturnValue("blob:voice"); URL.revokeObjectURL = vi.fn();
});
async function send(text = "Open my dashboard") { await userEvent.type(screen.getByRole("textbox"), text); await userEvent.click(screen.getByRole("button", { name: "Send text command" })); }
it("renders local readiness and text-only privacy information", () => { render(<VoiceAssistant />); expect(screen.getByRole("heading", { name: "Voice Agent" })).toBeVisible(); expect(screen.getByText(/Raw audio is not stored/)).toBeVisible(); expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled(); });
it("sends typed commands without microphone access and exposes a safe link", async () => { render(<VoiceAssistant />); await send(); expect(await screen.findByText(reply.message)).toBeVisible(); expect(screen.getByRole("link", { name: "Open relevant page" })).toHaveAttribute("href", "/dashboard"); expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled(); });
it("shows pending state and prevents duplicate commands", async () => { post.mockImplementation(() => new Promise(() => {})); render(<VoiceAssistant />); await userEvent.type(screen.getByRole("textbox"), "help"); await userEvent.dblClick(screen.getByRole("button", { name: "Send text command" })); expect(post).toHaveBeenCalledTimes(1); expect(screen.getByRole("button", { name: "Send text command" })).toBeDisabled(); expect(screen.getByRole("status")).toHaveTextContent("Understanding"); });
it("requires an explicit confirmation click", async () => { post.mockResolvedValueOnce(confirmation).mockResolvedValue({ message: "Investigation queued.", route: "/dashboard/ai/investigations/" + sid }); render(<VoiceAssistant />); await send("Analyze that workflow"); expect(await screen.findByRole("dialog")).toBeVisible(); expect(post).toHaveBeenCalledTimes(1); await userEvent.click(screen.getByRole("button", { name: "Confirm" })); expect(post.mock.calls[1][0]).toBe("/api/v1/auth/voice/confirm"); expect(await screen.findByRole("link", { name: "Open investigation report" })).toHaveAttribute("href", "/dashboard/ai/investigations/" + sid); });
it("cancels pending confirmation through the authenticated backend", async () => { post.mockResolvedValueOnce(confirmation).mockResolvedValue({ message: "Cancelled", route: null }); render(<VoiceAssistant />); await send("Analyze that workflow"); await screen.findByRole("dialog"); await userEvent.click(screen.getByRole("button", { name: "Cancel confirmation" })); expect(post.mock.calls[1][0]).toBe("/api/v1/auth/voice/cancel"); expect(screen.queryByRole("dialog")).toBeNull(); });
it.each(["Cannot reach the API.", "Your session has expired. Please sign in again.", "Local speech model is not installed."])("displays actionable API failure: %s", async message => { post.mockRejectedValue(new ApiError(message)); render(<VoiceAssistant />); await send(); expect(await screen.findByRole("alert")).toHaveTextContent(message); expect(screen.getByRole("button", { name: "Send text command" })).toBeEnabled(); });
it("reports microphone permission denial and keeps text mode", async () => { vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValue(new DOMException("Denied", "NotAllowedError")); render(<VoiceAssistant />); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); expect(await screen.findByRole("alert")).toHaveTextContent("Microphone permission denied"); await send(); expect(post).toHaveBeenCalledTimes(1); });
it("starts, stops, transcribes and allows editing before submission", async () => { render(<VoiceAssistant />); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); expect(screen.getByText(/Recording: 0 seconds/)).toBeVisible(); await userEvent.click(screen.getByRole("button", { name: "Stop recording" })); await waitFor(() => expect(screen.getByRole("textbox")).toHaveValue("Open my profile")); expect(stopTrack).toHaveBeenCalled(); expect(post).not.toHaveBeenCalled(); await userEvent.clear(screen.getByRole("textbox")); await userEvent.type(screen.getByRole("textbox"), "Open settings"); expect(screen.getByRole("textbox")).toHaveValue("Open settings"); });
it("cancels recording without uploading", async () => { render(<VoiceAssistant />); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); await userEvent.click(screen.getByRole("button", { name: "Cancel recording" })); expect(uploadAudio).not.toHaveBeenCalled(); expect(stopTrack).toHaveBeenCalled(); expect(screen.getByRole("status")).toHaveTextContent("cancelled"); });
it("stops at the server-provided recording limit", async () => { render(<VoiceAssistant />); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); await waitFor(() => expect(uploadAudio).toHaveBeenCalledTimes(1), { timeout: 2000 }); expect(stopTrack).toHaveBeenCalled(); });
it("uses the selected transcription language", async () => { render(<VoiceAssistant />); await userEvent.selectOptions(screen.getByLabelText("Transcription language"), "fr"); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); await userEvent.click(screen.getByRole("button", { name: "Stop recording" })); expect(uploadAudio.mock.calls[0][1]).toBe("fr"); });
it("shows speech errors without fabricated transcripts", async () => { uploadAudio.mockRejectedValue(new ApiError("No intelligible speech detected.")); render(<VoiceAssistant />); await userEvent.click(screen.getByRole("button", { name: "Start recording" })); await userEvent.click(screen.getByRole("button", { name: "Stop recording" })); expect(await screen.findByRole("alert")).toHaveTextContent("No intelligible speech"); expect(screen.getByRole("textbox")).toHaveValue(""); });
it("generates audio only on request and provides play pause stop replay", async () => { const play = vi.fn().mockResolvedValue(undefined), pause = vi.fn(); vi.stubGlobal("Audio", class { play = play; pause = pause; currentTime = 0; onended = null; }); post.mockResolvedValueOnce(reply).mockResolvedValue(new Blob(["wav"], { type: "audio/wav" })); render(<VoiceAssistant />); await send(); await userEvent.click(screen.getByRole("button", { name: "Generate voice response" })); expect(play).not.toHaveBeenCalled(); await userEvent.click(screen.getByRole("button", { name: "Play" })); expect(play).toHaveBeenCalledTimes(1); await userEvent.click(screen.getByRole("button", { name: "Pause" })); expect(pause).toHaveBeenCalled(); await userEvent.click(screen.getByRole("button", { name: "Replay" })); expect(play).toHaveBeenCalledTimes(2); await userEvent.click(screen.getByRole("button", { name: "Stop playback" })); expect(pause).toHaveBeenCalledTimes(3); });
it("retains only a session identifier and clears context on new conversation", async () => { render(<VoiceAssistant />); await send(); expect(sessionStorage.getItem("codemate-voice-session-voice-user")).toBe(sid); await userEvent.click(screen.getByRole("button", { name: "New conversation" })); expect(sessionStorage.getItem("codemate-voice-session-voice-user")).toBeNull(); });
it.each(["https://evil.test", "//evil.test", "/dashboard/../shell", "/dashboard/cicd/runs/1?owner=x&repo=y&installation=1&token=secret", "/api/v1/auth/logout"])("rejects untrusted navigation %s", route => { expect(safeVoiceRoute(route)).toBeNull(); });
it("preserves keyboard interaction", async () => { render(<VoiceAssistant />); fireEvent.change(screen.getByRole("textbox"), { target: { value: "help" } }); screen.getByRole("button", { name: "Send text command" }).focus(); await userEvent.keyboard("{Enter}"); expect(post).toHaveBeenCalledTimes(1); });

it("cancels previous playback when a new recording begins", async () => {
  const play = vi.fn().mockResolvedValue(undefined), pause = vi.fn();
  vi.stubGlobal("Audio", class { play = play; pause = pause; currentTime = 0; onended = null; });
  post.mockResolvedValueOnce(reply).mockResolvedValue(new Blob(["wav"], { type: "audio/wav" }));
  render(<VoiceAssistant />); await send();
  await userEvent.click(screen.getByRole("button", { name: "Generate voice response" }));
  await userEvent.click(screen.getByRole("button", { name: "Play" }));
  await userEvent.click(screen.getByRole("button", { name: "Start recording" }));
  expect(pause).toHaveBeenCalled(); expect(URL.revokeObjectURL).toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Generate voice response" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Cancel recording" }));
});

it("dismisses an expired confirmation while retaining an actionable error", async () => {
  post.mockResolvedValueOnce(confirmation).mockRejectedValue(new ApiError("Action expired. Identify the workflow again.", 409, "http", "VOICE_ACTION_EXPIRED"));
  render(<VoiceAssistant />); await send("Analyze that workflow");
  await screen.findByRole("dialog");
  await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Action expired");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("button", { name: "Send text command" })).toBeEnabled();
});
