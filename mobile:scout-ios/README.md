# Scout iOS App Shell

Scout is the native iOS companion for Codexify.

This scaffold follows the concepts defined in [`../docs/architecture/ios-scout-vault-remote-contract.md`](../docs/architecture/ios-scout-vault-remote-contract.md).

Guardian is the operator.

Vault remains the long-term memory authority.

This slice creates the first native SwiftUI app shell only. It does not implement:

- networking
- auth
- local models
- image analysis
- task streaming
- artifact retrieval

Future API work should prefer canonical `/api/*` routes.
