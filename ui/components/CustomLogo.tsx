"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";

export function CustomLogo() {
    const { user } = useAuth();
    const router = useRouter();

    return (
        <span
            onClick={(e) => {
                e.preventDefault();
                router.push(user ? "/generate" : "/");
            }}
            className="flex flex-row items-center gap-2 cursor-pointer group"
        >
            <div className="relative flex items-center justify-center w-8 h-8">
                {/* Glowing Background Blob */}
                <div className="absolute inset-0 bg-gradient-to-tr from-amber-500 via-emerald-500 to-purple-500 rounded-full blur-md opacity-40 group-hover:opacity-70 transition-opacity duration-500 mix-blend-screen" />

                {/* Database Cylinder Icon */}
                <svg
                    className="relative w-6 h-6 text-foreground drop-shadow-md group-hover:scale-105 transition-transform duration-300"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <ellipse cx="12" cy="5" rx="9" ry="3" />
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                    {/* Burst Sparks */}
                    <path d="M12 1v1M18.5 2.5l-.7.7M22 5h-1M5.5 2.5l.7.7M2 5h1" className="text-amber-500 animate-pulse" />
                </svg>
            </div>

            <b className="text-xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent transition-all group-hover:from-amber-600 group-hover:via-emerald-500 group-hover:to-purple-600 dark:group-hover:from-amber-400 dark:group-hover:via-emerald-400 dark:group-hover:to-purple-400">
                BurstDB
            </b>
        </span>
    );
}
