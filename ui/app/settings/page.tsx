"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { deleteAccount } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle, Eye, EyeOff, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SettingsPage() {
    const { user, signOut, isLoading } = useAuth();
    const router = useRouter();

    // States for Update Username
    const [username, setUsername] = useState("");
    const [updatingUsername, setUpdatingUsername] = useState(false);
    const [usernameMessage, setUsernameMessage] = useState("");

    // States for Update Password
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [updatingPassword, setUpdatingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState("");

    // States for Delete Account
    const [deleting, setDeleting] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState("");

    useEffect(() => {
        if (user?.user_metadata?.username) {
            setUsername(user.user_metadata.username);
        }
    }, [user]);

    if (isLoading) {
        return (
            <div className="flex justify-center items-center min-h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    if (!user) {
        router.push("/");
        return null;
    }

    const handleUpdateUsername = async (e: React.FormEvent) => {
        e.preventDefault();
        setUpdatingUsername(true);
        setUsernameMessage("");

        try {
            const { error } = await supabase.auth.updateUser({
                data: { username: username }
            });
            if (error) throw error;
            setUsernameMessage("Username updated successfully!");
        } catch (error: any) {
            setUsernameMessage(error.message || "Failed to update username.");
        } finally {
            setUpdatingUsername(false);
        }
    };

    const handleUpdatePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setUpdatingPassword(true);
        setPasswordMessage("");

        try {
            const { error } = await supabase.auth.updateUser({
                password: password
            });
            if (error) throw error;
            setPasswordMessage("Password updated successfully!");
            setPassword("");
        } catch (error: any) {
            setPasswordMessage(error.message || "Failed to update password.");
        } finally {
            setUpdatingPassword(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirm !== "DELETE") return;
        setDeleting(true);
        try {
            await deleteAccount();
            await signOut();
            router.push("/");
        } catch (error) {
            console.error(error);
            setDeleting(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto p-8 space-y-12 animate-in fade-in duration-500">
            <div>
                <h1 className="text-4xl font-bold mb-2 tracking-tight">Account Settings</h1>
                <p className="text-muted-foreground text-lg">Manage your profile and security preferences.</p>
            </div>

            <section className="space-y-6 bg-card p-6 rounded-xl border shadow-sm">
                <h2 className="text-2xl font-semibold border-b pb-4">Profile Information</h2>
                <form onSubmit={handleUpdateUsername} className="space-y-4 max-w-md pt-2">
                    <div className="space-y-2">
                        <Label htmlFor="username">Username</Label>
                        <Input
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Your username"
                        />
                    </div>
                    <Button type="submit" disabled={updatingUsername}>
                        {updatingUsername && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Username
                    </Button>
                    {usernameMessage && (
                        <p className={`text-sm font-medium ${usernameMessage.includes("success") ? "text-green-500 dark:text-green-400" : "text-destructive"}`}>
                            {usernameMessage}
                        </p>
                    )}
                </form>
            </section>

            <section className="space-y-6 bg-card p-6 rounded-xl border shadow-sm">
                <h2 className="text-2xl font-semibold border-b pb-4">Security</h2>
                <form onSubmit={handleUpdatePassword} className="space-y-4 max-w-md pt-2">
                    <div className="space-y-2">
                        <Label htmlFor="new-password">New Password</Label>
                        <div className="relative">
                            <Input
                                id="new-password"
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter new password"
                                minLength={6}
                                className="pr-10"
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
                    </div>
                    <Button type="submit" disabled={updatingPassword}>
                        {updatingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Update Password
                    </Button>
                    {passwordMessage && (
                        <p className={`text-sm font-medium ${passwordMessage.includes("success") ? "text-green-500 dark:text-green-400" : "text-destructive"}`}>
                            {passwordMessage}
                        </p>
                    )}
                </form>
            </section>

            <section className="space-y-6 pt-8 border-t border-destructive/20 mt-12 pl-2">
                <div>
                    <h2 className="text-2xl font-semibold text-destructive flex items-center gap-2">
                        <AlertTriangle className="h-6 w-6" />
                        Danger Zone
                    </h2>
                    <p className="text-sm text-muted-foreground mt-2">
                        Once you delete your account, there is no going back. Please be certain.
                    </p>
                </div>

                <div className="bg-destructive/10 p-6 rounded-lg border border-destructive/20 space-y-4 max-w-md">
                    <div className="space-y-2">
                        <Label htmlFor="delete-confirm" className="text-destructive font-semibold">
                            Type "DELETE" to confirm
                        </Label>
                        <Input
                            id="delete-confirm"
                            value={deleteConfirm}
                            onChange={(e) => setDeleteConfirm(e.target.value)}
                            placeholder="DELETE"
                            className="bg-background/50 border-destructive/30 focus-visible:ring-destructive"
                        />
                    </div>
                    <Button
                        variant="destructive"
                        onClick={handleDeleteAccount}
                        disabled={deleteConfirm !== "DELETE" || deleting}
                        className="w-full"
                    >
                        {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Permanently Delete Account
                    </Button>
                </div>
            </section>
        </div>
    );
}
