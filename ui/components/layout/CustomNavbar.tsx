"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { NavbarAuth } from "@/components/layout/NavbarAuth";
import { CustomLogo } from "./CustomLogo";

export function CustomNavbar() {
  const { user } = useAuth();

  return (
    <nav className="w-full flex items-center justify-between px-6 lg:px-12 py-6 absolute top-0 z-50">
      <div className="flex items-center">
        <CustomLogo />
      </div>

      <div className="hidden md:flex items-center gap-12 absolute left-1/2 -translate-x-1/2">
        <Link href="#" className="text-xs tracking-[0.2em] font-light text-foreground/70 hover:text-foreground transition-colors uppercase">
          Synthesis
        </Link>
        <Link href="#" className="text-xs tracking-[0.2em] font-light text-foreground/70 hover:text-foreground transition-colors uppercase">
          Modeling
        </Link>
        <Link href="#" className="text-xs tracking-[0.2em] font-light text-foreground/70 hover:text-foreground transition-colors uppercase">
          Solutions
        </Link>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-xs tracking-[0.2em] uppercase">
          <NavbarAuth />
        </div>
        {!user && (
          <Link href="/studio">
            <Button className="bg-[#9d25f4] hover:bg-[#851ad6] text-white rounded-md px-6 py-2 text-xs tracking-[0.1em] uppercase font-light border-0 shadow-[0_0_15px_rgba(157,37,244,0.3)]">
              Studio
            </Button>
          </Link>
        )}
      </div>
    </nav>
  );
}
