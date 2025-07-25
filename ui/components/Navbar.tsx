import Link from "next/link";
import { ModeToggle } from "./ModeToggle";
import { Button } from "./ui/button";

export function Navbar() {
  return (
    <nav className="w-full flex items-center justify-between p-6 sm:px-12 border-b border-border bg-background/80 backdrop-blur sticky top-0 z-10">
      <Link href="/">
        <span className="text-2xl font-bold tracking-tight select-none">
          DummyDB
        </span>
      </Link>
      <div className="flex items-center gap-4">
        <Link href="/generate">
          <Button>Get Started</Button>
        </Link>
        <Link href="/docs">
          <Button variant="outline">Docs</Button>
        </Link>
        <ModeToggle />
      </div>
    </nav>
  );
}
