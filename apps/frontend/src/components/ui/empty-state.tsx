import { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function EmptyState({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("empty-state", className)} {...props} />;
}
