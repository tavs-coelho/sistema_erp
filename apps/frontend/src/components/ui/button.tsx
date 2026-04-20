import { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const variantClass: Record<Variant, string> = {
  primary: "btn btn-primary",
  secondary: "btn",
  ghost: "btn btn-ghost",
  danger: "btn btn-danger",
};

const sizeClass: Record<Size, string> = {
  sm: "btn-sm",
  md: "",
  lg: "btn-lg",
};

export function Button({ className, variant = "secondary", size = "md", ...props }: Props) {
  return <button className={cn(variantClass[variant], sizeClass[size], className)} {...props} />;
}
