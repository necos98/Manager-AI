import ReactMarkdown from "react-markdown";

interface MarkdownViewerProps {
  content: string | null;
}

export function MarkdownViewer({ content }: MarkdownViewerProps) {
  if (!content) return <p className="text-muted-foreground italic text-sm">No content</p>;
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
