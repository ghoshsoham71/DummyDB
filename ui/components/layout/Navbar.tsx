"use client";

import Link from "next/link";
import { ModeToggle } from "@/components/shared/ModeToggle";
import { Button } from "@/components/ui/button";
import { Search } from "nextra/components";
import { usePathname } from "next/navigation";
import "nextra-theme-docs/style.css";
import { useAuth } from "@/lib/auth-context";
import { NavbarAuth } from "./NavbarAuth";

export function Navbar() {
  const pathname = usePathname();
  const { user, isLoading } = useAuth();

  return (
    <nav className="w-full flex items-center justify-between p-6 sm:px-12 border-b border-border bg-background/80 backdrop-blur sticky top-0 z-10">
      <Link href="/">
        <span className="text-2xl font-bold tracking-tight select-none">
          BurstDB
        </span>
      </Link>
      <div className="flex items-center gap-4">
        {pathname !== "/" && !isLoading && (
          <Link href={user ? "/#generate" : "/"}>
            <Button>{user ? "Generate Data" : "Get Started"}</Button>
          </Link>
        )}
        <Link href="/dashboard">
          <Button variant="outline">Dashboard</Button>
        </Link>
        <a href="/docs" target="_blank" rel="noopener noreferrer">
          <Button variant="outline">Docs</Button>
        </a>
        <Search />
        <ModeToggle />
        <NavbarAuth />
      </div>
    </nav>
  );
}

