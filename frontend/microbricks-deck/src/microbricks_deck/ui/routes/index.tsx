import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";
import { SECTIONS } from "@/lib/content";
import { TopNav } from "@/components/navigation/top-nav";
import { HeroSection } from "@/components/sections/hero-section";
import { ProblemSection } from "@/components/sections/problem-section";
import { VisionSection } from "@/components/sections/vision-section";
import { ArchitectureSection } from "@/components/sections/architecture-section";
import { CicdSection } from "@/components/sections/cicd-section";
import { ImplementationSection } from "@/components/sections/implementation-section";
import { DemoSection } from "@/components/sections/demo-section";

export const Route = createFileRoute("/")({
  component: DeckPage,
});

function DeckPage() {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.target !== document.body) return;

      const sectionIds = SECTIONS.map((s) => s.id);
      const current = sectionIds.findIndex((id) => {
        const el = document.getElementById(id);
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.top <= 100 && rect.bottom > 100;
      });

      if (e.key === "ArrowDown" || e.key === " ") {
        e.preventDefault();
        const next = Math.min(current + 1, sectionIds.length - 1);
        document.getElementById(sectionIds[next])?.scrollIntoView({ behavior: "smooth" });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev = Math.max(current - 1, 0);
        document.getElementById(sectionIds[prev])?.scrollIntoView({ behavior: "smooth" });
      } else if (e.key >= "1" && e.key <= "7") {
        e.preventDefault();
        const idx = parseInt(e.key) - 1;
        if (idx < sectionIds.length) {
          document.getElementById(sectionIds[idx])?.scrollIntoView({ behavior: "smooth" });
        }
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <>
      <TopNav />
      <main className="pt-14">
        <HeroSection />
        <ProblemSection />
        <VisionSection />
        <ArchitectureSection />
        <CicdSection />
        <ImplementationSection />
        <DemoSection />
      </main>
    </>
  );
}
