import { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant = "info" | "success" | "error";

type Props = HTMLAttributes<HTMLDivElement> & {
  variant?: Variant;
};

export function Toast({ className, variant = "info", ...props }: Props) {
  return <div className={cn("notice", variant !== "info" && variant, className)} role="status" {...props} />;
}
