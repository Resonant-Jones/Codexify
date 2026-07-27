import { type ComponentProps, type ElementType, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

/**
 * Protocols that must never be rendered as actionable links.
 */
const UNSAFE_PROTOCOLS = /^(javascript|data|vbscript|file):/i

function isSafeHref(href: string | undefined): href is string {
  if (!href) return false
  const trimmed = href.trim()
  if (!trimmed) return false
  return !UNSAFE_PROTOCOLS.test(trimmed)
}

export interface MarkdownMessageProps {
  /** Persisted message content. Must not be destructively rewritten. */
  content: string
  /** Optional CSS class for the outermost wrapper. */
  className?: string
}

/**
 * Custom component overrides passed to react-markdown.
 *
 * Safety policy:
 * - Raw HTML is not enabled (react-markdown v10 disables it by default).
 * - Script, event handlers, and embedded iframes cannot be introduced
 *   through Markdown alone.
 * - Unsafe link protocols (`javascript:`, `data:`, `vbscript:`, `file:`)
 *   are stripped; safe external links open in a new tab with `noopener noreferrer`.
 * - Code blocks are rendered inline so the host can apply horizontal scrolling.
 */
function safeComponents(): ComponentProps<typeof ReactMarkdown>["components"] {
  return {
    a({ href, children, ...rest }) {
      if (!isSafeHref(href)) {
        // Strip the href so the text remains readable without being an
        // actionable link.
        return <span {...rest}>{children}</span>
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          {...rest}
        >
          {children}
        </a>
      )
    },

    // Inline code: keep it compact.
    code({ className, children, ...rest }: any) {
      // When react-markdown supplies a className it's a fenced code block
      // rendered inside <pre>; otherwise it's inline.
      if (className) {
        return (
          <code className={className} {...rest}>
            {children}
          </code>
        )
      }
      return <code {...rest}>{children}</code>
    },

    // Wrap fenced code in a container class so CSS can give it a
    // contained surface and horizontal scroll.
    pre({ children, ...rest }: any) {
      return (
        <pre className="md-code-block" {...rest}>
          {children}
        </pre>
      )
    },

    // Blockquotes get a dedicated class for a subtle boundary.
    blockquote({ children, ...rest }: any) {
      return (
        <blockquote className="md-blockquote" {...rest}>
          {children}
        </blockquote>
      )
    },
  }
}

const markdownPluggins = [remarkGfm]

/**
 * Render safe Markdown for assistant messages inside the Chrome side panel.
 *
 * This component wraps the same react-markdown + remark-gfm stack used by
 * the main Codexify chat renderer without importing AppShell-specific state,
 * routing, diagnostics, or layout dependencies.
 *
 * Raw HTML is intentionally disabled.  Unsafe link protocols are stripped.
 * Safe external links open in a new tab with `noopener noreferrer`.
 */
export function MarkdownMessage({
  content,
  className,
}: MarkdownMessageProps): React.JSX.Element {
  const components = useMemo(() => safeComponents(), [])

  if (!content) {
    return <div className={className} />
  }

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={markdownPluggins}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMessage
