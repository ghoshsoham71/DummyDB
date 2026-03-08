import Link from "next/link";

export function Footer() {
  return (
    <footer className="w-full flex flex-col sm:flex-row justify-between items-center gap-2 py-4 px-8 text-xs text-muted-foreground border-t border-border mt-8">
      <span>
        &copy; {new Date().getFullYear()} BurstDB. All rights reserved.
      </span>
      <span>
        Made by{" "}
        <Link
          href="https://github.com/ghoshsoham71"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          @ghoshsoham71
        </Link>{" "}
        and{" "}
        <Link
          href="https://github.com/shm-dtt"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
        >
          @shm-dtt
        </Link>
      </span>
    </footer>
  );
}
