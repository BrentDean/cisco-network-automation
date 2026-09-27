# Cisco Network Automation & Change Validation

A portfolio project for automating and validating Cisco IOS XE network changes with Python.

The project is designed around a production-oriented workflow:

```text
desired state / change request
          |
          v
 Python automation layer
    |             |
    |             +--> validation / policy checks
    v
Cisco IOS XE device
    |
    +--> structured pre-change snapshot
    +--> controlled change
    +--> structured post-change snapshot
    +--> semantic diff
    +--> PASS / FAIL evidence
```

## Goals

- Use structured interfaces instead of screen-scraping CLI where practical.
- Capture network state before and after a change.
- Express expected state as data and validate it deterministically.
- Detect configuration or operational drift.
- Generate machine-readable evidence for each validation run.
- Exercise failure paths and rollback behavior, not only successful changes.
- Keep credentials and Cisco DevNet sandbox details out of version control.
- Test the offline validation logic in CI without requiring a live Cisco device.

## Planned Cisco integrations

The live integration layer will be exercised against Cisco DevNet IOS XE sandboxes using technologies such as:

- RESTCONF
- NETCONF
- YANG data models
- pyATS / Genie
- Cisco IOS XE

Live-device features will be added only after they are verified against an available DevNet environment.

## Initial milestones

1. **Offline validation core**
   - typed network snapshots
   - declarative validation policies
   - semantic pre/post diff
   - structured reports
   - unit tests and CI

2. **Read-only IOS XE integration**
   - environment-based credentials
   - connectivity checks
   - interface and route collection
   - baseline capture

3. **Controlled change workflow**
   - pre-change validation
   - small reversible change
   - post-change validation
   - rollback and rollback verification

4. **pyATS / Genie validation**
   - operational-state learning
   - pre/post comparison
   - reusable network test cases

## Security

Do not commit:

- DevNet usernames or passwords
- VPN credentials
- sandbox-specific secrets
- private keys
- tokens
- unredacted device configuration containing secrets

Use environment variables and local untracked configuration instead.

## Status

Foundation in progress. The first implementation focuses on testable offline network-state validation so the repository remains useful even when a DevNet sandbox is not reserved.
