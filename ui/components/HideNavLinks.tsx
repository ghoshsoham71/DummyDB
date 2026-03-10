"use client";

import { usePathname } from "next/navigation";

export function HideNavLinks() {
    const pathname = usePathname();

    if (pathname === "/") {
        return (
            <style dangerouslySetInnerHTML={{
                __html: `
        nav a[href="/generate"] {
          display: none !important;
        }
      `}} />
        );
    }

    return null;
}
