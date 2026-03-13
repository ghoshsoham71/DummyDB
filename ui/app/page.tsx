import { Button } from "@/components/ui/button";
import Link from "next/link";
import { TypingText } from "@/components/TypingText";
import { GenerateSection } from "@/components/GenerateSection";

export default function Home() {
  return (
    <>
      {/* Animated Full-Screen Silk Cloth Gradient */}
      <div className="fixed inset-0 pointer-events-none -z-10 bg-silk opacity-100 dark:opacity-80" />

      <div className="font-sans h-[calc(100vh-5rem)] min-h-[500px] flex flex-col items-center justify-center text-foreground relative py-2 lg:py-8 px-6 lg:px-24 overflow-hidden box-border">

        {/* Hero Section */}
        <main className="flex flex-col items-center text-center gap-8 w-full max-w-2xl relative z-10">
          <div className="flex flex-col gap-6 w-full">
            <h1 className="text-xl sm:text-3xl font-normal tracking-tight mb-2 drop-shadow-md flex flex-col sm:flex-row justify-center lg:justify-start gap-y-1 sm:gap-x-0.1 text-metallic">
              <span>Generate Synthetic Databases</span>
              <span className="inline-block opacity-0 animate-[fastSlideIn_0.4s_cubic-bezier(0.1,0.9,0.2,1)_0.1s_forwards] italic self-center sm:self-auto px-2 rounded-md">
                <TypingText text="Instantly" speed={10} className="text-metallic drop-shadow-[0_4px_6px_rgba(0,0,0,0.8)]" />
              </span>
            </h1>

            <p className="text-sm sm:text-base max-w-xl text-foreground font-light drop-shadow-sm leading-relaxed flex flex-col gap-1">
              <span>Scale up your database, or generate one from scratch with a few clicks.</span>
              <span>Powered by generative models and LLMs.</span>
              <span>Delivering production-ready synthetic databases.</span>
            </p>

            <div className="mt-4 flex flex-row items-center w-full max-w-[fit-content] self-center lg:self-start justify-center lg:justify-start gap-4 bg-white/50 dark:bg-black/40 backdrop-blur-xl border border-black/10 dark:border-white/20 py-3 px-6 rounded-2xl shadow-lg hover:shadow-xl transition-all">
              <span className="text-xs sm:text-sm font-extralight text-foreground tracking-widest">Native Support - </span>
              <div className="flex items-center gap-5">
                <img
                  src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/postgresql/postgresql-original.svg"
                  alt="PostgreSQL"
                  className="h-7 w-7 sm:h-8 sm:w-8 hover:scale-125 hover:-translate-y-1 transition-all cursor-help drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]"
                  title="PostgreSQL"
                />
                <img
                  src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/mongodb/mongodb-original.svg"
                  alt="MongoDB"
                  className="h-7 w-7 sm:h-8 sm:w-8 hover:scale-125 hover:-translate-y-1 transition-all cursor-help drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]"
                  title="MongoDB"
                />
                <img
                  src="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/neo4j/neo4j-original.svg"
                  alt="Neo4j"
                  className="h-7 w-7 sm:h-8 sm:w-8 hover:scale-125 hover:-translate-y-1 transition-all cursor-help drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]"
                  title="Neo4j"
                />
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Generate Section */}
      <section id="generate" className="py-16 px-6 lg:px-24 bg-muted/50">
        <GenerateSection />
      </section>
    </>
  );
}
