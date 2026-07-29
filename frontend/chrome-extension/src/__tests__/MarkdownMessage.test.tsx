import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { MarkdownMessage } from "../MarkdownMessage"

describe("MarkdownMessage", () => {
  it("renders bold markdown as a semantic <strong> element", () => {
    render(<MarkdownMessage content="Hello **bold** world." />)
    const el = screen.getByText("bold")
    expect(el.tagName).toBe("STRONG")
  })

  it("renders italic markdown semantically", () => {
    render(<MarkdownMessage content="This is *italic* text." />)
    const el = screen.getByText("italic")
    expect(el.tagName).toBe("EM")
  })

  it("renders ordered lists as <ol>", () => {
    render(<MarkdownMessage content={"1. First\n2. Second\n"} />)
    const list = screen.getByRole("list")
    expect(list.tagName).toBe("OL")
    const items = screen.getAllByRole("listitem")
    expect(items).toHaveLength(2)
  })

  it("renders unordered lists as <ul>", () => {
    render(<MarkdownMessage content={"- Alpha\n- Beta\n"} />)
    const list = screen.getByRole("list")
    expect(list.tagName).toBe("UL")
    const items = screen.getAllByRole("listitem")
    expect(items).toHaveLength(2)
  })

  it("renders inline code as <code>", () => {
    render(<MarkdownMessage content="Use `fn()` to call." />)
    const codeEl = screen.getByText("fn()")
    expect(codeEl.tagName).toBe("CODE")
  })

  it("renders fenced code as a contained code block", () => {
    render(
      <MarkdownMessage
        content={"```ts\nconst x = 1;\n```"}
      />,
    )
    // The <pre> should carry our wrapper class
    const pre = document.querySelector(".md-code-block")
    expect(pre).toBeTruthy()
    expect(pre!.tagName).toBe("PRE")
    const code = pre!.querySelector("code")
    expect(code).toBeTruthy()
    expect(code!.textContent).toContain("const x = 1")
  })

  it("renders blockquotes semantically", () => {
    render(<MarkdownMessage content={"> A quoted line"} />)
    const bq = document.querySelector(".md-blockquote")
    expect(bq).toBeTruthy()
    expect(bq!.tagName).toBe("BLOCKQUOTE")
    expect(bq!.textContent).toContain("A quoted line")
  })

  it("renders a safe HTTPS link with target and rel attributes", () => {
    render(
      <MarkdownMessage
        content="Visit [Codexify](https://codexify.example) for more."
      />,
    )
    const link = screen.getByRole("link", { name: "Codexify" })
    expect(link).toBeTruthy()
    expect(link.getAttribute("href")).toBe("https://codexify.example")
    expect(link.getAttribute("target")).toBe("_blank")
    expect(link.getAttribute("rel")).toBe("noopener noreferrer")
  })

  it("does not make javascript: protocol actionable", () => {
    render(
      <MarkdownMessage
        content="Click [malicious](javascript:alert(1)) here."
      />,
    )
    // The text should still be visible but not as a link.
    expect(screen.queryByRole("link")).toBeNull()
    expect(screen.getByText("malicious")).toBeTruthy()
  })

  it("does not make data: protocol actionable", () => {
    render(
      <MarkdownMessage
        content="See [data](data:text/html,<script>alert(1)</script>) link."
      />,
    )
    expect(screen.queryByRole("link")).toBeNull()
    expect(screen.getByText("data")).toBeTruthy()
  })

  it("does not create a script element from raw <script> input", () => {
    render(
      <MarkdownMessage
        content={'<script>alert("xss")</script>'}
      />,
    )
    expect(document.querySelector("script")).toBeNull()
  })

  it("does not create executable DOM from raw event-handler HTML", () => {
    render(
      <MarkdownMessage
        content={'<img src=x onerror="alert(1)">'}
      />,
    )
    // The raw HTML should appear as inert text or be omitted entirely.
    // It must not produce an img element.
    expect(document.querySelector("img")).toBeNull()
  })

  it("does not throw on empty content", () => {
    const { container } = render(<MarkdownMessage content="" />)
    expect(container.querySelector(".codexify-markdown") || container.firstChild).toBeTruthy()
  })

  it("renders ordinary plain text as readable text", () => {
    render(<MarkdownMessage content="Just some ordinary text." />)
    expect(screen.getByText("Just some ordinary text.")).toBeTruthy()
  })

  it("renders headings at multiple levels", () => {
    render(
      <MarkdownMessage
        content={"# Heading 1\n\n## Heading 2\n\n### Heading 3"}
      />,
    )
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Heading 1")
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Heading 2")
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("Heading 3")
  })

  it("renders strikethrough via GFM", () => {
    render(<MarkdownMessage content="This is ~~strikethrough~~ text." />)
    const el = screen.getByText("strikethrough")
    expect(el.tagName).toBe("DEL")
  })

  it("renders horizontal rules", () => {
    const { container } = render(
      <MarkdownMessage content={"Above\n\n---\n\nBelow"} />,
    )
    expect(container.querySelector("hr")).toBeTruthy()
  })

  it("renders nested lists", () => {
    render(
      <MarkdownMessage
        content={"- Outer\n  - Inner A\n  - Inner B\n"}
      />,
    )
    const items = screen.getAllByRole("listitem")
    expect(items).toHaveLength(3)
    expect(items[0].textContent).toContain("Outer")
    expect(items[1].textContent).toContain("Inner A")
  })

  it("renders a GFM table when the dependency supplies it", () => {
    render(
      <MarkdownMessage
        content={"| A | B |\n| --- | --- |\n| 1 | 2 |\n"}
      />,
    )
    const table = document.querySelector("table")
    expect(table).toBeTruthy()
    expect(table!.textContent).toContain("A")
    expect(table!.textContent).toContain("2")
  })

  it("exposes the codexify-markdown wrapper class", () => {
    const { container } = render(
      <MarkdownMessage content="Hello" className="codexify-markdown" />,
    )
    expect(container.querySelector(".codexify-markdown")).toBeTruthy()
  })
})
