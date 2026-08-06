import { useEffect, useState } from "react";
import { api, type Settings } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings } from "@/hooks/use-theme";

export function SettingsPage() {
  const { settings, loading, refresh } = useSettings();
  const [form, setForm] = useState<Partial<Settings>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) setForm(settings);
  }, [settings]);

  const update = (key: keyof Settings, value: string | number) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateSettings(form);
      await refresh();
      setMessage("Settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const concurrency = Number(form.concurrency ?? 10);

  if (loading && !settings) {
    return <p className="text-muted-foreground">Loading settings...</p>;
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Configure verification behavior. Defaults work out of the box.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Verification</CardTitle>
          <CardDescription>SMTP check parameters for list processing.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="concurrency">Concurrency (parallel checks)</Label>
            <Input
              id="concurrency"
              type="number"
              min={1}
              max={50}
              value={form.concurrency ?? ""}
              onChange={(e) => update("concurrency", Number(e.target.value))}
            />
            {concurrency > 25 && (
              <p className="text-xs text-risky">
                High concurrency may trigger rate limiting from Gmail, Outlook, and other providers.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeout">Timeout (seconds)</Label>
            <Input
              id="timeout"
              type="number"
              min={5}
              max={60}
              value={form.timeout_seconds ?? ""}
              onChange={(e) => update("timeout_seconds", Number(e.target.value))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="retries">Retry count</Label>
            <Input
              id="retries"
              type="number"
              min={0}
              max={3}
              value={form.retry_count ?? ""}
              onChange={(e) => update("retry_count", Number(e.target.value))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="helo">SMTP HELO domain (optional)</Label>
            <Input
              id="helo"
              placeholder="mail.yourdomain.com"
              value={form.smtp_helo_domain ?? ""}
              onChange={(e) => update("smtp_helo_domain", e.target.value)}
            />
          </div>

          {message && <p className="text-sm text-verified">{message}</p>}
          {error && <p className="text-sm text-failed">{error}</p>}

          <Button onClick={save} disabled={saving}>
            {saving ? "Saving..." : "Save settings"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Lists older than 90 days are automatically purged (weekly cron job).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
