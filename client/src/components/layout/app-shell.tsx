import { BarChart3, History, LayoutDashboard, LogOut, Moon, Search, Sun, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { SearchButton, useSearch } from "@/components/search/command-palette";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SegmentedControl, SegmentedItem } from "@/components/ui/tabs";
import { useLogout, useMe, useUnits } from "@/hooks/use-auth";
import { useColorMode } from "@/hooks/use-color-mode";
import type { Units } from "@/lib/types";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/compare", label: "Compare", icon: BarChart3 },
  { to: "/history", label: "History", icon: History },
  { to: "/account", label: "Account", icon: UserRound },
];

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2 whitespace-nowrap font-semibold tracking-tight", className)}>
      <span aria-hidden="true" className="grid size-8 place-items-center rounded-md bg-accent text-accent-foreground">
        <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="9" cy="9" r="3.5" />
          <path d="M9 2.5v1.5M2.5 9H4M4.4 4.4l1 1M14.5 13a4 4 0 1 1 0 8H8a3 3 0 0 1-.6-5.95A5 5 0 0 1 14.5 13Z" />
        </svg>
      </span>
      <span>Weather<span className="text-muted-foreground font-normal"> Analyzer</span></span>
    </span>
  );
}

function UnitsToggle() {
  const { units, setUnits } = useUnits();
  return (
    <SegmentedControl value={units} onValueChange={(v) => v && setUnits(v as Units)} aria-label="Temperature unit">
      <SegmentedItem value="metric" aria-label="Celsius">°C</SegmentedItem>
      <SegmentedItem value="imperial" aria-label="Fahrenheit">°F</SegmentedItem>
    </SegmentedControl>
  );
}

function ColorModeToggle() {
  const { mode, toggle } = useColorMode();
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
      {mode === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}

function UserMenu() {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Account menu">
          <span className="grid size-8 place-items-center rounded-full bg-muted text-sm font-semibold uppercase">
            {me?.username.slice(0, 1) ?? "?"}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>
          Signed in as <span className="font-medium text-foreground">{me?.username}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/account")}>
          <UserRound aria-hidden="true" /> Account
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => logout.mutate(undefined, { onSuccess: () => navigate("/login") })}>
          <LogOut aria-hidden="true" /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const MOBILE_ITEM = "flex flex-col items-center gap-1 py-2.5 text-xs font-medium text-muted-foreground";

function mobileLink({ to, label, icon: Icon, end }: (typeof NAV)[number]) {
  return (
    <NavLink key={to} to={to} end={end} className={({ isActive }) => cn(MOBILE_ITEM, isActive && "text-accent")}>
      <Icon className="size-5" aria-hidden="true" />
      {label}
    </NavLink>
  );
}

function MobileSearch() {
  const { openSearch } = useSearch();
  return (
    <button type="button" onClick={() => openSearch()} className={MOBILE_ITEM}>
      <Search className="size-5" aria-hidden="true" />
      Search
    </button>
  );
}

/** Sidebar on desktop, bottom navigation on mobile; the header holds °C/°F, light/dark and the account menu. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh md:flex">
      <div className="wx-backdrop" aria-hidden="true" />
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2">
        Skip to content
      </a>

      <aside className="hidden w-60 shrink-0 border-r border-border bg-card/70 backdrop-blur-xl md:block">
        <div className="sticky top-0 flex h-screen flex-col gap-6 p-4">
        <Logo className="px-2 pt-1" />
        <nav aria-label="Main" className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-muted text-foreground",
                )
              }
            >
              <Icon className="size-4" aria-hidden="true" /> {label}
            </NavLink>
          ))}
        </nav>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border/60 bg-background/70 px-4 backdrop-blur-xl sm:px-6">
          <Logo className="md:hidden" />
          {/* Phones search from the bottom nav; the header has no room left at 375px */}
          <SearchButton className="hidden sm:flex" />
          <div className="flex items-center gap-1 sm:gap-2">
            <UnitsToggle />
            <ColorModeToggle />
            <UserMenu />
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 sm:px-6 md:pb-12">
          {children}
        </main>
      </div>

      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-card/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden">
        {NAV.slice(0, 1).map(mobileLink)}
        <MobileSearch />
        {NAV.slice(1).map(mobileLink)}
      </nav>
    </div>
  );
}
