import { useState } from "react";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, rowStatusBadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type EmailResult = { email: string; status: string; reason: string };

export function ToolsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
        <p className="text-sm text-muted-foreground">Find and verify individual email addresses.</p>
      </div>

      <Tabs defaultValue="name" className="w-full">
        <TabsList className="grid w-full max-w-lg grid-cols-3">
          <TabsTrigger value="name">Find by Name</TabsTrigger>
          <TabsTrigger value="company">Find by Company</TabsTrigger>
          <TabsTrigger value="verify">Verify Email</TabsTrigger>
        </TabsList>

        <TabsContent value="name">
          <FindByNameTab />
        </TabsContent>
        <TabsContent value="company">
          <FindByCompanyTab />
        </TabsContent>
        <TabsContent value="verify">
          <VerifyEmailTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function FindByNameTab() {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    found: boolean;
    valid_email: string | null;
    best_guess?: string;
    permutations_tested: EmailResult[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.findEmail(name.trim(), domain.trim());
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Find the verified email address of any professional</CardTitle>
        <CardDescription>Tests common name patterns against the domain via SMTP.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input placeholder="Enter a full name..." value={name} onChange={(e) => setName(e.target.value)} />
          <span className="hidden text-muted-foreground sm:block">@</span>
          <Input placeholder="company.com" value={domain} onChange={(e) => setDomain(e.target.value)} />
          <Button onClick={submit} disabled={loading || !name || !domain}>
            <Search className="h-4 w-4" />
            {loading ? "Finding..." : "Find"}
          </Button>
        </div>

        {error && <p className="text-sm text-failed">{error}</p>}

        {result && (
          <div className="space-y-3 rounded-lg border border-border p-4">
            {result.found && result.valid_email ? (
              <div>
                <p className="text-lg font-semibold text-verified">{result.valid_email}</p>
                <p className="text-sm text-muted-foreground">Verified via SMTP</p>
              </div>
            ) : result.best_guess ? (
              <div>
                <p className="text-lg font-semibold text-risky">{result.best_guess}</p>
                <p className="text-sm text-muted-foreground">Best guess — verification inconclusive</p>
              </div>
            ) : (
              <p className="text-muted-foreground">No verified email found.</p>
            )}
            <Button variant="link" className="h-auto p-0" onClick={() => setShowAll(!showAll)}>
              {showAll ? "Hide" : "Show"} all {result.permutations_tested.length} patterns tested
            </Button>
            {showAll && <ResultTable rows={result.permutations_tested} />}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FindByCompanyTab() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    found: boolean;
    best_email: string | null;
    emails_tested: EmailResult[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.findEmailCompany(domain.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Find the best contact email for a company</CardTitle>
        <CardDescription>Tests info@, contact@, sales@, support@, hello@</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input placeholder="company.com" value={domain} onChange={(e) => setDomain(e.target.value)} />
          <Button onClick={submit} disabled={loading || !domain}>
            {loading ? "Finding..." : "Find"}
          </Button>
        </div>
        {error && <p className="text-sm text-failed">{error}</p>}
        {result && (
          <div className="space-y-3">
            {result.best_email && (
              <p className="font-medium">
                Best match:{" "}
                <span className={result.found ? "text-verified" : "text-risky"}>{result.best_email}</span>
              </p>
            )}
            <ResultTable rows={result.emails_tested} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function VerifyEmailTab() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ email: string; status: string; reason: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.verifyEmail(email.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const statusVariant = (s: string) => {
    if (s === "valid") return "verified" as const;
    if (s === "invalid") return "failed" as const;
    return "risky" as const;
  };

  const statusText = (s: string) => {
    if (s === "valid") return "Verified";
    if (s === "invalid") return "Failed";
    return "Risky";
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Verify any email address</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input placeholder="email@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button onClick={submit} disabled={loading || !email}>
            {loading ? "Verifying..." : "Verify"}
          </Button>
        </div>
        {error && <p className="text-sm text-failed">{error}</p>}
        {result && (
          <Card>
            <CardContent className="space-y-2 p-6">
              <p className="font-mono">{result.email}</p>
              <Badge variant={statusVariant(result.status)}>{statusText(result.status)}</Badge>
              <p className="text-sm text-muted-foreground">{result.reason}</p>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
}

function ResultTable({ rows }: { rows: EmailResult[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-muted-foreground">
          <th className="py-2">Email</th>
          <th className="py-2">Status</th>
          <th className="py-2">Reason</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.email} className="border-b border-border/40">
            <td className="py-2 font-mono text-xs">{r.email}</td>
            <td className="py-2">
              <Badge variant={rowStatusBadgeVariant(r.status === "valid" ? "verified" : r.status === "invalid" ? "failed" : "risky")}>
                {r.status === "valid" ? "Verified" : r.status === "invalid" ? "Failed" : "Risky"}
              </Badge>
            </td>
            <td className="py-2 text-muted-foreground">{r.reason}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
