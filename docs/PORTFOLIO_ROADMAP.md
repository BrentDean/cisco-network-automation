# Cisco Portfolio Roadmap

## Goal

Turn this repository into a concise technical portfolio that lets a recruiter or network-engineering hiring manager verify three things quickly:

1. I understand Cisco IOS XE and core network state.
2. I can automate Cisco workflows safely with Python and Cisco tooling.
3. I use software-engineering practices that make network changes testable, reviewable, and reversible.

The repository should favor **evidence over claims**. New features should produce reproducible commands, tests, structured output, and live-lab proof where practical.

## Current demonstrated capability

The current implementation already demonstrates:

- IOS XE state collection from live Cisco DevNet Catalyst 8000V devices;
- RESTCONF/YANG and NETCONF/YANG workflows;
- pyATS, Genie, Unicon, and AEtest;
- interface and route normalization;
- declarative policy validation;
- negative tests that intentionally produce validation failures;
- semantic pre/post change diffing;
- guarded RESTCONF configuration changes;
- read-after-write verification;
- rollback verification against the original baseline;
- cross-protocol state consistency checks;
- Python packaging, CLI design, pytest, Ruff, and GitHub Actions.

These capabilities should remain the foundation. The next work should expand breadth without turning the repository into an unfocused collection of demos.

## Next implementation milestones

### 1. Multi-device inventory and fleet validation

**Purpose:** Show that the automation model scales beyond one router.

Planned evidence:

- inventory containing multiple IOS XE targets;
- sequential and bounded-concurrency collection;
- per-device PASS/FAIL results;
- aggregate summary with failed checks and unreachable devices;
- failure isolation so one device does not invalidate the entire run;
- tests for partial failure and timeout behavior.

Recruiter signal: network automation, fleet operations, fault isolation, Python concurrency.

### 2. Configuration backup and compliance

**Purpose:** Demonstrate practical network operations beyond operational-state polling.

Planned evidence:

- retrieve running configuration through an appropriate Cisco-supported management path;
- redact or reject credential-bearing configuration before evidence is persisted;
- hash/version saved configuration artifacts;
- compare current configuration against approved policy;
- detect unauthorized or unexpected drift;
- generate a human-readable compliance report.

Recruiter signal: configuration management, security hygiene, drift detection, auditability.

### 3. Broader Cisco network-state validation

**Purpose:** Make the repository visibly reflect networking knowledge, not only API knowledge.

Candidate validations:

- interface addressing and administrative/operational state;
- default route and selected route expectations;
- VLAN and switched-interface state when a suitable IOS XE lab target is available;
- OSPF neighbor/state validation when a multi-router lab is available;
- BGP neighbor and route validation when a suitable lab topology is available;
- ACL presence and intent checks without exposing sensitive production configurations.

Each feature should be added only when it can be tested or demonstrated against an appropriate lab.

Recruiter signal: routing, switching, reachability, network troubleshooting, policy validation.

### 4. Change-plan workflow

**Purpose:** Make the change-control story closer to an operational engineering workflow.

Target flow:

```text
inventory
  -> pre-change collection
  -> policy gate
  -> proposed change
  -> explicit approval/write enablement
  -> apply
  -> read-after-write
  -> post-change validation
  -> semantic diff
  -> PASS or automatic/manual rollback path
  -> evidence bundle
```

Planned evidence:

- dry-run/change-plan output;
- intended-change assertions;
- failure when unrelated state changes;
- rollback decision evidence;
- machine-readable and concise human-readable reports.

Recruiter signal: production-minded change safety and operational discipline.

### 5. Cisco automation ecosystem breadth

Add integrations only where they strengthen the story.

Good candidates:

- Ansible network modules for declarative IOS XE configuration/verification;
- Nornir for multi-device task orchestration;
- additional pyATS/Genie parsers and AEtest suites;
- YANG model discovery/capability reporting.

The Python implementation should remain the core so the repository demonstrates programming ability rather than only tool invocation.

## Portfolio evidence standard

A feature is considered portfolio-ready when it includes most of the following:

- a clear README command;
- code that can be reviewed independently of the live lab;
- unit tests or deterministic fixtures;
- explicit failure behavior;
- safe credential handling;
- sample/redacted output;
- live-lab verification notes where appropriate;
- a focused Git commit and pull request describing the engineering decision.

## What this project should not claim

This project is a controlled lab portfolio. It should not imply:

- production ownership of an enterprise Cisco fleet;
- CCNA/CCNP certification;
- large-scale Cisco deployment experience that was not actually performed;
- production change authority;
- expertise with a Cisco product or protocol that has only been read about.

The strongest presentation is precise: demonstrate what was actually built, tested, failed intentionally, and recovered.

## Target role alignment

The repository is particularly relevant to roles such as:

- Network Automation Engineer;
- Network Security Automation Engineer;
- Infrastructure Automation Engineer;
- Junior / Associate Network Engineer with Python responsibilities;
- DevNet / network programmability roles;
- SRE or platform roles that interact with network infrastructure.

The distinguishing theme should be: **Cisco networking plus software-engineering discipline**.
