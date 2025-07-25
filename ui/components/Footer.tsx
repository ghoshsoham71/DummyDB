import { GitBranch } from "lucide-react";
import Link from "next/link";
import { Button } from "./ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function Footer() {
  return (
    <footer className="w-full flex flex-col sm:flex-row justify-between items-center gap-2 py-4 px-8 text-xs text-muted-foreground border-t border-border mt-8">
      <span>
        &copy; {new Date().getFullYear()} DummyDB. All rights reserved.
      </span>
      <span>
        Made by{" "}
        <Link
          href="https://github.com/shm-dtt"
          target="_blank"
          rel="noopener noreferrer"
        >
          <HoverCard>
            <HoverCardTrigger asChild>
              <Button variant="link">@shm-dtt</Button>
            </HoverCardTrigger>
            <HoverCardContent className="w-70">
              <div className="flex justify-center gap-4">
                <Avatar>
                  <AvatarImage src="https://github.com/shm-dtt.png" />
                  <AvatarFallback>SD</AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <h4 className="text-sm">@shm-dtt</h4>
                  <p className="text-sm">Software Engineer @nokia.</p>
                </div>
              </div>
            </HoverCardContent>
          </HoverCard>
        </Link>{" "}
        and{" "}
        <Link
          href="https://github.com/shm-dtt"
          target="_blank"
          rel="noopener noreferrer"
        >
          <HoverCard>
            <HoverCardTrigger asChild>
              <Button variant="link">@ghoshsoham71</Button>
            </HoverCardTrigger>
            <HoverCardContent className="w-70">
              <div className="flex justify-center gap-4">
                <Avatar>
                  <AvatarImage src="https://github.com/ghoshsoham71.png" />
                  <AvatarFallback>SG</AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <h4 className="text-sm">@ghoshsoham71</h4>
                  <p className="text-sm">Software Engineer @TCS.</p>
                </div>
              </div>
            </HoverCardContent>
          </HoverCard>
        </Link>
      </span>
      <Link
        href="https://github.com/ghoshsoham71/DummyDB"
        target="_blank"
        rel="noopener noreferrer"
      >
        <Button variant={"outline"} size={"sm"}>
          <GitBranch size={18} />
          GitHub
        </Button>
      </Link>
    </footer>
  );
}
