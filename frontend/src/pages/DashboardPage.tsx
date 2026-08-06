import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, Download, Play, FileSpreadsheet } from "lucide-react";
import { api, type List } from "@/lib/api";
import { formatNumber, formatRelativeDate, statusLabel } from "@/lib/utils";
import { Badge, listStatusBadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardPage() {
  const [lists, setLists] = useState<List[]>([]);
  const [stats, setStats] = useState({ total_emails_verified: 0, total_lists: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [listsRes, statsRes] = await Promise.all([api.getLists({ limit: 100 }), api.getStats()]);
      setLists(listsRes.lists);
      setStats(statsRes);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load lists");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const active = lists.find((l) => l.status === "processing");
  const queued = lists.filter((l) => l.status === "queued");

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this list and all results?")) return;
    await api.deleteList(id);
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Lists</h1>
          <p className="text-sm text-muted-foreground">
            {formatNumber(stats.total_emails_verified)} emails verified across {stats.total_lists} lists
          </p>
        </div>
        <Button asChild>
          <Link to="/lists/new">
            <Plus className="h-4 w-4" />
            New List
          </Link>
        </Button>
      </div>

      {active && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div>
              <p className="font-medium">
                Verifying: {active.name} — {formatNumber(active.processed_rows)} / {formatNumber(active.total_rows)}
              </p>
              <p className="text-sm text-muted-foreground">
                Verified {active.verified_count} · Risky {active.risky_count} · Failed {active.failed_count}
              </p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to={`/lists/${active.id}`}>View</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {queued.length > 0 && !active && (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">
            Queue: &quot;{queued[0].name}&quot; waiting to start
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-failed/50">
          <CardContent className="p-4 text-sm text-failed">{error}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All lists</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading && lists.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">Loading...</p>
          ) : lists.length === 0 ? (
            <div className="flex flex-col items-center gap-4 p-12 text-center">
              <p className="text-muted-foreground">Upload your first lead list to get started.</p>
              <Button asChild>
                <Link to="/lists/new">New List</Link>
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="px-6 py-3 font-medium">Name</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                    <th className="px-6 py-3 font-medium">Rows</th>
                    <th className="px-6 py-3 font-medium">Results</th>
                    <th className="px-6 py-3 font-medium">Created</th>
                    <th className="px-6 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {lists.map((list) => (
                    <tr key={list.id} className="border-b border-border/50 hover:bg-muted/30">
                      <td className="px-6 py-3">
                        <Link to={`/lists/${list.id}`} className="font-medium hover:text-primary">
                          {list.name}
                        </Link>
                        {list.filename && (
                          <p className="text-xs text-muted-foreground">{list.filename}</p>
                        )}
                      </td>
                      <td className="px-6 py-3">
                        <Badge variant={listStatusBadgeVariant(list.status)}>
                          {statusLabel(list.status)}
                        </Badge>
                      </td>
                      <td className="px-6 py-3">{formatNumber(list.total_rows)}</td>
                      <td className="px-6 py-3 text-xs text-muted-foreground">
                        {list.processed_rows > 0 ? (
                          <>
                            <span className="text-verified">{list.verified_count}V</span>{" "}
                            <span className="text-risky">{list.risky_count}R</span>{" "}
                            <span className="text-failed">{list.failed_count}F</span>
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-6 py-3 text-muted-foreground">
                        {formatRelativeDate(list.created_at)}
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex gap-1">
                          {list.status === "draft" && list.total_rows > 0 && (
                            <Button asChild variant="ghost" size="icon" title="Open to verify">
                              <Link to={`/lists/${list.id}`}>
                                <Play className="h-4 w-4" />
                              </Link>
                            </Button>
                          )}
                          {list.processed_rows > 0 && (
                            <>
                              <Button asChild variant="ghost" size="icon" title="Export CSV">
                                <a href={api.exportUrl(list.id, "all", "csv")} download>
                                  <Download className="h-4 w-4" />
                                </a>
                              </Button>
                              <Button asChild variant="ghost" size="icon" title="Export XLSX">
                                <a href={api.exportUrl(list.id, "all", "xlsx")} download>
                                  <FileSpreadsheet className="h-4 w-4" />
                                </a>
                              </Button>
                            </>
                          )}
                          {list.status !== "processing" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              title="Delete"
                              onClick={() => handleDelete(list.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
