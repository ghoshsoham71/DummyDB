import Link from "next/link";
import { ModeToggle } from "./ModeToggle";
import { Button } from "./ui/button";
import { Search } from "nextra/components";
import "nextra-theme-docs/style.css";

export function Navbar() {
  return (
    <nav className="w-full flex items-center justify-between p-6 sm:px-12 border-b border-border bg-background/80 backdrop-blur sticky top-0 z-10">
      <Link href="/">
        <span className="text-2xl font-bold tracking-tight select-none">
          BurstDB
        </span>
      </Link>
      <div className="flex items-center gap-4">
        <Link href="/generate">
          <Button>Get Started</Button>
        </Link>
        <Link href="/dashboard">
          <Button variant="outline">Dashboard</Button>
        </Link>
        <Link href="/docs">
          <Button variant="outline">Docs</Button>
        </Link>
        <Search/>
        <ModeToggle />
      </div>
    </nav>
  );
}

