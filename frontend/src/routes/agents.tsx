import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AgentsTab } from "@/features/agents/components/AgentsTab";

export const Route = createFileRoute("/agents")({
  component: AgentsPage,
});

function AgentsPage() {
  useEffect(() => {
    document.title = "Agents — Manager AI";
  }, []);

  return <AgentsTab />;
}
