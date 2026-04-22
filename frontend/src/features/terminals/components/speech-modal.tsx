import { useEffect, useState } from "react";
import { Mic, MicOff, Send, X } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/shared/components/ui/dialog";
import { Textarea } from "@/shared/components/ui/textarea";
import { useSpeechRecognition } from "@/features/terminals/hooks/use-speech-recognition";

interface SpeechModalProps {
  open: boolean;
  onClose: () => void;
  onSend: (text: string) => void;
}

export function SpeechModal({ open, onClose, onSend }: SpeechModalProps) {
  const [finalText, setFinalText] = useState("");
  const [interimText, setInterimText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { supported, listening, start, stop } = useSpeechRecognition({
    onResult: (finalT, interim) => {
      setFinalText(finalT);
      setInterimText(interim);
    },
    onError: (msg) => setError(msg),
  });

  useEffect(() => {
    if (open) {
      setFinalText("");
      setInterimText("");
      setError(null);
    } else {
      stop();
    }
  }, [open, stop]);

  function toggleListening() {
    setError(null);
    if (listening) {
      stop();
    } else {
      start();
    }
  }

  function handleSend() {
    const text = finalText.trim();
    if (!text) return;
    onSend(text);
  }

  const status: "unsupported" | "error" | "listening" | "idle" =
    !supported ? "unsupported" : error ? "error" : listening ? "listening" : "idle";

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Voice input</DialogTitle>
        </DialogHeader>

        {status === "unsupported" ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Voice input not supported in this browser.
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-center py-2">
              <Button
                type="button"
                size="lg"
                variant={listening ? "destructive" : "default"}
                onClick={toggleListening}
                aria-label={listening ? "Stop recording" : "Start recording"}
              >
                {listening ? <MicOff className="size-5 mr-2" /> : <Mic className="size-5 mr-2" />}
                {listening ? "Stop" : "Start"}
              </Button>
            </div>

            <div className="text-xs text-center text-muted-foreground h-4">
              {status === "listening" && "Listening…"}
              {status === "error" && `Error: ${error}`}
              {status === "idle" && (finalText ? "Review & edit, then Send." : "Click Start and speak.")}
            </div>

            {listening && (
              <div className="min-h-[3rem] rounded-md border bg-muted p-2 text-sm">
                <span>{finalText}</span>
                <span className="text-muted-foreground">{interimText}</span>
              </div>
            )}

            {!listening && (
              <Textarea
                value={finalText}
                onChange={(e) => setFinalText(e.target.value)}
                placeholder="Transcript will appear here. Edit if needed."
                className="min-h-[6rem]"
              />
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="ghost" onClick={onClose}>
            <X className="size-4 mr-1" />
            Cancel
          </Button>
          {status !== "unsupported" && (
            <Button onClick={handleSend} disabled={!finalText.trim() || listening}>
              <Send className="size-4 mr-1" />
              Send
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
