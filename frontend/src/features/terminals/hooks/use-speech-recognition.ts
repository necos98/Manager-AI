import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string; message?: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<{
    0: { transcript: string };
    isFinal: boolean;
    length: number;
  }>;
}

interface Options {
  lang?: string;
  onResult: (finalText: string, interim: string) => void;
  onError?: (message: string) => void;
}

interface Api {
  supported: boolean;
  listening: boolean;
  start: () => void;
  stop: () => void;
}

function resolveCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function useSpeechRecognition({ lang, onResult, onError }: Options): Api {
  const ctorRef = useRef<SpeechRecognitionCtor | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const finalRef = useRef("");
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);

  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);
  useEffect(() => { onResultRef.current = onResult; }, [onResult]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  useEffect(() => {
    const ctor = resolveCtor();
    ctorRef.current = ctor;
    setSupported(ctor !== null);
  }, []);

  const start = useCallback(() => {
    const ctor = ctorRef.current;
    if (!ctor) return;

    recognitionRef.current?.stop();

    const rec = new ctor();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang ?? navigator.language ?? "en-US";

    finalRef.current = "";

    rec.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const chunk = result[0].transcript;
        if (result.isFinal) {
          finalRef.current += chunk;
        } else {
          interim += chunk;
        }
      }
      onResultRef.current(finalRef.current, interim);
    };

    rec.onerror = (event) => {
      onErrorRef.current?.(event.error ?? event.message ?? "speech recognition error");
      setListening(false);
    };

    rec.onend = () => {
      setListening(false);
    };

    recognitionRef.current = rec;
    try {
      rec.start();
      setListening(true);
    } catch (e) {
      onErrorRef.current?.(e instanceof Error ? e.message : "failed to start recognition");
      setListening(false);
    }
  }, [lang]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
    };
  }, []);

  return { supported, listening, start, stop };
}
