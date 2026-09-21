import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[var(--accent)] text-[var(--heading)]",
        secondary: "border-[var(--b2)] bg-[var(--s2)] text-[var(--t2)]",
        destructive: "border-transparent bg-[var(--red-dim)] text-[var(--red)]",
        outline: "text-[var(--t2)]",
        success: "border-transparent bg-[var(--green-dim)] text-[var(--green)]",
        warning: "border-transparent bg-[var(--amber-dim)] text-[var(--amber)]",
        accent: "border-transparent bg-[var(--accent-dim)] text-[var(--accent-text)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
