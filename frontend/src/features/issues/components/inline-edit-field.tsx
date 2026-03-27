import { useState, useRef, useEffect } from "react";
import { Pencil, Check, X } from "lucide-react";
import { cn } from "@/shared/lib/utils";

interface InlineEditFieldProps {
  value: string;
  onSave: (value: string) => void;
  className?: string;
  inputClassName?: string;
  renderView?: (value: string) => React.ReactNode;
  validate?: (value: string) => string | null;
  multiline?: boolean;
  disabled?: boolean;
}

export function InlineEditField({
  value,
  onSave,
  className,
  inputClassName,
  renderView,
  validate,
  multiline = false,
  disabled = false,
}: InlineEditFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value);
      setError(null);
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError("Il campo non può essere vuoto");
      return;
    }
    if (validate) {
      const err = validate(trimmed);
      if (err) {
        setError(err);
        return;
      }
    }
    onSave(trimmed);
    setEditing(false);
  };

  const handleCancel = () => {
    setDraft(value);
    setError(null);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !multiline) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === "Escape") {
      handleCancel();
    }
    if (e.key === "Enter" && multiline && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSave();
    }
  };

  if (editing) {
    const sharedProps = {
      ref: inputRef as React.RefObject<HTMLInputElement & HTMLTextAreaElement>,
      value: draft,
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setDraft(e.target.value);
        setError(null);
      },
      onKeyDown: handleKeyDown,
      onBlur: handleSave,
      className: cn(
        "w-full rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring",
        inputClassName
      ),
    };

    return (
      <div className={cn("relative", className)}>
        {multiline ? (
          <textarea {...sharedProps} rows={3} />
        ) : (
          <input {...sharedProps} />
        )}
        {error && <p className="text-xs text-destructive mt-1">{error}</p>}
        <div className="flex gap-1 mt-1">
          <button
            onMouseDown={(e) => { e.preventDefault(); handleSave(); }}
            className="text-emerald-600 hover:text-emerald-700"
          >
            <Check className="size-3.5" />
          </button>
          <button
            onMouseDown={(e) => { e.preventDefault(); handleCancel(); }}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-start gap-1",
        !disabled && "cursor-pointer",
        className
      )}
      onClick={() => !disabled && setEditing(true)}
      title={disabled ? undefined : "Clicca per modificare"}
    >
      {renderView ? renderView(value) : <span className="text-sm">{value}</span>}
      {!disabled && (
        <Pencil className="size-3 mt-0.5 opacity-0 group-hover:opacity-60 shrink-0 text-muted-foreground" />
      )}
    </div>
  );
}
