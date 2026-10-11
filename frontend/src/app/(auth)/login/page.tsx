import { AuthFrame } from "@/components/auth/auth-frame";
import { GuestGate } from "@/components/auth/guest-gate";
import { LoginForm } from "@/components/auth/login-form";
export default function LoginPage() { return <AuthFrame><GuestGate><LoginForm /></GuestGate></AuthFrame>; }
