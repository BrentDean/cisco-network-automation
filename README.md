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

## Current foundation

The repository currently includes:

- normalized Python models for interfaces, routes, and device snapshots;
- read-only RESTCONF and NETCONF clients for Cisco IOS XE;
- YAML-based expected-state policies;
- deterministic validation with explicit PASS/FAIL results;
- semantic pre/post state comparison;
- JSON evidence/report generation;
- a CLI for offline validation and diffing;
- cross-protocol hostname validation between RESTCONF and NETCONF;
- pytest coverage and GitHub Actions CI;
- environment-based credential handling.

No credentials are stored in the repository.

## Cisco DevNet target

The first live target is the **IOS XE on Catalyst 8000V Always-On** sandbox.

Default endpoint:

```text
Host: devnetsandboxiosxec8k.cisco.com
RESTCONF: 443
NETCONF: 830
SSH: 22
```

The sandbox generates unique credentials when a user launches a session. Put those credentials in local environment variables only.

```bash
export CISCO_HOST=devnetsandboxiosxec8k.cisco.com
export CISCO_USERNAME='...'
export CISCO_PASSWORD='...'
export CISCO_RESTCONF_PORT=443
export CISCO_VERIFY_TLS=true
```

The Catalyst 8000V sandbox may present a self-signed HTTPS certificate. Keep TLS verification enabled by default. For this disposable DevNet sandbox only, explicitly disable certificate verification for the session if the local trust store rejects the sandbox certificate:

```bash
export CISCO_VERIFY_TLS=false
```

Do not make disabled certificate verification the project default or reuse that setting for production devices.

Then install the project:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

The first live check is intentionally read-only:

```bash
cisco-validate restconf-hello
```

It retrieves the hostname and IOS XE version through RESTCONF.

A generic read-only GET is also available:

```bash
cisco-validate restconf-get \
  --path Cisco-IOS-XE-interfaces-oper:interfaces
```

Capture a normalized live baseline containing hostname, IOS XE version,
operational interface state, and routing state:

```bash
mkdir -p reports/live

cisco-validate restconf-snapshot \
  --output reports/live/baseline.json
```

The collector converts IOS XE operational fields into the project's stable
snapshot model, including:

- `admin-status` → `admin_up`;
- `oper-status` → `oper_up`;
- IPv4 address + subnet mask → CIDR notation;
- empty or `0.0.0.0` addressing → no configured IPv4 address;
- IETF RIB entries → prefix, next hop, and normalized source protocol;
- receive/direct routes without a usable gateway → `next_hop: null`.

The live routing collector uses:

```text
ietf-routing:routing-state/routing-instance
```

## Offline validation

Run the included synthetic baseline against the expected-state policy:

```bash
cisco-validate validate \
  --snapshot tests/fixtures/baseline.json \
  --policy policies/lab_policy.yaml
```

Compare two normalized snapshots:

```bash
cisco-validate diff \
  --before tests/fixtures/baseline.json \
  --after tests/fixtures/changed.json
```

These offline paths are deliberately separate from device collection so validation logic can be tested in CI without network access.

## Design principles

- Prefer structured YANG-backed interfaces over screen-scraping CLI.
- Keep collection, normalized state, policy, validation, and reporting separate.
- Capture state before and after network changes.
- Test negative/failure conditions, not only happy paths.
- Fail closed when required configuration or credentials are missing.
- Keep shared-sandbox work read-only until a change is explicitly safe.
- Never commit credentials, private keys, tokens, or unredacted secrets.

## Roadmap

### 1. Offline validation core

- [x] normalized network snapshots
- [x] declarative validation policies
- [x] semantic pre/post diff
- [x] structured reports
- [x] unit tests and CI

### 2. Read-only IOS XE integration

- [x] environment-based credentials
- [x] generic RESTCONF GET support
- [x] hostname/version smoke test
- [x] normalize real interface state
- [x] normalize real routing state
- [x] save live interface and routing baseline snapshots

### 3. Controlled change workflow

This phase uses a private/reservable sandbox rather than the shared always-on device.

The demo write path is deliberately narrow:

- only `Loopback250` is managed;
- the address is fixed at `192.0.2.250/32`;
- the description is fixed at `portfolio-change-validation`;
- writes are disabled unless `CISCO_ALLOW_WRITES=true`;
- creation refuses to overwrite an existing Loopback250;
- deletion refuses to remove Loopback250 unless its description proves it was created by this demo;
- each create/delete operation performs a read-after-write verification.

```bash
export CISCO_ALLOW_WRITES=true

cisco-validate restconf-create-demo-loopback
cisco-validate restconf-delete-demo-loopback
```

- [x] pre-change validation
- [x] small reversible change
- [x] post-change validation
- [x] rollback
- [x] rollback verification

Observed private-sandbox workflow:

```text
baseline capture
  -> guarded RESTCONF create of Loopback250
  -> read-after-write verification
  -> semantic diff: 2 intended changes
  -> policy validation: 18/18 checks passed
  -> guarded RESTCONF delete
  -> read-after-delete verification
  -> semantic diff against original baseline: 0 changes
```

The semantic diff isolated exactly the intended interface and direct-route additions,
then verified full baseline restoration after rollback.

### 4. NETCONF and pyATS / Genie

The NETCONF client uses the IOS XE device handler in `ncclient`, port 830,
and a running-datastore subtree filter against the native IOS XE hostname.

For disposable DevNet labs where the SSH host key is not trusted locally:

```bash
export CISCO_NETCONF_HOSTKEY_VERIFY=false
```

Keep host-key verification enabled by default outside disposable lab sessions.

```bash
cisco-validate netconf-hello
cisco-validate netconf-hostname
cisco-validate netconf-interface --name GigabitEthernet1
cisco-validate cross-check-hostname
cisco-validate cross-check-interface --name GigabitEthernet1
```

- [x] NETCONF/YANG read-only connection
- [x] native hostname retrieval from running config
- [x] RESTCONF/NETCONF hostname cross-check
- [x] operational interface normalization over NETCONF
- [x] RESTCONF/NETCONF interface-state cross-check
A public-safe pyATS testbed is included at `inventory/pyats_testbed.example.yaml`.
It keeps credentials out of Git by resolving them from environment variables.

```bash
export PYATS_USERNAME=developer
read -r -s -p "pyATS device password: " PYATS_PASSWORD
echo
export PYATS_PASSWORD

pip install -e '.[pyats]'
pyats validate testbed inventory/pyats_testbed.example.yaml
```

- [x] public-safe pyATS testbed definition
- [ ] live pyATS/Unicon SSH connection
- [ ] Genie operational-state parsing
- [ ] reusable change-validation test cases

## Security

Do not commit:

- DevNet usernames or passwords
- VPN credentials
- sandbox-specific secrets
- private keys
- tokens
- unredacted device configuration containing secrets

Use environment variables and local untracked configuration instead.
