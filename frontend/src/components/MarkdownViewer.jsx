import ReactMarkdown from "react-markdown";

export default function MarkdownViewer({ content }) {
  if (!content) return <p className="text-gray-400 italic">No content</p>;
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
