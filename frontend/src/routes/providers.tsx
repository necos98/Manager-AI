import { createFileRoute } from "@tanstack/react-router";
import { ProviderConfigurationPage } from "@/features/providers/components/ProviderConfigurationPage";

export const Route = createFileRoute("/providers")({
  component: ProviderConfigurationPage,
});
