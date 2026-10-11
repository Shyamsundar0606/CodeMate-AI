import { AuthFrame } from "@/components/auth/auth-frame";
import { GuestGate } from "@/components/auth/guest-gate";
import { RegisterForm } from "@/components/auth/register-form";
export default function RegisterPage() { return <AuthFrame><GuestGate><RegisterForm /></GuestGate></AuthFrame>; }
