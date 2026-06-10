import * as React from "react";

interface CheckboxProps {
  checked?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  className?: string;
  "aria-label"?: string;
}

export function Checkbox({ checked, onClick, className = "", "aria-label": ariaLabel }: CheckboxProps) {
  return (
    <div
      role="checkbox"
      aria-checked={checked ?? false}
      aria-label={ariaLabel}
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.(e as unknown as React.MouseEvent);
        }
      }}
      className={[
        "size-4 rounded border border-primary/40 flex items-center justify-center",
        "transition-colors cursor-pointer",
        checked ? "bg-primary text-primary-foreground border-primary" : "bg-transparent hover:border-primary",
        className,
      ].join(" ")}
    >
      {checked && (
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
          <path d="M2 5L4 7L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
}
