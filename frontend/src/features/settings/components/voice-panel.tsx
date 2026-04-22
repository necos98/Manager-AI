import { useEffect, useMemo, useState } from "react";
import { useSettings, useUpdateSetting } from "@/features/settings/hooks";
import { Button } from "@/shared/components/ui/button";
import type { Setting } from "@/shared/types";

const KEYS = {
  enabled: "tts.enabled",
  cap: "tts.cap_chars",
  voice: "tts.voice",
  rate: "tts.rate",
  pitch: "tts.pitch",
  summarizeEnabled: "tts.summarize_enabled",
  summarizeModel: "tts.summarize_model",
  summarizePrompt: "tts.summarize_prompt",
  summarizeMaxLength: "tts.summarize_max_length",
  summarizeTimeout: "tts.summarize_timeout_seconds",
} as const;

const DEFAULT_PROMPT =
  "Riassumi il seguente testo per la lettura vocale in italiano. Scrivi in prosa scorrevole, massimo {max_length} parole. Niente code block, niente liste puntate, niente markdown. Se ci sono comandi o nomi di file leggili come testo normale.";

function readSetting(settings: Setting[] | undefined, key: string, fallback: string) {
  const s = settings?.find((x) => x.key === key);
  return s?.value ?? fallback;
}

export function VoicePanel() {
  const { data: settings } = useSettings();
  const update = useUpdateSetting();

  const enabled = readSetting(settings, KEYS.enabled, "false") === "true";
  const cap = Number(readSetting(settings, KEYS.cap, "500"));
  const voice = readSetting(settings, KEYS.voice, "");
  const rate = Number(readSetting(settings, KEYS.rate, "1.0"));
  const pitch = Number(readSetting(settings, KEYS.pitch, "1.0"));
  const summarizeEnabled =
    readSetting(settings, KEYS.summarizeEnabled, "false") === "true";
  const summarizeModel = readSetting(
    settings,
    KEYS.summarizeModel,
    "claude-haiku-4-5-20251001",
  );
  const summarizePrompt = readSetting(
    settings,
    KEYS.summarizePrompt,
    DEFAULT_PROMPT,
  );
  const summarizeMaxLength = Number(
    readSetting(settings, KEYS.summarizeMaxLength, "60"),
  );
  const summarizeTimeout = Number(
    readSetting(settings, KEYS.summarizeTimeout, "10"),
  );

  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  useEffect(() => {
    function load() {
      setVoices(window.speechSynthesis.getVoices());
    }
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, []);

  const sortedVoices = useMemo(
    () => [...voices].sort((a, b) => a.name.localeCompare(b.name)),
    [voices],
  );

  function set(key: string, value: string) {
    update.mutate({ key, value });
  }

  function testVoice() {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance("Questa è una prova della voce.");
    const v = sortedVoices.find((x) => x.name === voice);
    if (v) u.voice = v;
    u.rate = rate;
    u.pitch = pitch;
    window.speechSynthesis.speak(u);
  }

  return (
    <div className="space-y-4">
      <div className="border rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="font-medium text-sm">Enable TTS</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Speak Claude's response out loud when it finishes.
          </p>
        </div>
        <button
          role="switch"
          aria-checked={enabled}
          onClick={() => set(KEYS.enabled, enabled ? "false" : "true")}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            enabled ? "bg-primary" : "bg-input"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      <div className="border rounded-lg p-4 space-y-2">
        <label className="text-sm font-medium">Max characters</label>
        <input
          type="number"
          min={50}
          max={5000}
          step={50}
          value={cap}
          onChange={(e) =>
            set(KEYS.cap, String(Math.max(50, Math.min(5000, Number(e.target.value) || 500))))
          }
          className="w-32 border rounded px-2 py-1 text-sm bg-background"
        />
        <p className="text-xs text-muted-foreground">
          Longer messages are cut at a sentence or word boundary and end with "…".
        </p>
      </div>

      <div className="border rounded-lg p-4 space-y-2">
        <label className="text-sm font-medium">Voice</label>
        <select
          value={voice}
          onChange={(e) => set(KEYS.voice, e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm bg-background"
        >
          <option value="">Default (OS)</option>
          {sortedVoices.map((v) => (
            <option key={v.name} value={v.name}>
              {v.name} ({v.lang})
            </option>
          ))}
        </select>
      </div>

      <div className="border rounded-lg p-4 space-y-3">
        <div>
          <label className="text-sm font-medium">Rate — {rate.toFixed(1)}</label>
          <input
            type="range"
            min={0.5}
            max={2}
            step={0.1}
            value={rate}
            onChange={(e) => set(KEYS.rate, e.target.value)}
            className="w-full"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Pitch — {pitch.toFixed(1)}</label>
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={pitch}
            onChange={(e) => set(KEYS.pitch, e.target.value)}
            className="w-full"
          />
        </div>
      </div>

      <div className="border rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-sm">Pre-process with Haiku</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Rewrite Claude's response as flowing prose (no markdown, no code
              blocks) before reading it out loud.
            </p>
          </div>
          <button
            role="switch"
            aria-checked={summarizeEnabled}
            onClick={() =>
              set(KEYS.summarizeEnabled, summarizeEnabled ? "false" : "true")
            }
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
              summarizeEnabled ? "bg-primary" : "bg-input"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                summarizeEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Model</label>
          <input
            type="text"
            value={summarizeModel}
            onChange={(e) => set(KEYS.summarizeModel, e.target.value)}
            className="w-full border rounded px-2 py-1 text-sm bg-background font-mono"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Prompt</label>
          <textarea
            value={summarizePrompt}
            onChange={(e) => set(KEYS.summarizePrompt, e.target.value)}
            rows={5}
            className="w-full border rounded px-2 py-1 text-sm bg-background font-mono"
          />
          <p className="text-xs text-muted-foreground">
            {"{max_length}"} is replaced with the value below before the prompt
            is sent.
          </p>
        </div>

        <div className="flex gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Max length (words)</label>
            <input
              type="number"
              min={10}
              max={500}
              step={5}
              value={summarizeMaxLength}
              onChange={(e) =>
                set(
                  KEYS.summarizeMaxLength,
                  String(
                    Math.max(
                      10,
                      Math.min(500, Number(e.target.value) || 60),
                    ),
                  ),
                )
              }
              className="w-32 border rounded px-2 py-1 text-sm bg-background"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Timeout (s)</label>
            <input
              type="number"
              min={2}
              max={120}
              step={1}
              value={summarizeTimeout}
              onChange={(e) =>
                set(
                  KEYS.summarizeTimeout,
                  String(
                    Math.max(2, Math.min(120, Number(e.target.value) || 10)),
                  ),
                )
              }
              className="w-32 border rounded px-2 py-1 text-sm bg-background"
            />
          </div>
        </div>
      </div>

      <Button variant="outline" size="sm" onClick={testVoice}>
        Test voice
      </Button>
    </div>
  );
}
