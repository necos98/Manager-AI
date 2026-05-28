import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PipelinesTab } from "@/features/pipelines/components/PipelinesTab";

export const Route = createFileRoute("/pipelines")({
  component: PipelinesPage,
});

function PipelinesPage() {
  useEffect(() => {
    document.title = "Pipelines — Manager AI";
  }, []);

  return <PipelinesTab />;
}
