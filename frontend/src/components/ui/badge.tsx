import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        verified: "border-transparent bg-verified/15 text-verified",
        risky: "border-transparent bg-risky/15 text-risky",
        failed: "border-transparent bg-failed/15 text-failed",
        muted: "border-transparent bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export function listStatusBadgeVariant(status: string): BadgeProps["variant"] {
  if (status === "verified" || status === "completed") return "verified";
  if (status === "risky" || status === "processing" || status === "queued") return "risky";
  if (status === "failed" || status === "cancelled" || status === "interrupted") return "failed";
  return "muted";
}

export function rowStatusBadgeVariant(status: string): BadgeProps["variant"] {
  if (status === "verified") return "verified";
  if (status === "risky" || status === "processing" || status === "pending") return "risky";
  if (status === "failed") return "failed";
  return "muted";
}
