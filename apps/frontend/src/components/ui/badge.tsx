import { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("chip", className)} {...props} />;
}
