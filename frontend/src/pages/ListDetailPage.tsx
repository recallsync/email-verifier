import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, Pause, Play, XCircle } from "lucide-react";
import { api, subscribeProgress, type List, type ListRow, type ProgressEvent } from "@/lib/api";
import { formatNumber, statusLabel } from "@/lib/utils";
import { Badge, listStatusBadgeVariant, rowStatusBadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";

export function ListDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [list, setList] = useState<List | null>(null);
  const [rows, setRows] = useState<ListRow[]>([]);
  const [rowsTotal, setRowsTotal] = useState(0);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    if (!id) return;
    try {
      setList(await api.getList(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "List not found");
    }
  }, [id]);

  const loadRows = useCallback(async () => {
    if (!id) return;
    const res = await api.getListRows(id, {
      status: statusFilter === "all" ? undefined : statusFilter,
      search: search || undefined,
      limit: 100,
    });
    setRows(res.rows);
    setRowsTotal(res.total);
  }, [id, statusFilter, search]);

  useEffect(() => {
    loadList();
    loadRows();
  }, [loadList, loadRows]);

  useEffect(() => {
    if (!id || !list) return;
    const active = ["queued", "processing", "paused"].includes(list.status);
    if (!active) return;

    return subscribeProgress(
      id,
      (evt) => {
        setProgress(evt);
        if (evt.status === "completed" || evt.status === "cancelled") {
          loadList();
          loadRows();
        }
      },
      () => loadList()
    );
  }, [id, list?.status, loadList, loadRows]);

  if (!id) return null;
  if (error) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm">
          <Link to="/"><ArrowLeft className="h-4 w-4" /> Back</Link>
        </Button>
        <p className="text-failed">{error}</p>
      </div>
    );
  }
  if (!list) return <p className="text-muted-foreground">Loading...</p>;

  const pct = list.total_rows
    ? Math.round(((progress?.processed ?? list.processed_rows) / list.total_rows) * 100)
    : 0;

  const isActive = ["queued", "processing", "paused"].includes(list.status);

  const action = async (fn: () => Promise<unknown>) => {
    await fn();
    await loadList();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Button asChild variant="ghost" size="sm" className="mb-2 -ml-2">
            <Link to="/"><ArrowLeft className="h-4 w-4" /> Lists</Link>
          </Button>
          <h1 className="text-2xl font-bold">{list.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant={listStatusBadgeVariant(list.status)}>{statusLabel(list.status)}</Badge>
            {list.filename && <span className="text-sm text-muted-foreground">{list.filename}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          {list.status === "processing" && (
            <Button variant="outline" size="sm" onClick={() => action(() => api.pauseList(id))}>
              <Pause className="h-4 w-4" /> Pause
            </Button>
          )}
          {list.status === "paused" && (
            <Button variant="outline" size="sm" onClick={() => action(() => api.resumeList(id))}>
              <Play className="h-4 w-4" /> Resume
            </Button>
          )}
          {isActive && (
            <Button variant="destructive" size="sm" onClick={() => action(() => api.cancelList(id))}>
              <XCircle className="h-4 w-4" /> Cancel
            </Button>
          )}
        </div>
      </div>

      {(isActive || list.processed_rows > 0) && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <div className="flex justify-between text-sm">
              <span>
                {formatNumber(progress?.processed ?? list.processed_rows)} / {formatNumber(list.total_rows)} rows
              </span>
              <span>{pct}%</span>
            </div>
            <Progress value={pct} />
            <div className="flex gap-6 text-sm">
              <span className="text-verified">Verified {(progress?.verified ?? list.verified_count).toLocaleString()}</span>
              <span className="text-risky">Risky {(progress?.risky ?? list.risky_count).toLocaleString()}</span>
              <span className="text-failed">Failed {(progress?.failed ?? list.failed_count).toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {list.status === "draft" && list.total_rows > 0 && (
        <Button onClick={() => action(() => api.verifyList(id))}>Start Verification</Button>
      )}

      {list.processed_rows > 0 && (
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <a href={api.exportUrl(id, "all")} download>
              <Download className="h-4 w-4" /> Download Full CSV
            </a>
          </Button>
          <Button asChild variant="outline">
            <a href={api.exportUrl(id, "risky_failed")} download>
              <Download className="h-4 w-4" /> Export Risky + Failed
            </a>
          </Button>
          <span className="self-center text-xs text-muted-foreground">
            {list.risky_count + list.failed_count} rows in risky/failed export
          </span>
        </div>
      )}

      {list.processed_rows > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <Input
                placeholder="Search email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
            <div className="flex flex-wrap gap-2">
              {(["all", "verified", "risky", "failed"] as const).map((f) => (
                <Button
                  key={f}
                  variant={statusFilter === f ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(f)}
                >
                  {f === "all" ? "All" : statusLabel(f)}
                </Button>
              ))}
            </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-2 pr-4">#</th>
                    <th className="py-2 pr-4">Email</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.row_index} className="border-b border-border/40">
                      <td className="py-2 pr-4 text-muted-foreground">{row.row_index + 1}</td>
                      <td className="py-2 pr-4 font-mono text-xs">{row.email}</td>
                      <td className="py-2 pr-4">
                        <Badge variant={rowStatusBadgeVariant(row.status)}>
                          {statusLabel(row.status)}
                        </Badge>
                      </td>
                      <td className="py-2 text-muted-foreground">{row.reason ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              Showing {rows.length} of {rowsTotal.toLocaleString()} rows
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
