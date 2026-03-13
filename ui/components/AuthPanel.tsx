"use client";

import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Eye, EyeOff, Check, X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { checkUsernameAvailable } from "@/lib/api";
import { Turnstile } from '@marsidev/react-turnstile';

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
    const [resetEmail, setResetEmail] = useState("");
    const [resetLoading, setResetLoading] = useState(false);
    const [resetMessage, setResetMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const router = useRouter();

    // Debounce username check
    useEffect(() => {
        if (isLogin || !username.trim()) {
            setUsernameAvailable(null);
            return;
        }

        const delayDebounceFn = setTimeout(async () => {
            setCheckingUsername(true);
            const { available } = await checkUsernameAvailable(username.trim());
            setUsernameAvailable(available);
            setCheckingUsername(false);
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [username, isLogin]);

    const handleOAuth = async (provider: "google" | "github") => {
        setLoading(true);
        setError(null);
        try {
            const { error } = await supabase.auth.signInWithOAuth({
                provider,
                options: {
                    redirectTo: `${window.location.origin}/#generate`,
                }
            });
            if (error) throw error;
        } catch (err: any) {
            setError(err.message || `An error occurred with ${provider} login.`);
            setLoading(false);
        }
    };

    const handleForgotPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setResetLoading(true);
        setResetMessage(null);
        try {
            const { error } = await supabase.auth.resetPasswordForEmail(resetEmail, {
                redirectTo: `${window.location.origin}/reset-password`,
            });
            if (error) throw error;
            setResetMessage({ type: 'success', text: 'Password reset instructions sent! Please check your email.' });
        } catch (err: any) {
            setResetMessage({ type: 'error', text: err.message || 'Failed to send reset instructions.' });
        } finally {
            setResetLoading(false);
        }
    };

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        if (!captchaToken) {
            setError("Please complete the CAPTCHA.");
            setLoading(false);
            return;
        }

        try {
            if (isLogin) {
                const { error } = await supabase.auth.signInWithPassword({
                    email,
                    password,
                });
                if (error) throw error;
                router.push("/#generate");
            } else {
                if (!username.trim()) throw new Error("Username is required.");
                if (usernameAvailable === false) throw new Error("This username is already taken.");

                const { error, data } = await supabase.auth.signUp({
                    email,
                    password,
                    options: {
                        data: {
                            username: username.trim(),
                        }
                    }
                });
                if (error) throw error;

                // Show check email dialog on successful signup
                setShowCheckEmail(true);
            }
        } catch (err: any) {
            setError(err.message || "An error occurred during authentication.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col justify-center">
            <div className="mx-auto w-full max-w-sm space-y-6">
                <div className="text-center">
                    <h1 className="text-xl sm:text-lg font-bold tracking-tight text-foreground/90">
                        {isLogin
                            ? "Get Started"
                            : "Create an Account"}
                    </h1>
                </div>

                <form onSubmit={handleAuth} className="space-y-4">
                    {!isLogin && (
                        <div className="space-y-2">
                            <Label htmlFor="username">Username</Label>
                            <div className="relative">
                                <Input
                                    id="username"
                                    type="text"
                                    placeholder="johndoe"
                                    required={!isLogin}
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    disabled={loading}
                                    className={`bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg ${usernameAvailable === false ? "border-destructive focus-visible:ring-destructive pr-10" : "pr-10"}`}
                                />
                                {username.trim() && (
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                                        {checkingUsername ? (
                                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                                        ) : usernameAvailable === true ? (
                                            <Check className="h-4 w-4 text-green-500" />
                                        ) : usernameAvailable === false ? (
                                            <X className="h-4 w-4 text-destructive" />
                                        ) : null}
                                    </div>
                                )}
                            </div>
                            {usernameAvailable === false && (
                                <p className="text-xs text-destructive">This username is taken.</p>
                            )}
                        </div>
                    )}
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="name@example.com"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            disabled={loading}
                            className="bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg"
                        />
                    </div>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="password">Password</Label>
                            {isLogin && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setResetEmail(email);
                                        setShowForgotPassword(true);
                                    }}
                                    className="text-sm font-medium text-primary hover:underline dark:text-primary-400"
                                >
                                    Forgot password?
                                </button>
                            )}
                        </div>
                        <div className="flex items-center gap-3 w-full justify-between">
                            <div className="relative flex-1">
                                <Input
                                    id="password"
                                    type={showPassword ? "text" : "password"}
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    disabled={loading}
                                    className="pr-10 bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </button>
                            </div>
                            <div
                                className="w-10 h-10 shrink-0 rounded-md border border-white/30 dark:border-white/10 bg-white/20 dark:bg-black/20 backdrop-blur-lg flex items-center justify-center relative"
                            >
                                {captchaToken ? (
                                    <svg className="w-5 h-5 transition-all duration-300 scale-100" viewBox="0 0 128 128">
                                        <path fill="#F38020" d="M88.74 38.65c-6.83-20-33.81-22.18-44.5-2.58-13.43-5.22-26 5.86-22 19.34C4.19 61 7.27 88.08 30.29 88.08H96c17.65 0 24.32-22.14 11.53-33-2.14-1.84-2.88-5.32-1.31-7.79 3.39-5.37-6.02-14.73-17.48-8.64Z"/>
                                    </svg>
                                ) : (
                                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                )}
                                <div className="absolute inset-0 w-0 h-0 overflow-hidden opacity-0 pointer-events-none">
                                    <Turnstile
                                        siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "1x00000000000000000000AA"} // Dummy testing key fallback
                                        options={{
                                            size: 'invisible',
                                        }}
                                        onSuccess={(token) => {
                                            setCaptchaToken(token);
                                            setError(null);
                                        }}
                                        onError={() => setError("CAPTCHA validation failed. Please try again.")}
                                        onExpire={() => {
                                            setCaptchaToken(null);
                                            setError("CAPTCHA expired. Please try again.");
                                        }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                            {error}
                        </div>
                    )}

                    <div className="flex items-center gap-3 pt-2 w-full">
                        <Button type="submit" className="flex-1 bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md text-foreground shadow-sm transition-all" disabled={loading || !captchaToken}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {isLogin ? "Sign In" : "Sign Up"}
                        </Button>
                        <span className="text-sm font-medium text-muted-foreground/70 tracking-wide px-1">or</span>
                        <Button variant="ghost" type="button" className="flex-1 bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md shadow-sm transition-all" disabled={loading} onClick={() => handleOAuth("google")}>
                            <svg className="w-6 h-6 hover:scale-110 transition-transform" viewBox="0 0 24 24">
                                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                <path d="M1 1h22v22H1z" fill="none" />
                            </svg>
                        </Button>
                    </div>
                </form>

                <div className="text-center text-sm pt-2">
                    {isLogin ? "Don't have an account? " : "Already have an account? "}
                    <button
                        type="button"
                        className="font-medium text-primary hover:underline"
                        onClick={() => {
                            setIsLogin(!isLogin);
                            setError(null);
                        }}
                    >
                        {isLogin ? "Sign up" : "Sign in"}
                    </button>
                </div>

                <Dialog open={showCheckEmail} onOpenChange={setShowCheckEmail}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Check your email</DialogTitle>
                            <DialogDescription>
                                We've sent a confirmation link to <strong>{email}</strong>. Please check your inbox and confirm your email to activate your account.
                            </DialogDescription>
                        </DialogHeader>
                        <Button className="mt-4" onClick={() => { setShowCheckEmail(false); setIsLogin(true); }}>
                            Go to login
                        </Button>
                    </DialogContent>
                </Dialog>

                <Dialog open={showForgotPassword} onOpenChange={(open) => {
                    setShowForgotPassword(open);
                    if (!open) setResetMessage(null);
                }}>
                    <DialogContent className="sm:max-w-md bg-white/10 dark:bg-black/20 backdrop-blur-3xl border border-white/20 dark:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.12)]">
                        <DialogHeader>
                            <DialogTitle>Reset your password</DialogTitle>
                            <DialogDescription className="text-neutral-700 dark:text-neutral-300">
                                Enter your email address and we'll send you instructions to reset your password.
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleForgotPassword} className="space-y-4 mt-4">
                            <div className="space-y-2">
                                <Label htmlFor="reset-email">Email</Label>
                                <Input
                                    id="reset-email"
                                    type="email"
                                    placeholder="name@example.com"
                                    required
                                    value={resetEmail}
                                    onChange={(e) => setResetEmail(e.target.value)}
                                    disabled={resetLoading || resetMessage?.type === 'success'}
                                    className="bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg"
                                />
                            </div>

                            {resetMessage && (
                                <div className={`text-sm p-3 rounded-md ${resetMessage.type === 'success' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-destructive/10 text-destructive'}`}>
                                    {resetMessage.text}
                                </div>
                            )}

                            {!resetMessage || resetMessage.type === 'error' ? (
                                <Button type="submit" className="w-full bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md shadow-sm transition-all dark:text-white" disabled={resetLoading}>
                                    {resetLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Send reset instructions
                                </Button>
                            ) : (
                                <Button type="button" className="w-full bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md shadow-sm transition-all text-foreground dark:text-white" onClick={() => setShowForgotPassword(false)}>
                                    Close
                                </Button>
                            )}
                        </form>
                    </DialogContent>
                </Dialog>
            </div>
        </div>
    );
}
