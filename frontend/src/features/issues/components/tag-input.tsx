import { useState, useRef, useMemo, useCallback } from "react";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";

interface TagInputProps {
  /** Currently selected tags */
  tags: string[];
  /** Called when tags change (add/remove) */
  onChange: (tags: string[]) => void;
  /** All existing tags in the project for autocomplete */
  availableTags: string[];
  /** Disable the input */
  disabled?: boolean;
  /** Placeholder text for the input */
  placeholder?: string;
}

export function TagInput({
  tags,
  onChange,
  availableTags,
  disabled = false,
  placeholder = "Add tag...",
}: TagInputProps) {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter available tags that match the current input but aren't already selected
  const filteredSuggestions = useMemo(() => {
    const trimmed = input.trim();
    if (!trimmed) return [];
    const lowerInput = trimmed.toLowerCase();
    return availableTags.filter(
      (tag) =>
        tag.toLowerCase().includes(lowerInput) &&
        !tags.some((t) => t.toLowerCase() === tag.toLowerCase())
    );
  }, [input, availableTags, tags]);

  // Show "Create" option when input doesn't exactly match any available tag
  const showCreate =
    input.trim() !== "" &&
    !availableTags.some(
      (tag) => tag.toLowerCase() === input.trim().toLowerCase()
    );

  const showDropdown = isFocused && (filteredSuggestions.length > 0 || showCreate);

  const addTag = useCallback(
    (tag: string) => {
      const trimmed = tag.trim();
      if (!trimmed) return;
      if (trimmed.length > 50) return;
      if (tags.length >= 20) return;
      if (tags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) return;
      onChange([...tags, trimmed]);
      setInput("");
    },
    [tags, onChange],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (input.trim()) {
        addTag(input);
      }
    } else if (e.key === "Backspace" && !input && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const handleBlur = () => {
    // Small delay to allow mousedown on dropdown items to fire first
    setTimeout(() => setIsFocused(false), 150);
  };

  return (
    <div className="space-y-2">
      {/* Tag chips */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 pr-1">
              {tag}
              <button
                type="button"
                onClick={() => onChange(tags.filter((t) => t !== tag))}
                className="ml-0.5 hover:text-destructive cursor-pointer"
                disabled={disabled}
              >
                &times;
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Input with dropdown */}
      <div className="relative">
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          onFocus={() => setIsFocused(true)}
          disabled={disabled}
          placeholder={tags.length >= 20 ? "Max tags reached" : placeholder}
        />

        {showDropdown && (
          <div
            className="absolute top-full left-0 right-0 mt-1 border rounded-md bg-popover shadow-md z-10 max-h-40 overflow-y-auto"
            role="listbox"
          >
            {filteredSuggestions.map((suggestion) => (
              <div
                key={suggestion}
                onMouseDown={(e) => {
                  e.preventDefault();
                  addTag(suggestion);
                }}
                className="px-3 py-1.5 text-sm cursor-pointer hover:bg-accent"
                role="option"
                aria-selected={false}
              >
                {suggestion}
              </div>
            ))}
            {showCreate && (
              <div
                onMouseDown={(e) => {
                  e.preventDefault();
                  addTag(input);
                }}
                className="px-3 py-1.5 text-sm cursor-pointer hover:bg-accent border-t"
                role="option"
                aria-selected={false}
              >
                Create &ldquo;{input}&rdquo;
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
