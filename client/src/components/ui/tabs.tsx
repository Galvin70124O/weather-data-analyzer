import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import * as React from "react";

import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn("inline-flex h-9 items-center rounded-md bg-muted p-1", className)} {...props} />
));
TabsList.displayName = "TabsList";

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "num inline-flex h-7 items-center justify-center rounded-sm px-3 text-sm font-medium text-muted-foreground transition-colors",
      "focus-visible:outline-2 focus-visible:outline-accent data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-card",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = "TabsTrigger";

export const TabsContent = TabsPrimitive.Content;

/** Segmented control (e.g. °C / °F). */
export const SegmentedControl = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Root>,
  Omit<ToggleGroupPrimitive.ToggleGroupSingleProps, "type" | "value" | "defaultValue" | "onValueChange"> & {
    value: string;
    onValueChange: (v: string) => void;
  }
>(({ className, ...props }, ref) => (
  <ToggleGroupPrimitive.Root
    ref={ref}
    type="single"
    className={cn("inline-flex h-9 items-center rounded-md border border-border bg-card p-0.5", className)}
    {...props}
  />
));
SegmentedControl.displayName = "SegmentedControl";

export const SegmentedItem = React.forwardRef<
  React.ElementRef<typeof ToggleGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive.Item>
>(({ className, ...props }, ref) => (
  <ToggleGroupPrimitive.Item
    ref={ref}
    className={cn(
      "num inline-flex h-7 min-w-9 items-center justify-center rounded-sm px-2 text-sm font-medium text-muted-foreground",
      "focus-visible:outline-2 focus-visible:outline-accent data-[state=on]:bg-accent data-[state=on]:text-accent-foreground",
      className,
    )}
    {...props}
  />
));
SegmentedItem.displayName = "SegmentedItem";
