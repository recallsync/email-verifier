import { useCallback, useEffect, useState } from "react";
import { api, type Settings } from "@/lib/api";

export function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    api.getSettings().then((s) => {
      setTheme(s.theme);
      document.documentElement.classList.toggle("dark", s.theme === "dark");
    }).catch(() => {
      document.documentElement.classList.add("dark");
    });
  }, []);

  const toggleTheme = useCallback(async () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      await api.updateSettings({ theme: next });
    } catch {
      /* keep local preference */
    }
  }, [theme]);

  return { theme, toggleTheme };
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSettings(await api.getSettings());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { settings, loading, refresh };
}
