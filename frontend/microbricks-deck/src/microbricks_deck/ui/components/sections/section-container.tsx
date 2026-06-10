import { type ReactNode } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface SectionContainerProps {
  id: string;
  children: ReactNode;
  className?: string;
  fullHeight?: boolean;
}

export function SectionContainer({ id, children, className, fullHeight = true }: SectionContainerProps) {
  return (
    <section
      id={id}
      className={cn(
        "relative px-4 sm:px-6 lg:px-8 py-20 sm:py-28",
        fullHeight && "min-h-screen flex flex-col justify-center",
        className,
      )}
    >
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="max-w-6xl mx-auto w-full"
      >
        {children}
      </motion.div>
    </section>
  );
}

interface SectionTitleProps {
  badge?: string;
  title: string;
  subtitle?: string;
}

export function SectionTitle({ badge, title, subtitle }: SectionTitleProps) {
  return (
    <div className="mb-12 sm:mb-16">
      {badge && (
        <motion.span
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="inline-block px-3 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary border border-primary/20 mb-4"
        >
          {badge}
        </motion.span>
      )}
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">{title}</h2>
      {subtitle && (
        <p className="mt-4 text-lg text-muted-foreground max-w-2xl">{subtitle}</p>
      )}
    </div>
  );
}
