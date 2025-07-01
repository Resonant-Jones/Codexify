# Security Best Practices

## Plugin Review Policy
- All contributed plugins must undergo code review before inclusion.
- Review focuses on dependency safety and adherence to `PluginBase`.

## Secrets Management
- Load sensitive configuration from a local `.env` file.
- Never commit secrets to the repository.

## Continuous Auditing
- The CI workflow runs `pip-audit` to check for vulnerable dependencies.
