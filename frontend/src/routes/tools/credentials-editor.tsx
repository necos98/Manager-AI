import { createFileRoute } from "@tanstack/react-router";
import { CredentialsEditorPage } from "@/features/credentials-editor/components/credentials-editor";

export const Route = createFileRoute("/tools/credentials-editor")({
  component: CredentialsEditorPage,
});
