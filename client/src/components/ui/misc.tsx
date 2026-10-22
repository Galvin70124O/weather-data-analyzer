import * as React from "react";

import { cn } from "@/lib/utils";

/** Skeleton loader: a quiet block in the shape of what is coming (no spinners). */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
}

export function Badge({ className, tone = "neutral", ...props }: React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "warning" | "accent";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tone === "warning" && "border-warm/40 bg-warm/10 text-warm",
        tone === "accent" && "border-accent/40 bg-accent/10 text-accent",
        tone === "neutral" && "border-border bg-muted text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}
