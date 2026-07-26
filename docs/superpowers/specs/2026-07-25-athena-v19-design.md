# Athena AX6600 DAED v19 Design Specification

Status: **Approved design, pending implementation plan**  
Date: **2026-07-25**  
Target release: **v19.0.0-rc1**  
Repository: **jdy2**  
Device: **JDCloud RE-CS-02 / Athena AX6600**  
Target: **qualcommax/ipq60xx**

## 1. Purpose

v19 upgrades the existing v18 firmware-build project into a stable, auditable, and recoverable DAED appliance for the JDCloud Athena AX6600.

The release prioritizes, in order:

1. Network stability.
2. Low latency.
3. Maximum usable throughput.
4. Accurate, pollution-resistant DNS.
5. Gaming experience.
6. General proxy experience.
7. CPU efficiency and temperature.
8. NSS acceleration where compatible with DAED correctness.

The public repository must not contain private node credentials, subscription URLs, UUIDs, REALITY keys, short IDs, Wi-Fi passwords, personal MAC addresses, or private addressing beyond documented examples.

## 2. Existing v18 Baseline

The current project already provides:

- A GitHub Actions build based on LiBwrt commit `cf9444c1b20458687898489b36e1aebf56d9baf2`.
- Target `qualcommax/ipq60xx`, device `jdcloud_re-cs-02`.
- One build that outputs both initramfs and squashfs sysupgrade images.
- A 6 MiB persistent kernel slot guard.
- DAED, `luci-app-daede`, detached BTF, Athena display support, Wake-on-LAN, and Chinese LuCI.
- A RAM-boot emergency network.
- DAED and display disabled by default.
- Basic project, shell, configuration, and artifact checks.

v19 must retain these proven safeguards unless explicitly replaced by a stricter equivalent.

## 3. Release Model

v19 is an in-place evolution of the existing `jdy2` repository rather than a parallel project or a nested `v19/` tree.

The first public build is `v19.0.0-rc1`. A stable `v19.0.0` release is created only after successful initramfs and persistent-image testing on the real device.

The uploaded source archive contains build source only. Firmware binaries are produced by GitHub Actions.

## 4. Safe First-Boot Mode

The firmware boots in a safe, directly reachable state before DAED is configured.

Default first-boot behavior:

- LAN address: `192.168.50.1/24`.
- WAN: DHCP client, suitable for an upstream modem/router.
- DAED service: disabled and stopped.
- DAED UI listener: loopback only after initialization, never `0.0.0.0:2023` as the public default.
- Default LuCI theme: Argon, dark mode.
- Bootstrap theme: retained as a recovery fallback.
- Software flow offload: disabled.
- Hardware flow offload: disabled.
- ECM IPv4/IPv6 frontends: stopped conservatively when debugfs nodes are available.
- NSS firmware, NSS data path, Wi-Fi offload, ath11k, and QCN9074 support: retained.
- Athena display service: disabled by default.

The base system must provide LAN, WAN, DHCP, ordinary DNS, SSH, LuCI, and recovery access even with no node or DAED policy installed.

The RAM test image and persistent image use the same LAN address to avoid confusion and to avoid conflict with common upstream gateways at `192.168.1.1`.

## 5. Web and Theme Architecture

### 5.1 Normal management path

Nginx is the primary web entry point:

- `/cgi-bin/luci/` serves LuCI with Argon.
- `/athena-daed/` reverse-proxies DAED at `127.0.0.1:2023`.
- `/athena-recovery/` exposes diagnostics and recovery controls.

The DAED panel is available in LuCI under:

`Services -> DAED Panel`

The LuCI shell remains visible. The right-side content area embeds the complete native DAED frontend. DAED's own status, subscription, node group, DNS, routing, settings, and log navigation remain unchanged.

The implementation must not inject custom CSS or JavaScript into DAED's own frontend because that would create avoidable version coupling.

### 5.2 Reverse-proxy requirements

The Nginx proxy must support:

- Correct path forwarding.
- WebSocket upgrade headers.
- Streaming and long-lived requests used by logs and status updates.
- Reasonable connect, read, and send timeouts.
- Failure pages that show DAED status and recovery actions instead of a blank iframe.

DAED must listen on `127.0.0.1:2023` in the supported configuration. Port 2023 must not be exposed to WAN or ordinary LAN clients.

### 5.3 Recovery path

A recovery uhttpd/LuCI service remains available on:

`http://192.168.50.1:8080/`

Recovery characteristics:

- LAN-only firewall access.
- Bootstrap theme.
- Access to LuCI, service state, logs, backups, rollback, and network recovery.
- Not used as the normal management interface.

### 5.4 Theme behavior

v19 includes:

- `luci-theme-argon`.
- Argon configuration support.
- Dark mode as the default.
- User-selectable light/dark/auto mode, accent, background, blur, and opacity.
- Bootstrap retained as a fallback.

The public project does not include the user's personal background image.

## 6. Runtime Components

### 6.1 `athena-runtime` package

A dedicated package owns system-side policy and command-line tools. It contains:

- `/etc/config/athena`
- `/etc/init.d/athena-runtime`
- `/usr/bin/athena-setup`
- `/usr/bin/athena-health`
- `/usr/bin/athena-backup`
- `/usr/bin/athena-rollback`
- `/usr/bin/athena-runtime`
- `/usr/bin/athena-iot`
- `/usr/bin/athena-info`
- `/usr/bin/athena-feature-check`
- `/usr/share/athena/templates/`
- `/usr/share/athena/rules/`

Complex runtime behavior must not be generated inline from one large build-time shell script. `scripts/inject_runtime.sh` remains limited to safe boot defaults, RAM diagnostics, and first-boot initialization.

### 6.2 `luci-app-athena` package

A lightweight LuCI application provides:

- Overall status.
- DAED panel embedding.
- Generated template viewing/copying.
- Backup listing.
- Health-check results.
- Runtime policy status.
- Recovery actions.

It must call the same command-line backend as SSH workflows rather than duplicating system logic in JavaScript.

## 7. `athena-setup` Workflow

`athena-setup` is the primary initialization command. It is interactive by default and also exposes non-destructive checking and resume modes.

Supported commands:

- `athena-setup`
- `athena-setup --check`
- `athena-setup --resume`

### 7.1 Read-only preflight

The preflight validates:

- Device model and target.
- Kernel and platform compatibility.
- DAED and `luci-app-daede` installation.
- Integrated or detached BTF availability.
- Argon, Nginx, uhttpd, rpcd, and LuCI status.
- LAN/WAN subnet conflict.
- Available disk and memory.
- ECM debugfs availability.
- System time validity.
- Existing backup capacity.

`--check` must not change UCI, services, files, or firewall state.

### 7.2 Automatic backup

Before applying changes, `athena-setup` creates a dated backup under:

`/root/athena-backups/YYYYMMDD-HHMMSS/`

Each backup includes:

- Manifest.
- SHA256 checksums.
- `/etc/config` archive.
- `/etc/daed` and `wing.db` archive.
- Nginx and uhttpd configuration archive.
- Runtime files and UCI state.
- System report and pre-change service state.

The default retention is three backups. Cleanup occurs only after a new backup completes and verifies successfully.

### 7.3 Profiles

v19 exposes three profiles:

- `stable`: default public profile.
- `performance`: more aggressive but still supported.
- `custom`: template variables selected by the user.

The approved default is `stable`.

### 7.4 DAED database policy

`athena-setup` does not write directly to `/etc/daed/wing.db` and does not depend on internal SQLite schema details.

It generates importable files and guides the user through importing them in the native DAED panel.

Generated files:

- `/etc/athena/generated/global.dae`
- `/etc/athena/generated/dns.dae`
- `/etc/athena/generated/routing.dae`
- `/etc/athena/generated/IMPORT.md`

The setup tool pauses after generation. The user imports the files, selects a proxy group, starts DAED, and returns to the terminal for validation.

### 7.5 Idempotence and resume

State is stored in:

- `/etc/config/athena`
- `/var/lib/athena/setup-state`

Repeated or resumed runs must not:

- Duplicate firewall rules.
- Duplicate startup entries.
- Overwrite a verified backup.
- Delete subscriptions or nodes.
- Recreate identical generated files unnecessarily.

Logs are written to `/var/log/athena-setup.log` with credential redaction.

## 8. DAED Configuration Templates

Templates are stored under:

`packages/athena-runtime/files/usr/share/athena/templates/`

Required templates:

- `global.dae.tpl`
- `dns.dae.tpl`
- `routing.dae.tpl`

Supported public substitutions include:

- `{{PROXY_GROUP}}`
- `{{CHINA_DNS_PRIMARY}}`
- `{{CHINA_DNS_SECONDARY}}`
- `{{GLOBAL_DOH}}`
- `{{NODE_HOSTNAME}}`
- `{{NODE_IPS}}`
- `{{GAME_DEVICE_MACS}}`
- `{{BT_DSCP}}`
- `{{QUIC_POLICY}}`

Private node authentication fields are not template inputs and are never collected.

## 9. Global DAED Policy

The stable profile uses these design values:

- LAN interface: `br-lan`.
- WAN interface: `auto`.
- Automatic kernel parameter setup: enabled.
- Dial mode: `domain`.
- Sniffing timeout: 30 ms.
- Insecure TLS: disabled.
- Log level: warning.
- Transparent huge pages: disabled.
- MPTCP: disabled.
- Bootstrap resolver: selected domestic UDP DNS.
- Fallback resolver: secondary domestic UDP DNS.
- Health-check interval: 60 seconds.
- Health-check tolerance: 100 ms.

v19 does not reduce DAED's BPF connection-state map by default because BT/P2P use is in scope and the device has sufficient memory.

## 10. DNS Architecture

SmartDNS is not included in v19.

The DNS design has three independent resolution paths:

1. Chinese domains use low-latency domestic UDP DNS over direct routing.
2. Non-Chinese domains use a configured DoH endpoint through the selected proxy group.
3. Node and subscription domains use a domestic bootstrap resolver over forced direct routing.

Default domestic resolvers are configurable, with examples such as `223.5.5.5` and `119.29.29.29`.

The DNS template enables optimistic caching with a conservative stale period and bounded cache size.

The request rules must route DAED's node and subscription selectors to the direct domestic upstream before the general fallback.

HTTPS/ECH DNS records are not rejected by default. An explicit `disable_ech` option may add a rejection rule only when required for a diagnosed compatibility problem.

The generated routing policy must force bootstrap DNS addresses and configured node endpoints to `must_direct` to prevent recursive dependency on the proxy itself.

## 11. Traffic Routing Policy

Rules are generated in strict top-to-bottom order:

1. Private, link-local, broadcast, and multicast traffic.
2. Bootstrap DNS, node hostnames, and node IPs.
3. Explicit login/store domains that require the proxy.
4. Explicit download/CDN domains that should be direct.
5. Device-scoped real-time gaming traffic.
6. Minecraft defaults.
7. BT/P2P DSCP rule.
8. Chinese IP and domain rules.
9. Default proxy fallback.

A global `all UDP -> direct` rule is prohibited.

A global `all IPv6 -> direct` rule is prohibited.

### 11.1 Base behavior

- Chinese IPv4: direct.
- Chinese IPv6: direct.
- Non-Chinese IPv4: proxy by default.
- Non-Chinese IPv6: proxy by default.
- Private and local traffic: forced direct.

### 11.2 Steam

Versioned domain-list files distinguish:

- Store, account, login, help, and community traffic: proxy.
- Game downloads, content CDN, updates, and static content: direct.

Domain lists remain separate from the main generator so they can be updated independently.

### 11.3 Xbox

- Account, store, regional, entitlement, and subscription web traffic: proxy.
- Game downloads and update CDN: direct where classified.
- Real-time UDP for a configured Xbox/game device MAC: direct.

TCP traffic from the same device continues to follow domain and IP rules rather than bypassing the proxy wholesale.

### 11.4 Minecraft and other games

Default direct rules include common Minecraft Java and Bedrock ports.

Other game UDP is direct only for user-specified game-device MAC addresses. This avoids leaking unrelated QUIC, foreign UDP, or IPv6 traffic.

### 11.5 BT/P2P

The default mode uses DSCP value 4 to mark BT traffic for direct routing.

Supported modes:

- `off`
- `dscp` (default)
- `device`

The project documentation explains how to configure qBittorrent's outbound Type of Service value.

### 11.6 QUIC

Supported modes:

- `proxy` (default)
- `block` to force TCP fallback when the node's UDP path is unreliable

A public default that sends foreign UDP/443 directly is not allowed.

## 12. ECM, NSS, Flow Offload, CPU, and IRQ Policy

### 12.1 Retained acceleration

v19 retains:

- NSS firmware.
- NSS data path.
- NSS Wi-Fi offload.
- ath11k and QCN9074 support.
- Existing NSS memory profile.
- Existing hardware IRQ distribution.

### 12.2 Disabled connection bypass paths

v19 disables:

- OpenWrt software flow offload.
- OpenWrt hardware flow offload.
- ECM IPv4 frontend processing.
- ECM IPv6 frontend processing.

`athena-runtime` waits for the debugfs controls to appear before writing stop flags.

The implementation must not unload NSS/ECM kernel modules, write `defunct_all`, remove NSS firmware, or repeatedly reload networking modules.

### 12.3 CPU policy

Stable defaults:

- Governor: `performance`.
- DAED nice value: `-5`.
- DAED CPU affinity: `auto`.
- Existing IRQ assignment retained.
- RPS/XPS not enabled globally.

Manual affinity such as `1-3` is supported through UCI but is not the public default.

## 13. IoT 2.4 GHz Compatibility Network

v19 provides an optional, dedicated IoT SSID without weakening the primary Wi-Fi networks.

The IoT network is disabled and unconfigured on first boot. It is created only by an explicit interactive command:

`athena-iot setup`

The command requires the user to enter an SSID and passphrase locally. The passphrase is never written to setup logs, diagnostics, generated public templates, build metadata, or artifacts.

Stable compatibility defaults are:

- 2.4 GHz radio only, selected by runtime band detection rather than a fixed `radioN` name.
- Country code `CN`.
- 20 MHz channel width.
- Explicit channel `1`, `6`, or `11`; automatic channel selection is not the stable default.
- WPA2-PSK with AES/CCMP only.
- Protected management frames disabled for the IoT SSID.
- 802.11r fast transition, 802.11k neighbor reporting, and 802.11v BSS transition disabled.
- Wi-Fi 6/802.11ax disabled for the IoT SSID by default, with an explicit opt-in switch for compatibility testing.
- WMM enabled.
- SSID broadcast enabled.
- Client isolation disabled so LAN discovery protocols continue to work.
- The IoT interface joins the existing LAN bridge; v19 does not introduce a default IoT VLAN, multicast relay, or additional firewall zone.

Supported commands:

- `athena-iot setup`
- `athena-iot status`
- `athena-iot diagnose`
- `athena-iot disable`
- `athena-iot remove`

All state changes are idempotent, use UCI, create a verified Athena backup before changing wireless configuration, and reload Wi-Fi only after validation. Removal affects only the Athena-managed IoT section and never rewrites unrelated user SSIDs.

Diagnostics report the selected radio, band, channel, width, encryption mode, PMF, legacy/HE mode, association events, DHCP observations, and recent hostapd/netifd error counts. Output redacts SSIDs, passphrases, station MAC addresses, and client identifiers by default.

Because the original repository does not inject authentication, PMF, roaming, or 802.11ax settings, host-side inspection cannot prove which runtime setting caused an existing device to fail. The RC acceptance checklist therefore requires real-device association, DHCP, DNS, LAN discovery, Internet access, reconnect-after-reboot, and coexistence testing with at least one affected IoT device.

## 14. Health Check

`athena-health` supports:

- Default human-readable output.
- `--verbose`.
- `--json`.

Checks include:

- DAED service and process.
- DAED local API and reverse proxy.
- LAN DHCP and DNS.
- Domestic and foreign DNS resolution.
- Bootstrap resolution without proxy recursion.
- Recent bootstrap, SERVFAIL, timeout, and EOF error counts.
- IPv4 and IPv6 default routes.
- Chinese and foreign IPv6 handling.
- ECM stop flags.
- ECM accelerated-connection trend.
- Flow-offload state.
- CPU governor and optional affinity.
- Nginx, Argon, LuCI, and recovery uhttpd.
- Temperature and memory warnings.

Results are classified as `PASS`, `WARN`, or `FAIL`.

Health checks must not treat an unsupported BusyBox `nc -z` invocation as proof that a port is closed. Tests must preserve command errors and account for implementation differences.

## 15. Rollback and Failure Handling

Automatic rollback is offered when setup introduces a critical failure, including:

- No LAN DNS.
- Missing default route.
- DAED startup failure.
- Invalid generated configuration.
- Nginx configuration failure.
- Persistent bootstrap resolver loop.
- Critical health-check failure.

Rollback restores:

- UCI configuration.
- DAED database and files.
- Nginx/uhttpd configuration.
- Runtime files.
- Previous service enable/disable state.

Supported commands:

- `athena-rollback`
- `athena-rollback <backup-id>`
- `athena-rollback --component daed`

Rollback must not delete a backup until its restoration and post-restore checks complete.

## 16. Build-System Changes

### 16.1 Project structure

The implementation introduces:

- `.github/workflows/build-athena-v19.yml`
- `config/athena-v19.config`
- `packages/athena-runtime/`
- `packages/luci-app-athena/`
- `SOURCES.lock.json`
- Expanded verification scripts.
- Expanded documentation.

### 16.2 Pinned source policy

Every third-party source used by the build must resolve to a full commit hash in `SOURCES.lock.json`.

Moving branches such as `main`, `master`, and `26.x` must not be used directly by the actual build checkout.

Sources to lock include:

- LiBwrt.
- openwrt-daede.
- vmlinux-btf.
- Athena display package.
- Argon theme.
- Argon configuration package.
- Go packaging source when overridden.

The build fails if a lock entry is missing, cannot be fetched, or resolves to a different commit.

### 16.3 Workflow inputs

The v19 workflow remains manually triggered and exposes:

- `compile_jobs`: 1 or 2.
- `build_profile`: `stable` or `performance`.
- `release_stage`: `test` or `candidate`.

The workflow never pushes changes and does not automatically create a GitHub Release.

## 17. CI Verification

Pre-build checks include:

- Shell syntax.
- Python syntax.
- Workflow YAML parsing.
- Required-file and package-layout validation.
- Lock-file validation.
- Template rendering tests.
- Static DAED configuration checks.
- Nginx and LuCI menu checks.
- Permissions and line-ending checks.
- Merge-marker checks.
- Sensitive-information scanning.

The security scanner rejects likely:

- Proxy URLs with credentials.
- UUIDs outside approved examples.
- REALITY keys and short IDs.
- Subscription tokens and private keys.
- Wi-Fi passwords.
- Private node hostnames.
- Personal MAC addresses.
- User-specific public IPv6 addresses.

Approved placeholders and documentation examples remain allowed.

### 17.1 Effective configuration requirements

The final `.config` must include:

- Target and device selections.
- Initramfs and squashfs outputs.
- NSS firmware and correct QCN9074 firmware variant.
- DAED, DAED LuCI app, detached BTF.
- Argon and Argon configuration.
- Nginx and required LuCI integration.
- `athena-runtime` and `luci-app-athena`.
- Wake-on-LAN and Athena display.

It must exclude unrelated proxy managers and SmartDNS.

### 17.2 Image and package checks

The build fails unless both images are present:

- Initramfs `uImage.itb`.
- Squashfs sysupgrade image.

The persistent `uImage.itb` must remain at or below 6,291,456 bytes.

Kernel margin policy:

- At least 128 KiB remaining: pass.
- Below 128 KiB remaining: warning.
- Over limit: fail.

The produced package manifest and extracted rootfs must contain all required v19 packages and runtime files.

## 18. Artifact Layout

The GitHub Actions artifact is named:

`Athena-AX6600-v19-<run-number>`

It contains:

- `firmware/`
- `metadata/`
- `diagnostics/`
- `tools/`
- `docs/`
- Top-level checksum list.

Firmware files are renamed consistently to reduce user error.

Metadata includes exact source commits, effective configuration, project metadata, package manifest, and build information.

Diagnostics include build logs, useful error context, kernel size, template tests, and security scan results.

## 19. Flash and Validation Policy

### 19.1 Initramfs first

The user must first boot the full initramfs image through U-Boot and verify:

- `192.168.50.1` access.
- WAN DHCP.
- DHCP and DNS.
- Argon.
- Recovery port 8080.
- DAED disabled by default.
- DAED panel availability.
- NSS and Wi-Fi operation.
- Feature checks.

### 19.2 Persistent flash

Moving from v18 to v19 requires a clean sysupgrade without keeping settings because LAN, Web, DAED listener, and runtime configuration all change.

### 19.3 Initialization and acceptance

After importing nodes, the user runs `athena-setup`, imports generated templates, then runs `athena-health --verbose`.

A stable release requires successful checks for:

- Base networking.
- Domestic and foreign DNS.
- Bootstrap DNS.
- DAED proxying.
- IPv4 and IPv6.
- ECM and flow-offload policy.
- Argon and DAED embedding.
- Recovery UI.
- Reboot persistence.
- Backup and rollback.
- Optional IoT SSID association, DHCP, DNS, discovery, and reboot persistence when enabled.

## 20. Documentation Deliverables

v19 documentation includes:

- `README.md`
- `CHANGELOG.md`
- `docs/BUILD.md`
- `docs/FLASH.md`
- `docs/SETUP.md`
- `docs/DAED_CONFIG.md`
- `docs/GAMING.md`
- `docs/IOT_WIFI.md`
- `docs/RECOVERY.md`
- `docs/ARCHITECTURE.md`
- `THIRD_PARTY_NOTICES.md`
- `CHANGE_SUMMARY.md`

The documentation must clearly separate:

- Build-time guarantees.
- Static checks.
- Initramfs test requirements.
- Real-device observations.
- Unsupported assumptions.

## 21. Non-Goals for v19

v19 does not:

- Bundle SmartDNS.
- Directly edit DAED's SQLite database.
- Bundle private nodes or subscriptions.
- Rebuild DAED's native frontend as LuCI pages.
- Inject a custom theme into the DAED frontend.
- Enable all UDP direct routing.
- Enable all IPv6 direct routing.
- Automatically publish GitHub releases.
- Blindly rewrite IRQ, RPS, or XPS settings.
- Promise that GitHub Actions success alone proves the firmware is safe to flash persistently.
- Enable an IoT SSID, ship a default IoT passphrase, or isolate IoT clients in a new VLAN automatically.

## 22. Success Criteria

The implementation is complete when:

1. The repository passes all local static checks.
2. GitHub Actions builds both required images from pinned commits.
3. The artifact contains the required firmware, metadata, diagnostics, tools, and documentation.
4. Initramfs boots with safe direct networking at `192.168.50.1`.
5. Normal and recovery Web interfaces are reachable.
6. DAED remains disabled until user initialization.
7. Generated DAED templates do not create a bootstrap DNS dependency loop.
8. Domestic traffic is direct and non-Chinese traffic is proxied by default for both IPv4 and IPv6.
9. Steam download, selected game-device UDP, Minecraft, and DSCP-marked BT traffic follow the approved exceptions.
10. NSS and Wi-Fi acceleration remain functional while ECM frontends and flow offload remain stopped.
11. Backup, health checking, and rollback work after reboot.
12. No user secret or private node information appears in the public repository or build artifact.
13. The optional IoT SSID is disabled by default, can be created and removed without changing unrelated SSIDs, and uses the approved 2.4 GHz compatibility defaults.
14. At least one previously affected IoT device passes the documented real-device association and reconnect checklist before stable release.

## 23. Implementation Boundary

This document defines the approved design only. Implementation must begin with a separate, detailed execution plan. No design requirement may be silently removed or changed during implementation; any material change requires explicit user approval and an update to this specification.
