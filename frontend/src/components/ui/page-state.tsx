import { LoaderCircle, WifiOff } from "lucide-react";
export function LoadingState({ message = "Checking your session…" }: { message?: string }) {
  return <div className="page-state" role="status"><LoaderCircle className="spin" size={28} aria-hidden="true" /><p>{message}</p></div>;
}
export function ErrorState({ title, message, retry }: { title: string; message: string; retry?: () => void }) {
  return <section className="error-state" role="alert"><WifiOff size={26} aria-hidden="true" /><h2>{title}</h2><p>{message}</p>{retry && <button className="button secondary" onClick={retry}>Try again</button>}</section>;
}
