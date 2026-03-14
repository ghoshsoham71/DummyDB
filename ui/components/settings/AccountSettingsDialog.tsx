"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { deleteAccount, checkUsernameAvailable } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ProfileSection } from "./ProfileSection";
import { SecuritySection } from "./SecuritySection";
import { DangerZone } from "./DangerZone";

interface AccountSettingsDialogProps { open: boolean; onOpenChange: (open: boolean) => void; }

export function AccountSettingsDialog({ open, onOpenChange }: AccountSettingsDialogProps) {
    const { user, signOut } = useAuth();
    const [username, setUsername] = useState("");
    const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(null);
    const [checkingUsername, setCheckingUsername] = useState(false);
    const [updatingUsername, setUpdatingUsername] = useState(false);
    const [usernameMessage, setUsernameMessage] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [updatingPassword, setUpdatingPassword] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState("");
    const [deleting, setDeleting] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState("");

    useEffect(() => { if (open && user?.user_metadata?.username) setUsername(user.user_metadata.username); }, [user, open]);

    useEffect(() => {
        if (!open) return;
        const current = user?.user_metadata?.username || "";
        if (!username.trim() || username.trim() === current) { setUsernameAvailable(null); return; }
        const timer = setTimeout(async () => {
            setCheckingUsername(true);
            try { const { available } = await checkUsernameAvailable(username.trim()); setUsernameAvailable(available); } catch { setUsernameAvailable(null); }
            setCheckingUsername(false);
        }, 500);
        return () => clearTimeout(timer);
    }, [username, open, user]);

    const handleUpdateUsername = async (e: React.FormEvent) => {
        e.preventDefault();
        setUpdatingUsername(true); setUsernameMessage("");
        try {
            const { error } = await supabase.auth.updateUser({ data: { username } });
            if (error) throw error;
            setUsernameMessage("Username updated successfully!");
        } catch (e: any) { setUsernameMessage(e.message || "Failed"); } finally { setUpdatingUsername(false); }
    };

    const handleUpdatePassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) { setPasswordMessage("Passwords do not match"); return; }
        setUpdatingPassword(true); setPasswordMessage("");
        try {
            const { error } = await supabase.auth.updateUser({ password });
            if (error) throw error;
            setPasswordMessage("Password updated successfully!");
            setPassword(""); setConfirmPassword("");
        } catch (e: any) { setPasswordMessage(e.message || "Failed"); } finally { setUpdatingPassword(false); }
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirm !== "DELETE" || !window.confirm("Are you sure?")) return;
        setDeleting(true);
        try { await deleteAccount(); await signOut(); onOpenChange(false); } catch { setDeleting(false); }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md bg-card backdrop-blur-3xl border max-h-[85vh] overflow-y-auto">
                <DialogHeader><DialogTitle>Account Settings</DialogTitle><DialogDescription>Manage profile and security.</DialogDescription></DialogHeader>
                <div className="space-y-6 mt-4">
                    <ProfileSection username={username} setUsername={setUsername} usernameAvailable={usernameAvailable} checkingUsername={checkingUsername} updatingUsername={updatingUsername} usernameMessage={usernameMessage} onUpdateUsername={handleUpdateUsername} currentUsername={user?.user_metadata?.username || ""} />
                    <SecuritySection password={password} setPassword={setPassword} confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword} showPassword={showPassword} setShowPassword={setShowPassword} showConfirmPassword={showConfirmPassword} setShowConfirmPassword={setShowConfirmPassword} updatingPassword={updatingPassword} passwordMessage={passwordMessage} onUpdatePassword={handleUpdatePassword} provider={user?.app_metadata?.provider || 'email'} />
                    <DangerZone deleteConfirm={deleteConfirm} setDeleteConfirm={setDeleteConfirm} deleting={deleting} onDeleteAccount={handleDeleteAccount} />
                </div>
            </DialogContent>
        </Dialog>
    );
}
