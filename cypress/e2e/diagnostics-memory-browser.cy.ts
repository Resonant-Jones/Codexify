/**
 * Memory Browser Diagnostics E2E Tests
 *
 * Tests the RAG trace inspection panel under Settings → Diagnostics.
 * Validates that users can inspect semantic and memory retrieval results.
 */

describe("Memory Browser Diagnostics", () => {
  beforeEach(() => {
    // Start at the chat interface
    cy.visit("/chat");
  });

  it("displays the Diagnostics tab in Settings", () => {
    // Navigate to Settings
    cy.visit("/settings");

    // Verify Diagnostics tab exists
    cy.contains("button", "Diagnostics").should("exist").and("be.visible");
  });

  it("loads Memory Browser component when Diagnostics tab is clicked", () => {
    cy.visit("/settings");

    // Click Diagnostics tab
    cy.contains("button", "Diagnostics").click();

    // Verify Memory Browser header
    cy.contains("h2", "Memory Browser").should("be.visible");
    cy.contains("Inspect the context Codexify retrieved").should("be.visible");
  });

  it("shows empty state message when no RAG trace is available", () => {
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Should show no data message
    cy.contains("No RAG trace available yet").should("be.visible");
    cy.contains('Send a message with depth "normal"').should("be.visible");
  });

  it("displays metadata card with depth, thread ID, and timestamp", () => {
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Metadata card should exist
    cy.contains("Depth:").should("exist");
    cy.contains("Thread:").should("exist");
  });

  it("captures and displays RAG trace after chat completion", () => {
    // Intercept the completion API call
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Test response" },
        context: {
          semantic: [
            { text: "Semantic result 1", score: 0.95, metadata: {} },
            { text: "Semantic result 2", score: 0.88, metadata: {} },
          ],
          memory: [
            { text: "Memory result 1", score: 0.92, metadata: {} },
            { text: "Memory result 2", score: 0.85, metadata: {} },
          ],
        },
      },
    }).as("chatComplete");

    // Send a message in chat
    cy.get('textarea[placeholder*="Message"]').type("Test message{enter}");

    // Wait for completion
    cy.wait("@chatComplete");

    // Navigate to Settings → Diagnostics
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify Semantic Snippets section
    cy.contains("h3", "Semantic Snippets").should("be.visible");
    cy.contains("2 results").should("be.visible");
    cy.contains("Semantic result 1").should("be.visible");
    cy.contains("Semantic result 2").should("be.visible");

    // Verify Memory Recall section
    cy.contains("h3", "Memory Recall").should("be.visible");
    cy.contains("2 results").should("be.visible");
    cy.contains("Memory result 1").should("be.visible");
    cy.contains("Memory result 2").should("be.visible");
  });

  it("displays similarity scores for retrieved items", () => {
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Test" },
        context: {
          semantic: [{ text: "Test semantic", score: 0.951 }],
          memory: [{ text: "Test memory", score: 0.847 }],
        },
      },
    }).as("chatComplete");

    cy.get('textarea[placeholder*="Message"]').type("Test{enter}");
    cy.wait("@chatComplete");

    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify scores are displayed
    cy.contains("Score: 0.951").should("be.visible");
    cy.contains("Score: 0.847").should("be.visible");
  });

  it("displays metadata when available", () => {
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Test" },
        context: {
          semantic: [
            {
              text: "Test with metadata",
              score: 0.9,
              metadata: { source: "doc.pdf", page: 5 },
            },
          ],
          memory: [],
        },
      },
    }).as("chatComplete");

    cy.get('textarea[placeholder*="Message"]').type("Metadata test{enter}");
    cy.wait("@chatComplete");

    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify metadata is shown
    cy.contains("Metadata:").should("be.visible");
    cy.contains("source").should("be.visible");
  });

  it("preserves RAG trace across navigation from Chat to Settings", () => {
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Response" },
        context: {
          semantic: [{ text: "Preserved semantic data", score: 0.9 }],
          memory: [{ text: "Preserved memory data", score: 0.85 }],
        },
      },
    }).as("chatComplete");

    // Send message in chat
    cy.get('textarea[placeholder*="Message"]').type("Preserve test{enter}");
    cy.wait("@chatComplete");

    // Navigate away to dashboard
    cy.visit("/");

    // Navigate to Settings → Diagnostics
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Data should still be there
    cy.contains("Preserved semantic data").should("be.visible");
    cy.contains("Preserved memory data").should("be.visible");
  });

  it("updates trace when new completion is made", () => {
    // First completion
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "First" },
        context: {
          semantic: [{ text: "First semantic", score: 0.9 }],
          memory: [],
        },
      },
    }).as("firstComplete");

    cy.get('textarea[placeholder*="Message"]').type("First{enter}");
    cy.wait("@firstComplete");

    // Navigate to diagnostics
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();
    cy.contains("First semantic").should("be.visible");

    // Go back to chat
    cy.visit("/chat");

    // Second completion with different data
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 2, thread_id: 1, role: "assistant", content: "Second" },
        context: {
          semantic: [{ text: "Second semantic", score: 0.95 }],
          memory: [],
        },
      },
    }).as("secondComplete");

    cy.get('textarea[placeholder*="Message"]').type("Second{enter}");
    cy.wait("@secondComplete");

    // Check diagnostics again
    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Should show new data
    cy.contains("Second semantic").should("be.visible");
    cy.contains("First semantic").should("not.exist");
  });

  it("displays thread ID in metadata card", () => {
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 42, role: "assistant", content: "Test" },
        context: {
          semantic: [{ text: "Test", score: 0.9 }],
          memory: [],
        },
      },
    }).as("chatComplete");

    cy.get('textarea[placeholder*="Message"]').type("Thread ID test{enter}");
    cy.wait("@chatComplete");

    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify thread ID is displayed
    cy.contains("Thread: 42").should("be.visible");
  });

  it("displays timestamp in metadata card", () => {
    cy.intercept("POST", "/chat/*/complete*", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Test" },
        context: {
          semantic: [{ text: "Timestamp test", score: 0.9 }],
          memory: [],
        },
      },
    }).as("chatComplete");

    cy.get('textarea[placeholder*="Message"]').type("Timestamp test{enter}");
    cy.wait("@chatComplete");

    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify timestamp is displayed (should have "Time:" label)
    cy.contains("Time:").should("be.visible");
  });

  it("displays current depth mode in metadata", () => {
    // Set depth to "deep"
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("Deep").click();

    cy.intercept("POST", "/chat/*/complete*depth=deep", {
      statusCode: 200,
      body: {
        ok: true,
        message: { id: 1, thread_id: 1, role: "assistant", content: "Deep test" },
        context: {
          semantic: [{ text: "Deep semantic", score: 0.9 }],
          memory: [{ text: "Deep memory", score: 0.85 }],
        },
      },
    }).as("chatComplete");

    cy.get('textarea[placeholder*="Message"]').type("Deep mode test{enter}");
    cy.wait("@chatComplete");

    cy.visit("/settings");
    cy.contains("button", "Diagnostics").click();

    // Verify depth is shown
    cy.contains("Depth: deep").should("be.visible");
  });
});
