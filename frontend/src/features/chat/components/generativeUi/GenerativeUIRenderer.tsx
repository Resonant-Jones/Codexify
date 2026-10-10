/**
 * Generative UI renderer.
 *
 * Dispatches a parsed artifact to either a registered native component or an
 * isolated sandbox frame. Anything unrecognized degrades to ordinary assistant
 * text rather than failing the message.
 *
 * Feature-gated: with the gate off, no artifact is rendered and no generated
 * code is executed. The marker is still stripped from display text.
 *
 * Contract: docs/architecture/generative-ui-contract.md
 */
import React from "react";
import {
  uiArtifactKey,
  type GenerativeUiArtifact,
  type NativeUiArtifact,
  type SandboxUiArtifact,
} from "./artifactCodec";
import { resolveNativeUiComponent } from "./nativeRegistry";
import GenerativeUIErrorBoundary from "./GenerativeUIErrorBoundary";
import SandboxFrame from "./SandboxFrame";

/**
 * Build-time gate, following the existing `VITE_PRIVATE_PREVIEW` pattern.
 * Default is off.
 */
export function isGenerativeUiEnabled(): boolean {
  return import.meta.env.VITE_GENERATIVE_UI === "true";
}

export type GenerativeUIRendererProps = {
  artifacts: GenerativeUiArtifact[];
  onSendPrompt?: (text: string) => void;
  onHeightChange?: (height: number) => void;
};

const NativeArtifact: React.FC<{ artifact: NativeUiArtifact }> = ({ artifact }) => {
  const entry = resolveNativeUiComponent(artifact.component);
  // An unregistered component id is never resolved dynamically.
  if (!entry) return null;
  const Component = entry.component;
  return (
    <div data-testid="generative-ui-native" data-component={artifact.component} className={entry.className}>
      <Component {...artifact.props} />
    </div>
  );
};

const GenerativeUIRenderer: React.FC<GenerativeUIRendererProps> = ({
  artifacts,
  onSendPrompt,
  onHeightChange,
}) => {
  if (!artifacts.length || !isGenerativeUiEnabled()) return null;

  return (
    <GenerativeUIErrorBoundary>
      <div className="flex flex-col gap-2" data-testid="generative-ui-stack">
        {artifacts.map((artifact, index) => {
          const key = uiArtifactKey(artifact, index);
          if (artifact.kind === "native") {
            return <NativeArtifact key={key} artifact={artifact} />;
          }
          const sandboxArtifact: SandboxUiArtifact = artifact;
          return (
            <SandboxFrame
              key={key}
              artifact={sandboxArtifact}
              onSendPrompt={onSendPrompt}
              onHeightChange={onHeightChange}
            />
          );
        })}
      </div>
    </GenerativeUIErrorBoundary>
  );
};

export default GenerativeUIRenderer;