"use client";

import { useState, useEffect } from "react";

interface TypingTextProps {
    text: string;
    className?: string;
    speed?: number;
}

export function TypingText({ text, className = "", speed = 60 }: TypingTextProps) {
    const [displayedText, setDisplayedText] = useState("");
    const [index, setIndex] = useState(0);

    useEffect(() => {
        if (index < text.length) {
            const timer = setTimeout(() => {
                setDisplayedText((prev) => prev + text.charAt(index));
                setIndex((prev) => prev + 1);
            }, speed);

            return () => clearTimeout(timer);
        }
    }, [index, text, speed]);

    return (
        <span className={`inline-block ${className}`}>
            {displayedText}
            {index < text.length && (
                <span className="inline-block w-[3px] h-[0.9em] bg-foreground ml-1 -mb-[0.1em] animate-pulse" />
            )}
        </span>
    );
}
