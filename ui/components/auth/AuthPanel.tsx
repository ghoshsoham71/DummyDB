"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { checkUsernameAvailable } from "@/lib/api";
import { Turnstile } from '@marsidev/react-turnstile';
import { LoginView } from "./LoginView";
import { SignupView } from "./SignupView";
import { Loader2 } from "lucide-react";

export function AuthPanel() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState("");
    const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
    const [checkingUsername, setCheckingUsername] = useState(false);
    const [captchaToken, setCaptchaToken] = useState<string | null>(null);
    const [showPassword, setShowPassword] = useState(false);
    const [showCheckEmail, setShowCheckEmail] = useState(false);
    const [showForgotPassword, setShowForgotPassword] = useState(false);
    const { signInWithGoogle } = useAuth();

    const router = useRouter();

    useEffect(() => {
        if (isLogin || !username.trim()) { setUsernameAvailable(null); return; }
        const timer = setTimeout(async () => {
            setCheckingUsername(true);
            const { available } = await checkUsernameAvailable(username.trim());
            setUsernameAvailable(available);
            setCheckingUsername(false);
        }, 500);
        return () => clearTimeout(timer);
    }, [username, isLogin]);

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true); setError(null);
        if (!captchaToken) { setError("Please complete CAPTCHA"); setLoading(false); return; }
        try {
            if (isLogin) {
                const { error } = await supabase.auth.signInWithPassword({ email, password });
                if (error) throw error;
                router.push("/#generate");
            } else {
                const { error } = await supabase.auth.signUp({ email, password, options: { data: { username: username.trim() } } });
                if (error) throw error;
                setShowCheckEmail(true);
            }
        } catch (err: any) { setError(err.message || "Error"); } finally { setLoading(false); }
    };

    return (
        <div className="mx-auto w-full max-w-sm space-y-6">
            <h1 className="text-xl font-bold text-center">{isLogin ? "Get Started" : "Create Account"}</h1>
            {isLogin ? (
                <LoginView email={email} setEmail={setEmail} password={password} setPassword={setPassword} showPassword={showPassword} setShowPassword={setShowPassword} loading={loading} onForgotPassword={() => setShowForgotPassword(true)} onSubmit={handleAuth} captchaToken={captchaToken} />
            ) : (
                <SignupView email={email} setEmail={setEmail} username={username} setUsername={setUsername} usernameAvailable={usernameAvailable} checkingUsername={checkingUsername} password={password} setPassword={setPassword} showPassword={showPassword} setShowPassword={setShowPassword} loading={loading} onSubmit={handleAuth} captchaToken={captchaToken} />
            )}

            <div className="relative">
                <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                <div className="relative flex justify-center text-xs uppercase"><span className="bg-background px-2 text-muted-foreground">Or continue with</span></div>
            </div>

            <Button variant="outline" type="button" className="w-full" onClick={() => signInWithGoogle()} disabled={loading}>
                <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                    <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
                </svg>
                Google
            </Button>
            <div className="flex items-center gap-2">
                <div className="grow border-t opacity-20" />
                <span className="text-xs text-muted-foreground">CAPTCHA</span>
                <Turnstile siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "1x00000000000000000000AA"} options={{ size: 'invisible' }} onSuccess={setCaptchaToken} />
            </div>
            <div className="text-center text-sm">
                <button onClick={() => setIsLogin(!isLogin)} className="text-primary hover:underline">{isLogin ? "Sign up" : "Sign in"}</button>
            </div>
            {error && <div className="text-xs text-destructive p-3 bg-destructive/10 rounded">{error}</div>}
        </div>
    );
}
