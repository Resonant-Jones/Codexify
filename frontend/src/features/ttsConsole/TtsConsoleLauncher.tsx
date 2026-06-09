import { Volume2 } from "lucide-react";
import { useState } from "react";
import TtsConsoleWindow from "./TtsConsoleWindow";

type TtsConsoleLauncherProps = {
  className?: string;
};

export default function TtsConsoleLauncher({
  className,
}: TtsConsoleLauncherProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className={className}
        data-testid="tts-console-launcher"
        aria-label="TTS Console"
        title="TTS Console"
        onClick={() => setOpen(true)}
      >
        <Volume2 className="h-4 w-4" aria-hidden="true" />
      </button>
      <TtsConsoleWindow open={open} onClose={() => setOpen(false)} />
    </>
  );
}
