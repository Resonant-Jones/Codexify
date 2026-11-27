import { useEffect, useState } from "react";
import api from "@/lib/api";
import { toAbsoluteMediaUrl } from "@/hooks/useUploader";
import { useRenderableMediaSrc } from "@/hooks/useRenderableMediaSrc";
import type { GeneratedImage } from "@/features/chat/imageGeneration";
import WorkspaceImageViewerModal from "@/features/workspace/components/WorkspaceImageViewerModal";

export function GeneratedChatImage({ id }: { id: string }) {
  const [image, setImage] = useState<GeneratedImage | null>(null);
  const [failed, setFailed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [zoom, setZoom] = useState(100);
  const renderable = useRenderableMediaSrc(image ? toAbsoluteMediaUrl(image.src_url) : "");
  useEffect(() => {
    let active = true;
    setImage(null);
    setFailed(false);
    void api
      .get<GeneratedImage>(`/api/media/generated-images/${encodeURIComponent(id)}`)
      .then(({ data }) => {
        if (active) setImage(data);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [id]);
  if (failed || renderable.status === "error") return <p role="status">Image unavailable</p>;
  if (!image || renderable.status !== "ready") return <p role="status">Loading image…</p>;
  return (
    <>
      <button
        type="button"
        aria-label="Open generated image"
        className="block w-full text-left"
        onClick={() => setExpanded(true)}
      >
        <img
          src={renderable.src}
          alt={image.prompt}
          className="block w-full h-auto"
          style={{ maxHeight: 480, objectFit: "contain" }}
          onError={() => setFailed(true)}
        />
      </button>
      <WorkspaceImageViewerModal
        image={
          expanded
            ? {
                id,
                src_url: toAbsoluteMediaUrl(image.src_url),
                title: "Generated image",
                caption: image.prompt,
                mime_type: "image/png",
              }
            : null
        }
        zoom={zoom}
        onZoomChange={setZoom}
        onClose={() => setExpanded(false)}
      />
    </>
  );
}
