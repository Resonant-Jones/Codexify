describe("Chat infinite scroll", () => {
  beforeEach(() => {
    const apiKey = Cypress.env("GUARDIAN_API_KEY") || "001a8ae3c2e7fe3a89c466803beb3449df5989e97f6e170be43856a38e3e9e8e";

    cy.request({
      method: "POST",
      url: "http://localhost:8000/api/chat/threads",
      headers: { "X-API-Key": apiKey },
      body: { title: "Cypress Test" },
    }).then((response) => {
      expect(response.status).to.eq(200);
      const threadId = response.body?.thread?.id;
      expect(threadId, "thread id").to.exist;

      cy.wrap(threadId).as("threadId");

      Cypress._.times(60, (i) => {
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
