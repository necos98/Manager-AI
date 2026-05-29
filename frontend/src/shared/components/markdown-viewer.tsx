import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, Check } from "lucide-react";

interface MarkdownViewerProps {
  content: string | null;
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  if (!content) return <p className="text-muted-foreground italic text-sm">No content</p>;

  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }) {
            if (inline) {
              return <code className={className} {...props}>{children}</code>;
            }

            const text = String(children).replace(/\n$/, "");
            const isCopied = copiedCode === text;

            return (
              <div className="relative group">
                <pre className={className}>
                  <code {...props}>{children}</code>
                </pre>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(text);
                    setCopiedCode(text);
                    setTimeout(() => setCopiedCode(null), 2000);
                  }}
                  className="absolute top-2 right-2 p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity bg-muted/80 hover:bg-muted text-muted-foreground"
                  title="Copy code"
                >
                  {isCopied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                </button>
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
