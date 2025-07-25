import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function Home() {
  return (
    <div className="font-sans min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      {/* Hero Section */}
      <main className="flex flex-1 flex-col items-center justify-center text-center gap-8 px-4">
        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight mb-2">
          Generate Fake Data Instantly
        </h1>
        <p className="text-lg sm:text-2xl max-w-xl text-muted-foreground mb-6">
          Effortlessly create realistic mock data for SQL, NoSQL, and Graph
          databases. Perfect for testing, prototyping, and demos.
        </p>
        <Link href="/generate">
          <Button size={"lg"}>Get Started</Button>
        </Link>
      </main>
      <Footer />
    </div>
  );
}
