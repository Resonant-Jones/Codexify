describe("Chat infinite scroll", () => {
  beforeEach(() => {
    const apiKey = Cypress.env("GUARDIAN_API_KEY");
    if (!apiKey) {
      throw new Error("GUARDIAN_API_KEY must be set for Cypress API requests.");
    }

    cy.request({
      method: "POST",
      url: "http://localhost:8000/api/chat/threads",
      headers: { "X-API-Key": apiKey },
      body: { title: "Cypress Test" },
    }).then((response) => {
      expect(response.status).to.eq(200);
      const threadId = response.body?.id;
      expect(threadId, "thread id").to.exist;

      cy.wrap(threadId).as("threadId");

      // Seed ~80 messages as requested
      Cypress._.times(80, (i) => {
        cy.request({
          method: "POST",
          url: `http://localhost:8000/api/chat/${threadId}/messages`,
          headers: { "X-API-Key": apiKey },
          body: { role: "user", content: `hello world ${i + 1}` },
        });
      });

      cy.visit(`http://localhost:5173/chat/${threadId}`);
    });
  });

  it("loads messages and supports infinite scroll", () => {
    // Wait for at least one message to appear in ChatView
    cy.get('[data-testid="chat-message"]', { timeout: 10000 }).should("have.length.greaterThan", 0);

    // Scroll to top to trigger older messages load
    cy.get('[data-testid="chat-container"]').scrollTo("top");

    // Loading indicator appears
    cy.get('[data-testid="chat-loading"]').should("exist");

    // Messages grow after loading
    cy.get('[data-testid="chat-message"]').then(($initial) => {
      const initialCount = $initial.length;

      cy.get('[data-testid="chat-message"]', { timeout: 5000 }).should(($final) => {
        expect($final.length).to.be.greaterThan(initialCount);
      });
    });

    // No error visible
    cy.get('[data-testid="chat-error"]').should("not.exist");
  });
});
