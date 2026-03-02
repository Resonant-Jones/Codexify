import { useEffect, useState } from "react";
import { resolveApiUrl } from "@/lib/runtimeConfig";

type ThreadContent = {
  id: number;
  title: string;
  summary: string;
  created_at: string;
  updated_at: string;
  messages: Array<{
    id: number;
    role: string;
    content: string;
    created_at: string;
  }>;
};

type DocumentContent = {
  id: string;
  title?: string;
  filename?: string;
  content?: string;
  format?: string;
  filesize?: number;
  mime_type?: string;
  src_url?: string;
  created_at: string;
  updated_at: string;
};

type ShareData = {
  ok: boolean;
  target_type: "thread" | "document";
  target_id: number | string;
  content: ThreadContent | DocumentContent;
};

type SharePageProps = {
  token: string;
};

export function SharePage({ token }: SharePageProps) {
  const [data, setData] = useState<ShareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSharedContent = async () => {
      try {
        const response = await fetch(resolveApiUrl(`/api/share/${token}`));

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail || `Failed to load shared content (${response.status})`
          );
        }

        const json = await response.json();
        if (!json.ok) {
          throw new Error(json.detail || "Failed to load shared content");
        }

        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load shared content");
      } finally {
        setLoading(false);
      }
    };

    fetchSharedContent();
  }, [token]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100svh",
          fontSize: 14,
          color: "rgba(0,0,0,.6)",
        }}
      >
        Loading shared content…
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100svh",
          padding: 20,
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: 400 }}>
          <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
            Unable to load shared content
          </div>
          <div style={{ fontSize: 13, color: "rgba(0,0,0,.6)", lineHeight: 1.6 }}>
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100svh",
          color: "rgba(0,0,0,.6)",
        }}
      >
        No content found
      </div>
    );
  }

  // Render thread content
  if (data.target_type === "thread") {
    const thread = data.content as ThreadContent;
    return (
      <div
        style={{
          minHeight: "100svh",
          backgroundColor: "rgba(0,0,0,.02)",
        }}
      >
        <div
          style={{
            maxWidth: 800,
            margin: "0 auto",
            padding: "40px 20px",
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          {/* Header */}
          <header style={{ marginBottom: 40 }}>
            <h1
              style={{
                fontSize: 32,
                fontWeight: 700,
                margin: "0 0 8px 0",
                color: "rgba(0,0,0,.9)",
              }}
            >
              {thread.title}
            </h1>
            <p
              style={{
                fontSize: 13,
                color: "rgba(0,0,0,.6)",
                margin: 0,
              }}
            >
              Shared {new Date(thread.created_at).toLocaleDateString()} at{" "}
              {new Date(thread.created_at).toLocaleTimeString()}
            </p>
            {thread.summary && (
              <p
                style={{
                  fontSize: 14,
                  color: "rgba(0,0,0,.7)",
                  marginTop: 12,
                  lineHeight: 1.6,
                }}
              >
                {thread.summary}
              </p>
            )}
          </header>

          {/* Messages */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {thread.messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: 11,
                    textTransform: "uppercase",
                    color: msg.role === "user" ? "#0066cc" : "#008000",
                    minWidth: 60,
                  }}
                >
                  {msg.role}
                </div>
                <div
                  style={{
                    flex: 1,
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: "rgba(0,0,0,.8)",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {thread.messages.length === 0 && (
            <div
              style={{
                padding: 40,
                textAlign: "center",
                color: "rgba(0,0,0,.4)",
                fontSize: 13,
              }}
            >
              No messages in this thread
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render document content
  if (data.target_type === "document") {
    const doc = data.content as DocumentContent;
    const isGenerated = "content" in doc;

    return (
      <div
        style={{
          minHeight: "100svh",
          backgroundColor: "rgba(0,0,0,.02)",
        }}
      >
        <div
          style={{
            maxWidth: 800,
            margin: "0 auto",
            padding: "40px 20px",
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
        >
          {/* Header */}
          <header style={{ marginBottom: 40 }}>
            <h1
              style={{
                fontSize: 32,
                fontWeight: 700,
                margin: "0 0 8px 0",
                color: "rgba(0,0,0,.9)",
              }}
            >
              {isGenerated ? doc.title : doc.filename}
            </h1>
            <p
              style={{
                fontSize: 13,
                color: "rgba(0,0,0,.6)",
                margin: 0,
              }}
            >
              Shared {new Date(doc.created_at).toLocaleDateString()} at{" "}
              {new Date(doc.created_at).toLocaleTimeString()}
            </p>
          </header>

          {/* Content */}
          {isGenerated ? (
            <div
              style={{
                fontSize: 14,
                lineHeight: 1.8,
                color: "rgba(0,0,0,.8)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {doc.content}
            </div>
          ) : (
            <div
              style={{
                padding: 20,
                backgroundColor: "#fff",
                borderRadius: 8,
                border: "1px solid rgba(0,0,0,.08)",
              }}
            >
              <div style={{ fontSize: 13, marginBottom: 12 }}>
                <strong>Filename:</strong> {doc.filename}
              </div>
              <div style={{ fontSize: 13, marginBottom: 12 }}>
                <strong>Type:</strong> {doc.mime_type}
              </div>
              <div style={{ fontSize: 13, marginBottom: 12 }}>
                <strong>Size:</strong> {((doc.filesize || 0) / 1024).toFixed(2)} KB
              </div>
              <a
                href={doc.src_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-block",
                  padding: "8px 12px",
                  backgroundColor: "#0066cc",
                  color: "#fff",
                  borderRadius: 4,
                  textDecoration: "none",
                  fontSize: 13,
                  fontWeight: 500,
                  marginTop: 8,
                }}
              >
                Download Document
              </a>
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}
