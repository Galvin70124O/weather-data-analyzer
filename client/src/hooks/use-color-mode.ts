import { useCallback, useSyncExternalStore } from "react";

export type ColorMode = "dark" | "light";
const STORAGE_KEY = "color-mode";

/*
 * Light/dark lives on <html class="dark"> (the first paint is set in index.html, dark first) and is
 * remembered in this browser. A tiny shared store, so the header toggle and the Account page
 * always agree.
 */
const listeners = new Set<() => void>();

function current(): ColorMode {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function setColorMode(mode: ColorMode): void {
  document.documentElement.classList.toggle("dark", mode === "dark");
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* private mode: just don't remember */
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useColorMode(): { mode: ColorMode; setMode: (mode: ColorMode) => void; toggle: () => void } {
  const mode = useSyncExternalStore(subscribe, current);
  const toggle = useCallback(() => setColorMode(current() === "dark" ? "light" : "dark"), []);
  return { mode, setMode: setColorMode, toggle };
}
