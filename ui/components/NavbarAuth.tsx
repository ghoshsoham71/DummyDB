"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LogOut, User, Settings } from "lucide-react";
import Link from "next/link";
import { AccountSettingsDialog } from "./AccountSettingsDialog";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { AuthPanel } from "./AuthPanel";

export function NavbarAuth() {
    const { user, signOut, isLoading } = useAuth();
    const [showSettings, setShowSettings] = useState(false);
    const [authDialogOpen, setAuthDialogOpen] = useState(false);

    if (isLoading) {
        return <div className="w-8 h-8 rounded-full border border-border animate-pulse bg-muted" />;
    }

    if (!user) {
        return (
            <>
                <Button variant="outline" onClick={() => setAuthDialogOpen(true)}>
                    Login
                </Button>
                <Dialog open={authDialogOpen} onOpenChange={setAuthDialogOpen}>
                    <DialogContent className="sm:max-w-md">
                    <DialogTitle className="sr-only">Login</DialogTitle>
                    <AuthPanel />
                </DialogContent>
                </Dialog>
            </>
        );
    }

    return (
        <>
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span className="text-sm font-medium">
                        Welcome {user.user_metadata?.username || user.email?.split('@')[0]}
                    </span>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                        <p className="text-sm font-medium leading-none">Account</p>
                        <p className="text-xs leading-none text-muted-foreground">
                            {user.user_metadata?.username || user.email}
                        </p>
                    </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                    <Link href="/dashboard" className="cursor-pointer">Dashboard</Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowSettings(true)} className="cursor-pointer flex items-center">
                    <Settings className="mr-2 h-4 w-4" />
                    Account Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={signOut} className="cursor-pointer text-destructive focus:text-destructive">
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Log out</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
        <AccountSettingsDialog open={showSettings} onOpenChange={setShowSettings} />
        </>
    );
}
