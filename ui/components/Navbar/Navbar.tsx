import { ModeToggle } from "../ModeToggle/ModeToggle";
import { Button } from "../ui/button";

export function Navbar() {
  return (
    <nav className="w-full flex items-center justify-between p-6 sm:px-12 border-b border-border bg-background/80 backdrop-blur sticky top-0 z-10">
      <span className="text-2xl font-bold tracking-tight select-none">
        DummyDB
      </span>
      <div className="flex items-center gap-4">
        <Button>Get Started</Button>
        <Button variant="outline">Docs</Button>
        <ModeToggle />
      </div>
    </nav>
  );
}
