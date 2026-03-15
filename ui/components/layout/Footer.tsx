import Link from "next/link";
import { CustomLogo } from "./CustomLogo";

export function Footer() {
  return (
    <footer className="w-full border-t border-border bg-muted/30 pt-20 pb-10 px-6 lg:px-24 text-muted-foreground transition-premium">
      <div className="max-w-7xl mx-auto flex flex-col gap-16">
        <div className="flex flex-col md:flex-row justify-between gap-12">
          
          <div className="flex flex-col gap-6 max-w-xs animate-in-fade">
            <div className="flex items-center gap-3">
              <CustomLogo />
            </div>
            <p className="text-xs font-normal leading-relaxed text-muted-foreground/60">
              Advanced generative modeling for the data-driven enterprise. 
              Synthesizing the future of scalable infrastructure.
            </p>
          </div>

          <div className="flex gap-16 sm:gap-24 animate-in-fade" style={{ animationDelay: '100ms' }}>
            <div className="flex flex-col gap-4">
              <h5 className="text-[10px] font-semibold tracking-[0.2em] uppercase text-foreground/80">Architecture</h5>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Synthesis Engine</Link>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Modeling LLMs</Link>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Compliance</Link>
            </div>

            <div className="flex flex-col gap-4">
              <h5 className="text-[10px] font-semibold tracking-[0.2em] uppercase text-foreground/80">Interface</h5>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Security Specs</Link>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Cloud Hybrid</Link>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">Case Studies</Link>
            </div>

            <div className="flex flex-col gap-4">
              <h5 className="text-[10px] font-semibold tracking-[0.2em] uppercase text-foreground/80">Resources</h5>
              <Link href="/docs" className="text-xs font-normal hover:text-primary transition-premium">Documentation</Link>
              <Link href="/docs" className="text-xs font-normal hover:text-primary transition-premium">API Reference</Link>
              <Link href="#" className="text-xs font-normal hover:text-primary transition-premium">System Status</Link>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8 border-t border-border animate-in-slide" style={{ animationDelay: '200ms' }}>
          <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-8">
            <p className="text-[10px] font-normal tracking-wide uppercase text-muted-foreground/40">
              © {new Date().getFullYear()} BURSTDB SYNTHESIS SYSTEMS.
            </p>
            <div className="flex gap-4">
               <Link href="https://github.com/ghoshsoham71" target="_blank" rel="noopener noreferrer" className="text-[10px] font-medium tracking-widest uppercase hover:text-primary transition-premium">@ghoshsoham71</Link>
               <Link href="https://github.com/shm-dtt" target="_blank" rel="noopener noreferrer" className="text-[10px] font-medium tracking-widest uppercase hover:text-primary transition-premium">@shm-dtt</Link>
            </div>
          </div>
          <p className="text-[10px] font-normal tracking-[0.1em] uppercase text-muted-foreground/40">
            Precision Engineered for Data Sovereignty.
          </p>
        </div>
      </div>
    </footer>
  );
}
