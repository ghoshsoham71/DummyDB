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
                router.push(user ? "/#generate" : "/");
            }}
            className="flex flex-row items-center gap-3 cursor-pointer group"
        >
            <div className="relative flex items-center justify-center w-6 h-6">
                <svg
                    className="relative w-6 h-6 text-foreground/80 group-hover:text-purple-500 transition-colors duration-300"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <path d="M12 2 L22 12 L12 22 L2 12 Z" />
                    <circle cx="12" cy="12" r="3" fill="currentColor" opacity="0.5" className="group-hover:opacity-100 transition-opacity" />
                </svg>
            </div>

            <span className="text-xl font-light tracking-[0.2em] uppercase text-foreground/90 group-hover:text-foreground transition-colors">
                BURSTDB
            </span>
        </span>
    );
}
