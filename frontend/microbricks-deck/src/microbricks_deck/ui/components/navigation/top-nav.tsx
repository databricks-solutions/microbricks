import { useActiveSection, useScrollProgress } from "@/hooks/use-active-section";
import { SECTIONS } from "@/lib/content";
import { cn } from "@/lib/utils";

export function TopNav() {
  const active = useActiveSection();
  const progress = useScrollProgress();

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="microbricks" className="w-7 h-7" />
          <span className="font-semibold text-sm">microbricks</span>
        </div>

        <div className="hidden sm:flex items-center gap-1">
          {SECTIONS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              className={cn(
                "px-2.5 py-1 text-xs rounded-md transition-all duration-200",
                active === id
                  ? "bg-primary/15 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="sm:hidden flex items-center gap-1.5">
          {SECTIONS.map(({ id }) => (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              className={cn(
                "w-2 h-2 rounded-full transition-all duration-200",
                active === id ? "bg-primary scale-125" : "bg-muted-foreground/30",
              )}
            />
          ))}
        </div>
      </div>

      <div className="h-0.5 bg-muted">
        <div
          className="h-full bg-primary/60 transition-all duration-150"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </nav>
  );
}
