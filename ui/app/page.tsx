import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-purple-500/30 overflow-x-hidden font-sans">
      {/* Hero Section */}
      <section className="relative pt-40 pb-32 px-6 flex flex-col items-center justify-center text-center animate-in-fade">
        {/* Subtle background glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/10 dark:bg-purple-600/5 blur-[120px] rounded-full pointer-events-none animate-float" />

        <div className="relative z-10 flex flex-col items-center max-w-4xl">
          {/* Pill */}
          <div className="flex items-center gap-3 px-4 py-1.5 mb-8 border border-primary/20 bg-primary/5 rounded-full">
            <div className="w-1.5 h-4 bg-primary rounded-sm" />
            <span className="text-[10px] sm:text-xs font-light tracking-[0.2em] text-primary uppercase">
              Next-Gen Generative Modeling
            </span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-normal tracking-tight leading-[1.1] mb-8 text-foreground/90 animate-blur-in">
            <span className="title-mask"><span className="title-reveal">Generative Data Seeding</span></span>
            <span className="title-mask" style={{ animationDelay: '100ms' }}><span className="title-reveal" style={{ animationDelay: '100ms' }}>for the</span></span>
            <span className="title-mask" style={{ animationDelay: '200ms' }}>
              <span className="title-reveal font-semibold bg-gradient-to-r from-purple-500 via-purple-600 to-indigo-600 dark:from-purple-400 dark:via-purple-500 dark:to-indigo-500 bg-clip-text text-transparent" style={{ animationDelay: '200ms' }}>
                Modern Enterprise
              </span>
            </span>
          </h1>

          <p className="text-sm sm:text-base md:text-lg text-muted-foreground font-normal max-w-2xl leading-relaxed mb-12 animate-in-slide" style={{ animationDelay: '400ms' }}>
            Transform your development lifecycle with architecturally-aware synthetic databases. 
            High-fidelity modeling for complex relational environments.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-6 animate-in-slide" style={{ animationDelay: '600ms' }}>
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-6 rounded-sm text-xs tracking-[0.1em] font-medium transition-premium shadow-lg dark:shadow-[0_0_20px_rgba(139,60,255,0.3)] uppercase hover:-translate-y-1">
              Begin Synthesis
            </Button>
            <Button variant="outline" className="bg-transparent border-border hover:bg-muted text-foreground/80 px-8 py-6 rounded-sm text-xs tracking-[0.1em] font-medium uppercase transition-premium hover:-translate-y-1">
              Technical Specs
            </Button>
          </div>
        </div>

        {/* Scroll prompt */}
        <div className="absolute bottom-12 flex flex-col items-center gap-4 opacity-50">
          <div className="w-[1px] h-12 bg-gradient-to-b from-transparent via-foreground/30 to-transparent" />
          <span className="text-[9px] tracking-[0.3em] font-light uppercase text-foreground/70">
            Scroll to explore architecture
          </span>
        </div>
      </section>

      {/* Separator */}
      <div className="w-full h-px bg-border/50" />

      {/* The Who, Where, Why */}
      <section className="py-24 px-6 lg:px-24 max-w-7xl mx-auto animate-in-slide">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 lg:gap-20">
          {/* Who */}
          <div className="flex flex-col gap-6 group hover:-translate-y-2 transition-premium animate-in-slide" style={{ animationDelay: '0ms' }}>
            <div className="w-8 h-8 rounded-sm bg-primary/5 border border-primary/20 flex items-center justify-center group-hover:bg-primary/10 transition-premium">
              <div className="w-3 h-px bg-primary/60" />
            </div>
            <h3 className="text-lg font-medium tracking-wide text-foreground/90">The Who</h3>
            <p className="text-sm font-normal text-muted-foreground leading-relaxed">
              Engineered for DevOps architects, QA leads, and Data Scientists who require production-grade datasets without the privacy overhead.
            </p>
          </div>

          {/* Where */}
          <div className="flex flex-col gap-6 group hover:-translate-y-2 transition-premium animate-in-slide" style={{ animationDelay: '200ms' }}>
            <div className="w-8 h-8 rounded-sm bg-primary/5 border border-primary/20 flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-primary/60 rounded-sm" />
            </div>
            <h3 className="text-lg font-medium tracking-wide text-foreground/90">The Where</h3>
            <p className="text-sm font-normal text-muted-foreground leading-relaxed">
              Ideal for high-compliance environments, CI/CD pipelines, and local development clusters where PII exposure is a critical risk.
            </p>
          </div>

          {/* Why */}
          <div className="flex flex-col gap-6">
            <div className="w-8 h-8 rounded-sm bg-primary/5 border border-primary/20 flex items-center justify-center">
              <div className="w-px h-3 bg-primary/60" />
            </div>
            <h3 className="text-lg font-medium tracking-wide text-foreground/90">The Why</h3>
            <p className="text-sm font-normal text-muted-foreground leading-relaxed">
              Achieve parity with production schemas while maintaining total anonymity. Accelerate testing cycles with deterministic, repeatable data generation.
            </p>
          </div>
        </div>
      </section>

      <div className="w-full h-px bg-border/50" />

      {/* Efficiency Redefined */}
      <section className="py-32 px-6 lg:px-24 max-w-7xl mx-auto animate-in-slide">
        <div className="flex flex-col lg:flex-row gap-20">
          {/* Left Content */}
          <div className="flex-1 flex flex-col gap-12">
            <div>
              <p className="text-[10px] tracking-[0.2em] font-medium text-primary uppercase mb-4">
                Efficiency Redefined
              </p>
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-normal tracking-tight leading-tight text-foreground/90">
                Synthetic Generation at <br />
                <i className="text-foreground/70">Hyper-Scale</i>
              </h2>
            </div>

            <div className="flex flex-col gap-10">
              <div className="flex gap-4 items-start">
                <div className="mt-1 w-4 h-4 border border-primary/40 rounded-sm flex-shrink-0" />
                <div className="flex flex-col gap-2">
                  <h4 className="text-sm font-medium text-foreground/90">Massive reduction in token consumption</h4>
                  <p className="text-xs sm:text-sm font-light text-muted-foreground leading-relaxed">
                    Our proprietary generative modeling engine optimizes data structures natively, bypassing expensive LLM token pathways for 98% cost efficiency.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="mt-1 w-4 h-4 border border-primary/40 rounded-sm flex-shrink-0" />
                <div className="flex flex-col gap-2">
                  <h4 className="text-sm font-medium text-foreground/90">Schema-Aware Synthesis</h4>
                  <p className="text-xs sm:text-sm font-light text-muted-foreground leading-relaxed">
                    Deep introspection of foreign keys and complex constraints ensures that your synthetic data maintains perfect referential integrity.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 items-start">
                <div className="mt-1 w-4 h-4 border border-primary/40 rounded-sm flex-shrink-0" />
                <div className="flex flex-col gap-2">
                  <h4 className="text-sm font-medium text-foreground/90">Differential Privacy Layer</h4>
                  <p className="text-xs sm:text-sm font-normal text-muted-foreground leading-relaxed animate-in-slide" style={{ animationDelay: '200ms' }}>
                    Mathematical guarantees that ensure no original production data can be reconstructed from the synthesized output.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Graphic */}
          <div className="flex-1 relative flex items-center justify-center">
            {/* Soft backdrop glow */}
            <div className="absolute inset-0 bg-primary/5 blur-[80px] rounded-full animate-float" />
            
            <div className="relative w-full max-w-lg aspect-[4/3] bg-card border border-border rounded-md shadow-2xl dark:shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col hover:shadow-primary/5 transition-premium group">
              {/* Fake Window Header */}
              <div className="h-10 border-b border-border flex items-center justify-between px-4 bg-muted/30">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-foreground/10" />
                  <div className="w-2 h-2 rounded-full bg-foreground/10" />
                  <div className="w-2 h-2 rounded-full bg-foreground/10" />
                </div>
                <div className="text-[8px] font-medium tracking-[0.2em] text-muted-foreground uppercase">
                  ANA / TECH / METRIC / ACTIVE
                </div>
              </div>

              {/* Fake Content Area */}
              <div className="p-8 flex flex-col flex-1 gap-4 opacity-70 animate-reveal">
                <div className="w-full h-2 bg-primary/20 rounded-sm" />
                <div className="w-3/4 h-2 bg-muted rounded-sm" />
                <div className="w-5/6 h-2 bg-muted rounded-sm" />
                <div className="mt-auto grid grid-cols-3 gap-4">
                  <div className="flex flex-col items-center justify-center p-4 border border-primary/20 bg-primary/5 rounded-sm hover:bg-primary/10 transition-premium">
                    <span className="text-lg font-normal text-primary mb-1">100M</span>
                    <span className="text-[7px] tracking-[0.2em] font-medium text-muted-foreground uppercase">Rows/Sec</span>
                  </div>
                  <div className="flex flex-col items-center justify-center p-4 border border-primary/20 bg-primary/5 rounded-sm hover:bg-primary/10 transition-premium">
                    <span className="text-lg font-normal text-primary mb-1">92%</span>
                    <span className="text-[7px] tracking-[0.2em] font-medium text-muted-foreground uppercase">Cost Drop</span>
                  </div>
                  <div className="flex flex-col items-center justify-center p-4 border border-primary/20 bg-primary/5 rounded-sm hover:bg-primary/10 transition-premium">
                    <span className="text-lg font-normal text-primary mb-1">0.0ms</span>
                    <span className="text-[7px] tracking-[0.2em] font-medium text-muted-foreground uppercase">Latency</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 relative flex justify-center">
        <div className="relative w-full max-w-5xl bg-gradient-to-b from-muted/50 to-background dark:from-[#111116] dark:to-[#0a0a0c] border border-border rounded-lg overflow-hidden flex flex-col items-center text-center px-6 py-24">
          {/* Subtle top highlight */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/3 h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
          
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-normal tracking-tight text-foreground/90 mb-6">
            Ready to deploy high-fidelity <br className="hidden sm:block" />
            synthetic architecture?
          </h2>
          <p className="text-sm font-light text-muted-foreground max-w-lg mb-12 leading-relaxed">
            Experience the future of generative modeling. No production data risk. 
            Minimal token overhead. Maximum development velocity.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 animate-in-slide" style={{ animationDelay: '200ms' }}>
            <Button className="bg-primary hover:bg-primary/90 text-primary-foreground px-10 py-6 rounded-sm text-xs tracking-[0.1em] font-medium transition-premium shadow-lg dark:shadow-[0_0_20px_rgba(139,60,255,0.2)] uppercase hover:-translate-y-1">
              Request Access
            </Button>
             <Link href="/docs">
              <Button variant="outline" className="bg-transparent border-border hover:bg-muted text-foreground/80 px-10 py-6 rounded-sm text-xs tracking-[0.1em] font-medium uppercase transition-premium hover:-translate-y-1">
                View Docs
              </Button>
            </Link>
          </div>
        </div>
      </section>

    </div>
  );
}
