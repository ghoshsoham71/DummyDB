"use client";

import { usePathname } from "next/navigation";

export function ConditionalSearch() {
    const pathname = usePathname();

    // Only show the search bar when we are on the /docs path
    if (pathname?.startsWith("/docs")) {
        return null;
    }

    // Render a global style block to hide Nextra's built-in search components on non-docs pages
    return (
        <style dangerouslySetInnerHTML={{
            __html: `
      .nextra-search { display: none !important; }
      /* Fallback for Nextra 4 internal specific classes if needed */
      nav > .flex > .flex > .nextra-search { display: none !important; }
      header [role="search"] { display: none !important; }
    `}} />
    );
}
