"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

export function ModeToggle() {
  const { theme, setTheme, systemTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  // Wait until mounted to avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    // Render a placeholder with the same layout before hydration
    return <div className="w-[72px] h-[36px] rounded-full border border-border bg-background/30 backdrop-blur-md" />
  }

  const currentTheme = theme === "system" ? systemTheme : theme
  const isDark = currentTheme === "dark"

  return (
    <div className="relative flex items-center w-[72px] h-[36px] rounded-full border border-white/20 bg-background/30 backdrop-blur-md shadow-inner dark:border-white/10 dark:bg-black/30 p-1 cursor-pointer"
      onClick={() => setTheme(isDark ? "light" : "dark")}>

      {/* Sliding Background */}
      <div
        className={`absolute h-[28px] w-[30px] rounded-full bg-primary/20 backdrop-blur-md shadow-[0_0_10px_rgba(0,0,0,0.1)] transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${isDark ? "translate-x-[32px]" : "translate-x-0"
          }`}
      />

      {/* Icons */}
      <div className="relative z-10 flex w-full justify-between px-1.5 items-center">
        <Sun className={`h-4 w-4 transition-colors duration-500 ${!isDark ? "text-primary drop-shadow-[0_0_2px_rgba(255,255,255,0.8)]" : "text-muted-foreground"}`} />
        <Moon className={`h-4 w-4 transition-colors duration-500 ${isDark ? "text-primary drop-shadow-[0_0_2px_rgba(255,255,255,0.8)]" : "text-muted-foreground"}`} />
      </div>

      <span className="sr-only">Toggle theme</span>
    </div>
  )
}
