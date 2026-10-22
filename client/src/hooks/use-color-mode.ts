import { useCallback, useEffect, useState } from "react";

export type ColorMode = "dark" | "light";
const STORAGE_KEY = "color-mode";

/** Light/dark, remembered in this browser. The first paint is set in index.html (dark first). */
export function useColorMode(): { mode: ColorMode; toggle: () => void } {
  const [mode, setMode] = useState<ColorMode>(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", mode === "dark");
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* private mode: just don't remember */
    }
  }, [mode]);

  const toggle = useCallback(() => setMode((m) => (m === "dark" ? "light" : "dark")), []);
  return { mode, toggle };
}
