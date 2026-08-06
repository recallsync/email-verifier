import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function NewListPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [listId, setListId] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    total_rows: number;
    email_column: string;
    estimated_duration: string;
    columns: string[];
  } | null>(null);
  const [ambiguousColumns, setAmbiguousColumns] = useState<string[] | null>(null);
  const [selectedColumn, setSelectedColumn] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (f: File | null) => {
    if (f) {
      const lower = f.name.toLowerCase();
      if (!lower.endsWith(".csv") && !lower.endsWith(".xlsx") && !lower.endsWith(".xlsm")) {
        setError("Please upload a CSV or XLSX file.");
        return;
      }
    }
    setFile(f);
    setUploadResult(null);
    setAmbiguousColumns(null);
    setError(null);
  };

  const upload = async (emailColumn?: string) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      let id = listId;
      if (!id) {
        if (!name.trim()) {
          setError("List name is required");
          setLoading(false);
          return;
        }
        const created = await api.createList(name.trim());
        id = created.id;
        setListId(id);
      }
      const result = await api.uploadCsv(id, file, emailColumn);
      setUploadResult(result);
      setAmbiguousColumns(null);
    } catch (e) {
      const err = e as Error & { columns?: string[]; error?: string };
      if (err.columns?.length) {
        setAmbiguousColumns(err.columns);
        setError(err.message);
      } else {
        setError(err.message || "Upload failed");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!listId) return;
    setLoading(true);
    try {
      await api.verifyList(listId);
      navigate(`/lists/${listId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to queue list");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">New List</h1>
        <p className="text-sm text-muted-foreground">Upload a CSV to verify email addresses locally.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>List details</CardTitle>
          <CardDescription>Name your list and upload a CSV or Excel (.xlsx) file.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">List name</Label>
            <Input
              id="name"
              placeholder="e.g. Q1 Dental Leads"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!!listId}
            />
          </div>

          <div
            className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 transition-colors hover:border-primary/50"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFile(e.dataTransfer.files[0] ?? null);
            }}
          >
            <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Drag and drop CSV or XLSX, or click to browse</p>
            <Input
              type="file"
              accept=".csv,.xlsx,.xlsm"
              className="mt-4 max-w-xs"
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            />
            {file && <p className="mt-2 text-sm font-medium">{file.name}</p>}
          </div>

          {ambiguousColumns && (
            <div className="space-y-2">
              <Label>Email column</Label>
              <Select value={selectedColumn} onValueChange={setSelectedColumn}>
                <SelectTrigger>
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {ambiguousColumns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                disabled={!selectedColumn || loading}
                onClick={() => upload(selectedColumn)}
              >
                Upload with selected column
              </Button>
            </div>
          )}

          {error && <p className="text-sm text-failed">{error}</p>}

          {uploadResult && (
            <div className="rounded-lg bg-muted/50 p-4 text-sm space-y-1">
              <p className="font-medium">{uploadResult.total_rows.toLocaleString()} rows detected</p>
              <p className="text-muted-foreground">Email column: {uploadResult.email_column}</p>
              <p className="text-muted-foreground">Estimated: {uploadResult.estimated_duration}</p>
            </div>
          )}

          <div className="flex gap-2">
            {!uploadResult && file && !ambiguousColumns && (
              <Button disabled={loading} onClick={() => upload()}>
                {loading ? "Uploading..." : "Upload CSV"}
              </Button>
            )}
            {uploadResult && (
              <>
                <Button onClick={handleVerify} disabled={loading}>
                  Start Verification
                </Button>
                <Button variant="outline" onClick={() => handleFile(null)}>
                  Different file
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
