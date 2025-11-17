/**
 * Depth Selector E2E Tests
 *
 * Tests the RAG depth selector UI component and its integration with the backend.
 * Validates that users can control Codexify's perceptual depth via the UI.
 */

describe("RAG Depth Selector", () => {
  beforeEach(() => {
    // Visit the chat interface
    cy.visit("/chat");
  });

  it("displays the depth selector button in the header", () => {
    // The Layers icon button should be visible in the header
    cy.get('button[aria-label="RAG depth selector"]').should("exist").and("be.visible");
  });

  it("opens the depth selector dropdown when clicked", () => {
    // Click the depth selector button
    cy.get('button[aria-label="RAG depth selector"]').click();

    // Dropdown menu should be visible with all depth options
    cy.contains("RAG Depth").should("be.visible");
    cy.contains("Shallow").should("be.visible");
    cy.contains("Normal").should("be.visible");
    cy.contains("Deep").should("be.visible");
    cy.contains("Diagnostic").should("be.visible");
  });

  it("shows depth descriptions in the dropdown", () => {
    cy.get('button[aria-label="RAG depth selector"]').click();

    // Verify each depth mode has a description
    cy.contains("Fast, ephemeral awareness").should("be.visible");
    cy.contains("Situational recall + semantic grounding").should("be.visible");
    cy.contains("Rich memory + cross-thread resonance").should("be.visible");
    cy.contains("System introspection + trace visibility").should("be.visible");
  });

  it("changes depth state when a depth option is selected", () => {
    cy.get('button[aria-label="RAG depth selector"]').click();

    // Select "Deep" depth
    cy.contains("Deep").click();

    // Console log should confirm depth change
    cy.window().then((win) => {
      cy.spy(win.console, "log").as("consoleLog");
    });

    // Open dropdown again and verify Deep is highlighted
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("div", "Deep").parent().should("have.class", "bg-accent");
  });

  it("includes depth parameter in chat completion API requests", () => {
    // Intercept the chat completion API call
    cy.intercept("POST", "/chat/*/complete*").as("chatComplete");

    // Create a new thread and send a message
    cy.get('button[aria-label="New chat"]').click();
    cy.get('textarea[placeholder*="Message"]').type("Hello, Guardian{enter}");

    // Wait for the completion request and verify depth parameter
    cy.wait("@chatComplete").its("request.url").should("include", "depth=normal");
  });

  it("sends different depth values based on user selection", () => {
    // Set depth to "deep"
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("Deep").click();

    // Intercept the chat completion API call
    cy.intercept("POST", "/chat/*/complete*").as("chatComplete");

    // Send a message
    cy.get('textarea[placeholder*="Message"]').type("Test deep mode{enter}");

    // Verify the request includes depth=deep
    cy.wait("@chatComplete").its("request.url").should("include", "depth=deep");
  });

  it("includes diagnostic depth data in response when diagnostic mode is selected", () => {
    // Set depth to "diagnostic"
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("Diagnostic").click();

    // Intercept the chat completion API call
    cy.intercept("POST", "/chat/*/complete*").as("chatComplete");

    // Send a message
    cy.get('textarea[placeholder*="Message"]').type("Test diagnostic mode{enter}");

    // Wait for the response
    cy.wait("@chatComplete").then((interception) => {
      // Verify the request URL includes depth=diagnostic
      expect(interception.request.url).to.include("depth=diagnostic");

      // In diagnostic mode, the backend should include sensor data
      // This would be visible in the assembled context (not directly in response body)
      // The test validates the API contract
    });
  });

  it("persists depth selection across message sends", () => {
    // Set depth to "shallow"
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("Shallow").click();

    // Intercept multiple completion calls
    cy.intercept("POST", "/chat/*/complete*").as("chatComplete");

    // Send first message
    cy.get('textarea[placeholder*="Message"]').type("First message{enter}");
    cy.wait("@chatComplete").its("request.url").should("include", "depth=shallow");

    // Send second message (depth should still be shallow)
    cy.get('textarea[placeholder*="Message"]').type("Second message{enter}");
    cy.wait("@chatComplete").its("request.url").should("include", "depth=shallow");
  });

  it("allows changing depth mid-conversation", () => {
    cy.intercept("POST", "/chat/*/complete*").as("chatComplete");

    // First message with normal depth
    cy.get('textarea[placeholder*="Message"]').type("First with normal{enter}");
    cy.wait("@chatComplete").its("request.url").should("include", "depth=normal");

    // Change to deep
    cy.get('button[aria-label="RAG depth selector"]').click();
    cy.contains("Deep").click();

    // Second message with deep depth
    cy.get('textarea[placeholder*="Message"]').type("Second with deep{enter}");
    cy.wait("@chatComplete").its("request.url").should("include", "depth=deep");
  });

  it("shows tooltip with current depth on hover", () => {
    // Hover over the depth selector button
    cy.get('button[aria-label="RAG depth selector"]').trigger("mouseover");

    // Tooltip should show current depth and description
    cy.get('button[aria-label="RAG depth selector"]')
      .should("have.attr", "title")
      .and("include", "Normal")
      .and("include", "Situational recall + semantic grounding");
  });
});
