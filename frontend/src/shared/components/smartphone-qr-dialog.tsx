import { useQuery } from "@tanstack/react-query";
import QRCode from "react-qr-code";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog";

interface SmartphoneQrDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

async function fetchNetworkInfo(): Promise<{ local_ip: string }> {
  const res = await fetch("/api/network-info");
  if (!res.ok) throw new Error("Failed to fetch network info");
  return res.json();
}

export function SmartphoneQrDialog({ open, onOpenChange }: SmartphoneQrDialogProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["network-info"],
    queryFn: fetchNetworkInfo,
    enabled: open,
    staleTime: 30_000,
  });

  const url = data
    ? `http://${data.local_ip}:${window.location.port || "4173"}`
    : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Open on Smartphone</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4 py-4">
          {isLoading && (
            <p className="text-sm text-muted-foreground">Detecting network address...</p>
          )}
          {isError && (
            <p className="text-sm text-destructive">Could not detect local IP address.</p>
          )}
          {url && (
            <>
              <div className="bg-white p-4 rounded-lg">
                <QRCode value={url} size={200} />
              </div>
              <code className="text-xs text-muted-foreground break-all">{url}</code>
              <p className="text-xs text-muted-foreground text-center">
                Make sure your phone is on the same Wi-Fi network.
              </p>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
