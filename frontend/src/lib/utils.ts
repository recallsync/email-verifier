import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    verified: "Verified",
    risky: "Risky",
    failed: "Failed",
    pending: "Pending",
    processing: "Processing",
    skipped: "Skipped",
    draft: "Draft",
    queued: "Queued",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
    interrupted: "Interrupted",
  };
  return map[status] ?? status;
}
