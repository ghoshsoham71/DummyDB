import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

export default function GeneratePage() {
  return (
    <div className="font-sans min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <main className="flex flex-1 flex-col items-center justify-center text-center gap-8 px-4">
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight mb-2">Generate Data</h1>
        <p className="text-lg max-w-xl text-muted-foreground mb-6">
          Use the form below to generate mock data for your database.
        </p>
        {/* TODO: Add form here */}
        <div className="border border-dashed border-border rounded p-8 text-muted-foreground">
          Form will go here.
        </div>
      </main>
      <Footer />
    </div>
  );
} 