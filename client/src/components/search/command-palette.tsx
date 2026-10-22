import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import { Clock, Loader2, MapPin, Search } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { Skeleton } from "@/components/ui/misc";
import { api, ApiError } from "@/lib/api";
import type { City } from "@/lib/types";
import { cn } from "@/lib/utils";

/*
 * City search for the whole app: Ctrl+K / ⌘K, the header search button and the mobile nav all
 * open the same palette. By default picking a city opens its page; Compare opens it in "pick"
 * mode to add a city instead.
 */
interface OpenOptions {
  onPick?: (city: City) => void;
  title?: string;
  exclude?: number[];
}

const SearchContext = createContext<{ openSearch: (options?: OpenOptions) => void } | null>(null);

export function useSearch() {
  const context = useContext(SearchContext);
  if (!context) throw new Error("useSearch needs <SearchProvider>");
  return context;
}

export const MIN_QUERY = 2;       // the server's minimum

export function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/** True for Ctrl+K (Windows/Linux) and ⌘K (Mac). */
export function isSearchShortcut(event: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey">): boolean {
  return event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey) && !event.altKey;
}

export function SearchProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<OpenOptions | null>(null);
  const openSearch = useCallback((next: OpenOptions = {}) => setOptions(next), []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (!isSearchShortcut(event)) return;
      event.preventDefault();
      setOptions((open) => (open ? null : {}));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo(() => ({ openSearch }), [openSearch]);
  return (
    <SearchContext.Provider value={value}>
      {children}
      <CommandPalette options={options} onClose={() => setOptions(null)} />
    </SearchContext.Provider>
  );
}

const ITEM = cn(
  "flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm",
  "data-[selected=true]:bg-muted data-[selected=true]:text-foreground",
);

function CommandPalette({ options, onClose }: { options: OpenOptions | null; onClose: () => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const debounced = useDebounced(query.trim(), 250);
  const open = options !== null;
  const searching = debounced.length >= MIN_QUERY;

  useEffect(() => { if (!open) setQuery(""); }, [open]);

  const results = useQuery({
    queryKey: ["city-search", debounced.toLowerCase()],
    queryFn: () => api.searchCities(debounced),
    enabled: open && searching,
    staleTime: 10 * 60_000,
  });
  const recent = useQuery({ queryKey: ["recent-searches"], queryFn: api.recentSearches, enabled: open && !searching });

  const exclude = new Set(options?.exclude ?? []);
  const cities = (searching ? results.data : recent.data?.map((r) => r.city))?.filter((c) => !exclude.has(c.id)) ?? [];
  const typingAhead = query.trim() !== debounced || (searching && results.isFetching && !results.data);

  function pick(city: City) {
    onClose();
    if (options?.onPick) options.onPick(city);
    else navigate(`/cities/${city.id}`);
  }

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed inset-x-3 top-[12vh] z-50 mx-auto max-w-lg overflow-hidden rounded-lg border border-border bg-card shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
          aria-describedby={undefined}
        >
          <Dialog.Title className="sr-only">{options?.title ?? "Search cities"}</Dialog.Title>
          <Command shouldFilter={false} loop label={options?.title ?? "Search cities"}>
            <div className="flex items-center gap-2 border-b border-border px-3">
              <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <Command.Input
                autoFocus
                value={query}
                onValueChange={setQuery}
                placeholder={options?.title ?? "Search a city, e.g. London"}
                className="h-12 w-full bg-transparent text-base outline-none placeholder:text-muted-foreground"
              />
              {typingAhead && <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" aria-label="Searching" />}
              <kbd className="hidden rounded border border-border px-1.5 text-xs text-muted-foreground sm:inline">Esc</kbd>
            </div>
            <Command.List className="max-h-[50vh] overflow-y-auto p-2">
              {searching && results.isPending && (
                <div className="space-y-2 p-1" aria-hidden="true">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-9" />)}</div>
              )}
              {searching && results.isError && (
                <div role="alert" className="px-3 py-6 text-center text-sm">
                  <p className="font-medium">Search isn&apos;t available right now</p>
                  <p className="mt-1 text-muted-foreground">{results.error instanceof ApiError ? results.error.message : null}</p>
                  <button type="button" className="mt-3 text-sm font-medium text-accent hover:underline" onClick={() => results.refetch()}>Try again</button>
                </div>
              )}
              {searching && results.isSuccess && cities.length === 0 && !typingAhead && (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">No cities match &ldquo;{debounced}&rdquo;. Try another spelling.</p>
              )}
              {!searching && (
                <p className="px-3 pb-1 pt-2 text-xs font-medium text-muted-foreground">
                  {cities.length ? "Recent" : `Type at least ${MIN_QUERY} letters to search.`}
                </p>
              )}
              {cities.map((city) => (
                <Command.Item key={city.id} value={String(city.id)} onSelect={() => pick(city)} className={ITEM}>
                  {searching ? <MapPin className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                             : <Clock className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />}
                  <span className="min-w-0 truncate">
                    <span className="font-medium">{city.name}</span>
                    <span className="text-muted-foreground">{city.label.slice(city.name.length)}</span>
                  </span>
                </Command.Item>
              ))}
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Header button: a search field look-alike on desktop, an icon on phones. */
export function SearchButton({ className }: { className?: string }) {
  const { openSearch } = useSearch();
  return (
    <button
      type="button"
      onClick={() => openSearch()}
      aria-label="Search cities (Ctrl+K)"
      aria-keyshortcuts="Control+K Meta+K"
      className={cn(
        "flex h-9 items-center gap-2 rounded-md border border-border bg-card/70 px-2.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
        "focus-visible:outline-2 focus-visible:outline-accent sm:w-64 sm:px-3",
        className,
      )}
    >
      <Search className="size-4" aria-hidden="true" />
      <span className="hidden sm:inline">Search cities…</span>
      <kbd className="ml-auto hidden rounded border border-border px-1.5 text-xs sm:inline">Ctrl K</kbd>
    </button>
  );
}
