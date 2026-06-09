import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/formatters";
import { cn } from "@/lib/utils";

const COLORS = [
  "bg-blue-600",
  "bg-emerald-600",
  "bg-violet-600",
  "bg-amber-600",
  "bg-rose-600",
  "bg-cyan-600",
  "bg-fuchsia-600",
  "bg-lime-600",
];

function hashName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

interface PatientAvatarProps {
  givenName: string;
  familyName: string;
  className?: string;
}

export function PatientAvatar({
  givenName,
  familyName,
  className,
}: PatientAvatarProps) {
  const initials = getInitials(givenName, familyName);
  const color = COLORS[hashName(givenName + familyName) % COLORS.length];

  return (
    <Avatar className={cn("", className)}>
      <AvatarFallback className={cn(color, "text-white font-medium")}>
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}
