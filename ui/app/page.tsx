import { Navbar } from "../components/Navbar/Navbar";
import { ModeToggle } from "../components/ModeToggle/mode-toggle";
import { Button } from "../components/ui/button";
import { GitBranch } from "lucide-react";

export default function Home() {
  return (
    <div className="font-sans min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      {/* Hero Section */}
      <main className="flex flex-1 flex-col items-center justify-center text-center gap-8 px-4">
        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight mb-2">Generate Fake Data Instantly</h1>
        <p className="text-lg sm:text-2xl max-w-xl text-muted-foreground mb-6">
          Effortlessly create realistic mock data for SQL, NoSQL, and Graph databases. Perfect for testing, prototyping, and demos.
        </p>
        <Button size={"lg"}>Get Started</Button> 
      </main>
      <footer className="w-full flex flex-col sm:flex-row justify-center items-center gap-2 py-4 text-xs text-muted-foreground border-t border-border mt-8">
        <span>&copy; {new Date().getFullYear()} DummyDB. All rights reserved.</span>
        <a
          href="https://github.com/ghoshsoham71/DummyDB"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 px-3 py-1 rounded hover:bg-accent transition-colors text-foreground text-sm font-medium"
          style={{ textDecoration: 'none' }}
        >
          <GitBranch size={18} />
          GitHub
        </a>
      </footer>
    </div>
  );
}
