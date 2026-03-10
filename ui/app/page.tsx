import { Button } from "@/components/ui/button";
import Link from "next/link";
import { AuthPanel } from "@/components/AuthPanel";
import { TypingText } from "@/components/TypingText";

export default function Home() {
  return (
    <>
      {/* Animated Full-Screen Silk Cloth Gradient */}
      <div className="fixed inset-0 pointer-events-none -z-10 bg-silk opacity-100 dark:opacity-80" />

      <div className="font-sans min-h-[calc(100vh-4rem)] flex flex-col lg:flex-row items-center justify-between text-foreground relative py-12 px-6 lg:px-24">

        {/* Hero Section */}
        <main className="flex flex-col items-center lg:items-start text-center lg:text-left gap-8 w-full max-w-2xl relative z-10">
          <div className="flex flex-col gap-6">
            <h1 className="text-4xl sm:text-6xl font-bold tracking-tight mb-2 drop-shadow-sm min-h-[1.2rem] sm:min-h-[1.2em]">
              <TypingText text="Generate Fake Data Instantly" speed={70} />
            </h1>
            <p className="text-lg sm:text-2xl max-w-xl text-muted-foreground drop-shadow-sm">
              Effortlessly create realistic mock data for SQL, NoSQL, and Graph
              databases. Perfect for testing, prototyping, and demos.
            </p>
          </div>
        </main>

        {/* Auth Section - Glass Box */}
        <aside className="w-full max-w-[320px] lg:w-[320px] lg:min-w-[320px] relative z-10 mt-8 lg:mt-0">
          <div className="bg-white/10 dark:bg-black/20 backdrop-blur-3xl border border-white/20 dark:border-white/10 rounded-3xl p-6 sm:p-8 shadow-[0_8px_32px_rgba(0,0,0,0.12)]">
            <AuthPanel />
          </div>
        </aside>
      </div>
    </>
  );
}
