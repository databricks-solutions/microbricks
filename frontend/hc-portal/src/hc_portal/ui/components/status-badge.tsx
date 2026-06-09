import { Badge } from "@/components/ui/badge";

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  completed: "default",
  active: "default",
  resulted: "default",
  paid: "default",
  collected: "default",
  scheduled: "secondary",
  pending: "secondary",
  sent: "secondary",
  ordered: "secondary",
  cancelled: "destructive",
  expired: "destructive",
  overdue: "destructive",
  no_show: "destructive",
};

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase().replace(/[\s-]/g, "_");
  const variant = STATUS_VARIANTS[normalized] ?? "outline";

  return <Badge variant={variant}>{status}</Badge>;
}
