"use client";

import { usePathname } from "next/navigation";

export function HideNavLinks() {
    const pathname = usePathname();

    // Hide Nextra layout elements on all pages EXCEPT /docs
    if (!pathname.startsWith("/docs")) {
        return (
            <style dangerouslySetInnerHTML={{
                __html: `
        .nextra-nav-container, footer.nextra-footer {
          display: none !important;
        }
        /* Make sure the main content can span the full height without Nextra's padding */
        article.nextra-content {
          padding: 0 !important;
          max-width: none !important;
        }
        .nextra-toc {
          display: none !important;
        }
      `}} />
        );
    }

    return null;
}
