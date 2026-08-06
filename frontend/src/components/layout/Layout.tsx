import { Link, NavLink, Outlet } from "react-router-dom";
import { Mail, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/use-theme";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium transition-colors hover:text-foreground ${
    isActive ? "text-foreground" : "text-muted-foreground"
  }`;

export function Layout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Mail className="h-5 w-5 text-primary" />
            Email Verifier
          </Link>
          <nav className="flex items-center gap-6">
            <NavLink to="/" end className={navLinkClass}>
              Lists
            </NavLink>
            <NavLink to="/tools" className={navLinkClass}>
              Tools
            </NavLink>
            <NavLink to="/settings" className={navLinkClass}>
              Settings
            </NavLink>
            <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-3 text-xs text-muted-foreground">
          Local SMTP verification cannot fully confirm mailboxes on Gmail, Outlook, and similar
          providers. Risky results are expected — export them for a second pass if needed.
        </div>
      </footer>
    </div>
  );
}
