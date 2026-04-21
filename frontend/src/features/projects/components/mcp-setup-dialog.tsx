import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";
import { Button } from "@/shared/components/ui/button";
import { Separator } from "@/shared/components/ui/separator";

interface McpSetupDialogProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function McpSetupDialog({ projectId, open, onOpenChange }: McpSetupDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>MCP Server Setup</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 min-w-0">
          <div className="min-w-0">
            <h3 className="font-medium text-sm mb-1">Endpoint URL</h3>
            <code className="block bg-muted rounded px-3 py-2 text-sm font-mono break-all">
              http://localhost:8000/mcp/
            </code>
          </div>

          <Separator />

          <div className="min-w-0">
            <h3 className="font-medium text-sm mb-2">Claude Code</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Run this command in your terminal:
            </p>
            <pre className="bg-muted rounded px-3 py-2 text-sm font-mono whitespace-pre-wrap break-all">
              claude mcp add --transport http ManagerAi http://localhost:8000/mcp/
            </pre>
          </div>

          <Separator />

          <div className="min-w-0">
            <h3 className="font-medium text-sm mb-2">Other MCP Clients</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Add this to your client configuration (Streamable HTTP):
            </p>
            <pre className="bg-muted rounded px-3 py-2 text-sm font-mono overflow-x-auto max-w-full">
              {JSON.stringify(
                {
                  mcpServers: {
                    ManagerAi: {
                      type: "url",
                      url: "http://localhost:8000/mcp/",
                    },
                  },
                },
                null,
                2,
              )}
            </pre>
          </div>

          <Separator />

          <div className="min-w-0">
            <h3 className="font-medium text-sm mb-1">Project ID</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Most tools require the <code className="bg-muted px-1 rounded">project_id</code> parameter:
            </p>
            <code className="block bg-muted rounded px-3 py-2 text-sm font-mono break-all">
              {projectId}
            </code>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-sm text-blue-800">
              <span className="font-medium">Tip:</span> Use the "Install manager.json" action to automatically place the project ID file in your project root.
            </p>
          </div>
        </div>

        <Button variant="outline" className="w-full" onClick={() => onOpenChange(false)}>
          Close
        </Button>
      </DialogContent>
    </Dialog>
  );
}
