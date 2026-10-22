import { AlertTriangle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** A friendly error with a Retry button. */
export function ErrorState({ title = "Something went wrong", message, onRetry, className }: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div role="alert" className={cn("flex flex-col items-center gap-3 rounded-lg border border-border bg-card px-6 py-10 text-center", className)}>
      <span className="grid size-11 place-items-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="size-5" aria-hidden="true" />
      </span>
      <div>
        <p className="font-semibold">{title}</p>
        {message && <p className="mt-1 max-w-md text-sm text-muted-foreground">{message}</p>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw aria-hidden="true" /> Try again
        </Button>
      )}
    </div>
  );
}

/** "Nothing here yet" with a short hint and an optional action. */
export function EmptyState({ icon, title, message, action, className }: {
  icon: ReactNode;
  title: string;
  message?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-6 py-10 text-center", className)}>
      <span className="grid size-11 place-items-center rounded-full bg-muted text-muted-foreground [&_svg]:size-5">{icon}</span>
      <div>
        <p className="font-semibold">{title}</p>
        {message && <p className="mt-1 max-w-md text-sm text-muted-foreground">{message}</p>}
      </div>
      {action}
    </div>
  );
}
