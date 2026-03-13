"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";
import { apiFetch } from "./api";
import { useRouter } from "next/navigation";

interface AuthContextType {
    user: User | null;
    session: Session | null;
    isLoading: boolean;
    signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    session: null,
    isLoading: true,
    signOut: async () => { },
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [session, setSession] = useState<Session | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        // Helper to parse OAuth tokens from URL (hash or query)
        const processOAuthTokens = async () => {
            const hash = window.location.hash || "";
            const query = window.location.search || "";
            const urlParams = new URLSearchParams(query.replace(/^\?/, ""));
            let accessToken = urlParams.get("access_token");
            let refreshToken = urlParams.get("refresh_token");

            if (!accessToken || !refreshToken) {
                // Check hash, handling cases where hash has multiple parts (e.g., #generate#access_token=...)
                const hashParts = hash.split('#').filter(Boolean);
                const tokenPart = hashParts.length > 1 ? hashParts[hashParts.length - 1] : hash.replace(/^#/, "");
                const hashParams = new URLSearchParams(tokenPart);
                accessToken = hashParams.get("access_token");
                refreshToken = hashParams.get("refresh_token");
            }

            if (accessToken && refreshToken) {
                const { data, error } = await supabase.auth.setSession({
                    access_token: accessToken,
                    refresh_token: refreshToken,
                });
                if (error) throw error;
                setSession(data.session ?? null);
                setUser(data.session?.user ?? null);

                // Clear tokens from URL and set hash to generate if it was the redirect target
                const newHash = hash.includes('#generate') ? '#generate' : '';
                window.history.replaceState({}, document.title, window.location.pathname + window.location.search + newHash);
                return true;
            }

            return false;
        };

        // Initialize session and/or handle OAuth redirect tokens.
        const initializeAuth = async () => {
            try {
                const handled = await processOAuthTokens();
                if (!handled) {
                    const { data: { session }, error } = await supabase.auth.getSession();
                    if (error) throw error;
                    setSession(session);
                    setUser(session?.user ?? null);
                }
            } catch (error) {
                console.error("Error getting session:", error);
            } finally {
                setIsLoading(false);
            }
        };

        initializeAuth();

        // Some OAuth flows return tokens via hash without reloading; watch for it.
        const onHashChange = async () => {
            const handled = await processOAuthTokens();
            if (handled) {
                setIsLoading(false);
            }
        };

        window.addEventListener("hashchange", onHashChange);

        // Listen for auth state changes, including sign-in/out traps.
        const { data: authListener } = supabase.auth.onAuthStateChange(
            async (event, currentSession) => {
                setSession(currentSession);
                setUser(currentSession?.user ?? null);
                setIsLoading(false);

                if (event === "SIGNED_OUT") {
                    // Send signal to backend to clear cookie potentially, or clear local state
                    try {
                        await apiFetch("/auth/logout", { method: "POST" });
                    } catch (e) {
                        console.error("Logout API failed", e);
                    }
                    router.push("/");
                }
            }
        );

        return () => {
            authListener.subscription.unsubscribe();
            window.removeEventListener("hashchange", onHashChange);
        };
    }, [router]);

    const signOut = async () => {
        try {
            await supabase.auth.signOut();
        } catch (error) {
            console.error("Error signing out:", error);
        }
    };

    return (
        <AuthContext.Provider value={{ user, session, isLoading, signOut }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};
