import { forwardRef, InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-2xl border border-surface-border bg-surface px-5 py-4 text-lg text-charcoal",
        "placeholder:text-charcoal-soft/50 outline-none transition-all duration-200",
        "focus:border-gold-400 focus:ring-4 focus:ring-gold-100",
        className
      )}
      {...props}
    />
  );
});

Input.displayName = "Input";