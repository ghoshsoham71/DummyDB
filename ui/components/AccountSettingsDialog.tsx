"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { deleteAccount, checkUsernameAvailable } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, AlertTriangle, Eye, EyeOff, Save, Check, X } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface AccountSettingsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function AccountSettingsDialog({ open, onOpenChange }: AccountSettingsDialogProps) {
    const { user, signOut } = useAuth();

    // States for Update Username
    const [username, setUsername] = useState("");
    const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
    const [checkingUsername, setCheckingUsername] = useState(false);
    const [updatingUsername, setUpdatingUsername] = useState(false);
    const [usernameMessage, setUsernameMessage] = useState("");

    // States for Update Password
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [updatingPassword, setUpdatingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState("");

    // States for Delete Account
    const [deleting, setDeleting] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState("");

    useEffect(() => {
        if (open && user?.user_metadata?.username) {
            setUsername(user.user_metadata.username);
        }
    }, [user, open]);

    useEffect(() => {
        if (!open) return;
        const currentName = user?.user_metadata?.username || "";
        const trimmed = username.trim();
        
        if (!trimmed || trimmed === currentName) {
            setUsernameAvailable(null);
            return;
        }

        const delayDebounceFn = setTimeout(async () => {
            setCheckingUsername(true);
            try {
                const { available } = await checkUsernameAvailable(trimmed);
                setUsernameAvailable(available);
            } catch (e) {
                setUsernameAvailable(null);
            }
            setCheckingUsername(false);
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [username, open, user]);

    const handleUpdateUsername = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const trimmed = username.trim();
        if (!trimmed) {
            setUsernameMessage("Username cannot be empty.");
            return;
        }
        if (trimmed === user?.user_metadata?.username) {
            setUsernameMessage("This is already your username.");
            return;
        }
        if (usernameAvailable === false) {
            setUsernameMessage("This username is taken.");
            return;
        }

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

        if (!password.trim()) {
            setPasswordMessage("Password cannot be empty.");
            return;
        }
        
        if (password !== confirmPassword) {
            setPasswordMessage("Passwords do not match.");
            return;
        }

        setUpdatingPassword(true);
        setPasswordMessage("");

        try {
            const { error } = await supabase.auth.updateUser({
                password: password
            });
            if (error) throw error;
            setPasswordMessage("Password updated successfully!");
            setPassword("");
            setConfirmPassword("");
        } catch (error: any) {
            setPasswordMessage(error.message || "Failed to update password.");
        } finally {
            setUpdatingPassword(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirm !== "DELETE") return;
        if (!window.confirm("WARNING: Are you sure you want to delete your entire account permanently? All your schemas and generated data will be wiped out immediately.")) return;
        setDeleting(true);
        try {
            await deleteAccount();
            await signOut();
            onOpenChange(false);
        } catch (error) {
            console.error(error);
            setDeleting(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md bg-white/10 dark:bg-black/20 backdrop-blur-3xl border border-white/20 dark:border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.12)] max-h-[85vh] overflow-y-auto scrollbar-thin">
                <DialogHeader>
                    <DialogTitle>Account Settings</DialogTitle>
                    <DialogDescription className="text-neutral-700 dark:text-neutral-300">
                        Manage your profile and security preferences.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 mt-4">
                    {/* Profile Section */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-medium border-b pb-2">Profile Information</h3>
                        <form onSubmit={handleUpdateUsername} className="space-y-3">
                            <div className="flex gap-2 items-end">
                                <div className="space-y-2 flex-1">
                                    <Label htmlFor="settings-username">Username</Label>
                                    <div className="relative">
                                        <Input
                                            id="settings-username"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            placeholder="Your username"
                                            className={`bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg pr-10 ${(usernameAvailable === false && username.trim() !== user?.user_metadata?.username) ? "border-destructive focus-visible:ring-destructive text-destructive" : ""}`}
                                        />
                                        {username.trim() !== "" && username.trim() !== user?.user_metadata?.username && (
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
                                </div>
                                <TooltipProvider>
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <Button type="submit" size="icon" disabled={updatingUsername} className="bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md text-foreground dark:text-white transition-all shrink-0">
                                                {updatingUsername ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                                                <span className="sr-only">Save Username</span>
                                            </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                            <p>Save Username</p>
                                        </TooltipContent>
                                    </Tooltip>
                                </TooltipProvider>
                            </div>
                            {usernameMessage && (
                                <p className={`text-sm font-medium ${usernameMessage.includes("success") ? "text-green-600 dark:text-green-400" : "text-destructive"}`}>
                                    {usernameMessage}
                                </p>
                            )}
                        </form>
                    </div>

                    {/* Security Section */}
                    <div className="space-y-4 relative">
                        <h3 className="text-sm font-medium border-b pb-2">Security</h3>
                        
                        {user?.app_metadata?.provider !== 'email' && (
                            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/40 backdrop-blur-[3px] rounded-b-lg mt-8">
                                <span className="text-xs font-medium text-foreground bg-background/80 dark:bg-black/60 px-3 py-1 rounded-full border border-border/50 shadow-sm backdrop-blur-md">
                                    Password managed via {user?.app_metadata?.provider ? user.app_metadata.provider.charAt(0).toUpperCase() + user.app_metadata.provider.slice(1) : 'OAuth'}
                                </span>
                            </div>
                        )}

                        <form onSubmit={handleUpdatePassword} className={`space-y-3 ${user?.app_metadata?.provider !== 'email' ? 'opacity-40 pointer-events-none grayscale' : ''}`}>
                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <Label htmlFor="settings-new-password">New Password</Label>
                                    <div className="relative">
                                        <Input
                                            id="settings-new-password"
                                            type={showPassword ? "text" : "password"}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder="Enter new password"
                                            minLength={6}
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
                                </div>
                                <div className="flex gap-2 items-end">
                                    <div className="space-y-2 flex-1">
                                        <Label htmlFor="settings-confirm-password">Confirm Password</Label>
                                        <div className="relative">
                                            <Input
                                                id="settings-confirm-password"
                                                type={showConfirmPassword ? "text" : "password"}
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                placeholder="Retype new password"
                                                minLength={6}
                                                className="pr-10 bg-white/20 dark:bg-black/20 border-white/30 dark:border-white/10 backdrop-blur-lg"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                                            >
                                                {showConfirmPassword ? (
                                                    <EyeOff className="h-4 w-4" />
                                                ) : (
                                                    <Eye className="h-4 w-4" />
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button type="submit" size="icon" disabled={updatingPassword} className="bg-white/10 hover:bg-white/20 dark:bg-black/20 dark:hover:bg-black/40 border border-white/20 dark:border-white/10 backdrop-blur-md text-foreground dark:text-white transition-all shrink-0">
                                                    {updatingPassword ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                                                    <span className="sr-only">Update Password</span>
                                                </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                <p>Update Password</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                </div>
                            </div>
                            {passwordMessage && (
                                <p className={`text-sm font-medium ${passwordMessage.includes("success") ? "text-green-600 dark:text-green-400" : "text-destructive"}`}>
                                    {passwordMessage}
                                </p>
                            )}
                        </form>
                    </div>

                    {/* Danger Zone */}
                    <div className="space-y-4 pt-2">
                        <h3 className="text-sm font-medium text-destructive border-b border-destructive/20 pb-2 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4" />
                            Danger Zone
                        </h3>
                        <div className="bg-destructive/10 p-4 rounded-lg border border-destructive/20 space-y-3">
                            <p className="text-xs text-black dark:text-muted-foreground">
                                Once you delete your account, there is no going back. Please be certain.
                            </p>
                            <div className="space-y-2">
                                <Label htmlFor="delete-confirm-input" className="text-xs text-destructive font-semibold">
                                    Type "DELETE" to confirm
                                </Label>
                                <Input
                                    id="delete-confirm-input"
                                    value={deleteConfirm}
                                    onChange={(e) => setDeleteConfirm(e.target.value)}
                                    placeholder="DELETE"
                                    className="bg-background/50 border-destructive/30 focus-visible:ring-destructive text-sm"
                                />
                            </div>
                            <Button
                                variant="destructive"
                                onClick={handleDeleteAccount}
                                disabled={deleteConfirm !== "DELETE" || deleting}
                                className="w-full text-sm h-9 active:brightness-50 active:bg-neutral-950 transition-all duration-75"
                            >
                                {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Permanently Delete Account
                            </Button>
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
