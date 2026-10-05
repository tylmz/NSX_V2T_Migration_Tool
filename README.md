# NSX Migration for VMware Cloud Director – v1.5 (community build)

A patched build of the **NSX Migration for VMware Cloud Director** tool, used to migrate NSX Data Center for vSphere (NSX-V) backed organization VDCs to NSX-T Data Center backed organization VDCs within the same VMware Cloud Director instance.

> **Community build.** v1.5 is based on the upstream tag [`MT_v1.4.2.2.H001`](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/releases/tag/MT_v1.4.2.2.H001) of [Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool), with a small set of bug fixes and a Windows build. It is **not** an official VMware, Broadcom or Calsoft release and comes with no support or warranty. The tool changes production Cloud Director, NSX and vCenter objects: always test on a non-production organization VDC first, including a full rollback.

---

## Contents

- [What's different from 1.4.2.2.H001](#whats-different-from-14222h001)
- [Supported environments](#supported-environments)
- [Download and install](#download-and-install)
- [Preparing your environment](#preparing-your-environment)
- [Configuration (userInput.yml)](#configuration-userinputyml)
- [Running the tool](#running-the-tool)
- [Recommended migration runbook](#recommended-migration-runbook)
- [Logs and troubleshooting](#logs-and-troubleshooting)
- [Known limitations](#known-limitations)
- [Building from source](#building-from-source)
- [Security notes](#security-notes)
- [License and attribution](#license-and-attribution)

---

## What's different from 1.4.2.2.H001

Every code change is marked with a `PATCH-n` comment. Full details are in [PATCHES.md](PATCHES.md).

| Patch | Fixes |
|---|---|
| **PATCH-1** | Crash during topology, rollback or cleanup when an external network subnet has an empty static IP pool (VCD returns `null`). |
| **PATCH-1b** | Target IP pool update no longer adds an IP that is already in the target pool, so a target subnet can be pre-seeded with the edge gateway's own IP. |
| **PATCH-2** | Crash in the static route check, and missed load balancer VIPs, when an edge gateway uplink carries more than one subnet. |
| **PATCH-4** | `list index out of range` instead of a readable error when a required `-v2t` network is missing (upstream issues [#4](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/4) and [#7](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/7)). |
| **PATCH-5** | Compatibility with `pycryptodome`, which allows a Windows build on Python 3.8/3.9. Behavior is identical to the original `pycrypto` code. |
| **Build** | `pyinstaller-hooks-contrib` pinned to a version compatible with PyInstaller 4.5.1, spec file cleanup, `build_windows.bat`. |

The console shows `Build Version: v1.5` at startup.

---

## Supported environments

v1.5 keeps the compatibility of upstream 1.4.2.2.H001:

- VMware Cloud Director **10.4.x and 10.5.x**. **Do not use with 10.6** – the tool selects the highest API version VCD offers, and API 39.x breaks the precheck (upstream issue [#21](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/21)). Keep VCD on its current version until all migrations are finished.
- An NSX-V backed and an NSX-T backed Provider VDC in the same VCD instance, managed by the same or different vCenter Server instances.
- A migration client (Windows or Linux) with network access to the VCD, NSX-T Manager, NSX-V Manager and vCenter Server APIs.

For the full list of prerequisites, supported features and unsupported features, see the official [NSX Migration for VMware Cloud Director 1.4.2 user guide](https://docs.vmware.com/en/VMware-NSX-Migration-for-VMware-Cloud-Director/index.html); it still describes this codebase accurately.

---

## Download and install

### Windows

1. Download `vcdNSXMigrator-v1.5-win64.zip` from the [Releases](../../releases) page.
2. Extract it to a local folder, for example `C:\v2t\`. Avoid OneDrive or other synced folders.
3. Keep the whole `vcdNSXMigrator` folder together; the executable needs the files next to it. OpenSSL binaries are bundled (the tool calls `openssl` for certificate operations).
4. Check that it runs:

   ```
   cd C:\v2t\vcdNSXMigrator
   vcdNSXMigrator.exe --help
   ```

No Python installation is needed on the migration client.

### Linux

No prebuilt Linux binary is published for v1.5 yet. Build one from source (see [Building from source](#building-from-source)) or use the upstream Linux build of 1.4.2.2.H001 if you do not need the fixes.

---

## Preparing your environment

The upstream user guide has the authoritative list. The items people most often miss:

**Cloud Director**
- NSX-T Manager registered in VCD, with **Network provider scope** set (required for Data Center Groups).
- Geneve network pool and an NSX-T backed Provider VDC with **identically named** storage policies and VM placement policies. The vCenter VM groups behind placement policies must also have identical names.
- Target Tier-0 / VRF imported as a provider gateway. Its subnets must contain the source edge gateways' external subnets (see [Known limitations](#known-limitations) for legacy IP blocks vs IP Spaces).
- A **dummy external network**: any port group registered as an external network. Each source edge gateway needs one free vNIC (at most 9 of 10 in use).
- Organization VDCs using shared direct networks need an NSX-T segment backed external network named `<source external network>-v2t`.

**NSX-T**
- An edge cluster for the target Tier-1 gateways (`EdgeGatewayDeploymentEdgeCluster`).
- Default MAC of the NSX-T virtual distributed router changed so it does not match the NSX-V DLR MAC.
- If you use the L2 bridging workflow: dedicated bridging edge nodes deployed from NSX-T Manager on the NSX-V cluster. Not needed when bridging is skipped.

**Before each organization VDC**
- Disable VMware Cloud Director Availability or backup/replication protection on its vApps.
- Delete empty vApps, power-cycle suspended VMs, eject media, disable vApp fencing.

---

## Configuration (userInput.yml)

Copy `sampleUserInput.yml` to a new file and edit it. One file per organization VDC (or per group of VDCs migrated together) keeps runs easy to track.

Minimal example for one organization VDC:

```yaml
---
VCloudDirector:
  Common:
    ipAddress: vcd.example.local
    username: administrator          # System organization administrator
    verify: False
  Organization:
    OrgName: ExampleOrg
  SourceOrgVDC:
    - OrgVDCName: ExampleOrg-VDC
      NSXVProviderVDCName: pvdc-nsxv
      NSXTProviderVDCName: pvdc-nsxt
      Tier0Gateways: provider-gateway-01   # a single name (string)
      EmptyIPPoolOverride: True
      EdgeGatewayDeploymentEdgeCluster: tenant-t1-edge-cluster
      AdvertiseRoutedNetworks: False
      NonDistributedNetworks: False
  DummyExternalNetwork: dummy-ext-net
  CloneOverlayIds: False

NSXT:
  Common:
    ipAddress: nsxt.example.local
    username: admin
    verify: False

NSXV:
  Common:
    ipAddress: nsxv.example.local
    username: admin
    verify: False

Vcenter:
  Common:
    ipAddress: vcenter.example.local
    username: administrator@vsphere.local
    verify: False

Common:
  MaxThreadCount: 75
  TimeoutForVappMigration: 3600
```

Key options worth understanding:

| Option | Notes |
|---|---|
| `Tier0Gateways` | Name of the target provider gateway, as shown in VCD. |
| `EmptyIPPoolOverride` | Set to `True` when external network subnets have no spare IP (for example /30 point-to-point subnets). Without it, rollback and cleanup fail when a pool would become empty. |
| `EdgeGatewayDeploymentEdgeCluster` | NSX-T edge cluster for the target Tier-1 gateways. Also required for DHCP on isolated networks. |
| `AdvertiseRoutedNetworks` | `True` forces a **dedicated** provider gateway. On a shared legacy provider gateway the precheck rejects it. |
| `EdgeClusterName` (under `NSXT`) | Bridging edge clusters. Optional; omit it when bridging is skipped. |
| `ImportedNetworkTransportZone` | NSX-T VLAN transport zone, needed only for dedicated direct networks. |
| `MaxThreadCount` / `TimeoutForVappMigration` | Parallel vApp moves and per-vApp timeout (seconds). Size them to your vMotion bandwidth. |

---

## Running the tool

Run the commands from the tool folder. On Windows, CMD is the documented shell; PowerShell also works, but put a `.\` in front of the executable and **quote comma-separated lists** (PowerShell otherwise splits them):

```
.\vcdNSXMigrator.exe --filepath=userInput.yml -s "bridging,movevapp"
```

| Task | Command |
|---|---|
| Assess all NSX-V org VDCs (read-only) | `vcdNSXMigrator.exe --filepath=v2tAssessmentInput.yml --v2tAssessment` |
| Precheck one migration (read-only) | `vcdNSXMigrator.exe --filepath=userInput.yml --preCheck` |
| Full migration | `vcdNSXMigrator.exe --filepath=userInput.yml` |
| Run only some workflows | `vcdNSXMigrator.exe --filepath=userInput.yml -e services` |
| Skip workflows | `vcdNSXMigrator.exe --filepath=userInput.yml -s bridging` |
| Roll back | `vcdNSXMigrator.exe --filepath=userInput.yml --rollback` |
| Clean up after a successful migration | `vcdNSXMigrator.exe --filepath=userInput.yml --cleanup` |
| Reuse saved passwords | add `--passwordFile=<path>` to any command except `--v2tAssessment` |

The first run prompts for the VCD, NSX-T, NSX-V and vCenter passwords and saves an encrypted password file; its location is printed on the console.

**Workflows** (used with `-e` / `-s`), in execution order:

| Workflow | What it does |
|---|---|
| `topology` | Always runs. Creates the target org VDC, edge gateways and networks. Disables the source org VDC. |
| `bridging` | L2 bridging between source and target networks. Optional. |
| `services` | North-south switchover: disconnects the source edge gateways, configures NAT, firewall, IPsec, DHCP, load balancer and so on, and connects the target edge gateways to the Tier-0. |
| `movevapp` | Moves vApps and VMs (vMotion) to the target org VDC. |

If a run fails, fix the cause and run the same command again: the tool resumes from the last completed step. Do not change objects the tool created while remediating.

---

## Recommended migration runbook

Per organization VDC:

1. **Assessment** once for the whole environment; resolve anything flagged for the VDC.
2. **Precheck** until clean: `--preCheck` (add `-s bridging` if you will skip bridging).
3. **Before the maintenance window:** `-e topology`. This builds the target side without touching north-south traffic.
4. **In the window:** run the remaining workflows, e.g. `-s bridging`. Verify north-south connectivity (NAT, routing toward the Tier-0) right after `services`, before VMs move.
5. **Verify** with the tenant: inbound NAT services, outbound traffic, VPNs, routes.
6. **Cleanup** only after the tenant confirms everything works, ideally a few days later. Cleanup deletes the source org VDC, so rollback is no longer possible afterwards.

**Without bridging**, VMs left in the source org VDC lose their gateway as soon as `services` runs. Plan `services` and `movevapp` for the same window, and move each org VDC completely.

**Rollback** is supported until cleanup. Plan time for it in every window; VM traffic can be interrupted for some time during rollback (NSX-T known issue), and reconnecting VM NICs from the tenant portal restores it.

---

## Logs and troubleshooting

Logs are written to the `logs` folder next to the executable:

| File | Content |
|---|---|
| `VCD-NSX-Migrator-Main-<timestamp>.log` | Full debug log of a migration, rollback or cleanup run. Start here for tracebacks. |
| `VCD-NSX-Migrator-preCheck-Summary-<timestamp>.log` | Table of failed validations from a precheck. |
| `<VCD-UUID>-v2tAssessmentReport-*.csv` | Assessment detailed and summary reports (in `reports`). |

Common messages:

| Message | Meaning |
|---|---|
| `... is connected to multiple subnets of external network ...` | An edge gateway uplink has several subnets, and not all of them are covered by the target provider gateway. Add the missing subnet(s) to the provider gateway. |
| `... equivalent NSX-T segment backed external network - <name>-v2t is not present` | Either a subnet is missing from the provider gateway or the `-v2t` network has not been created. |
| `EmptyPoolOverride flag must be set to true ...` | Set `EmptyIPPoolOverride: True` for that org VDC. |
| `Could not find disk storage policy <X>` | The **disk's** storage policy is missing in the target, not necessarily `<X>` (misleading upstream message, issue [#34](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/34)). |
| `Specified parent network is invalid` during `movevapp` | Target network not in scope of the target org VDC; check Data Center Group / shared network scoping (issue [#13](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/13)). |

---

## Known limitations

These come from upstream behavior and are **not** changed in v1.5:

- **Legacy IP blocks need exact subnets.** On a provider gateway using legacy IP blocks, each source edge gateway subnet must exist on the provider gateway with the same network and prefix; overlapping subnet definitions cannot coexist. Provider gateways using **IP Spaces** accept larger internal scopes that contain the source subnets.
- **Every external subnet needs a static pool.** VCD rejects external network subnets with an empty static IP pool.
- **Static routes** whose next hop is reached through a Tier-0 connected uplink are reported as warnings and **not migrated**; configure them manually on the Tier-1 or Tier-0/VRF.
- **NAT rules with ranges** are only partly validated: the precheck catches ranges in DNAT translated addresses, but ranges in DNAT original addresses or SNAT addresses pass the precheck and fail during `services` (issue [#6](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/6)). Check NAT rules before the window.
- **Application port profiles** are reused within a run; when a second org VDC of the same organization is migrated in a later run, a `CUSTOM-...` profile name conflict is possible (issue [#2](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/2)).
- **VCD 10.6** is not supported (issue [#21](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/21)).
- `movevapp` moves all vApps of an org VDC; there is no per-vApp selection (feature request [#5](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues/5)).

---

## Building from source

### Windows

Requirements: Python **3.8 or 3.9** x64 (PyInstaller 4.5.1 does not support newer versions), [Win64 OpenSSL Light](https://slproweb.com/products/Win32OpenSSL.html) installed in `C:\Program Files\OpenSSL-Win64`, internet access for pip.

```
git clone -b release/v1.5 https://github.com/tylmz/NSX_V2T_Migration_Tool.git
cd NSX_V2T_Migration_Tool
build_windows.bat
```

Or download the source zip of the `v1.5` release, extract it and run `build_windows.bat` from CMD. The script creates a virtual environment, installs the pinned dependencies, builds with PyInstaller, copies OpenSSL into the package and runs `--help`. The result is in `dist\vcdNSXMigrator\`.

To build with Python 3.9 instead of 3.8, change `py -3.8` to `py -3.9` in `build_windows.bat`.

### Linux

Build on the **oldest** distribution you will run on (PyInstaller binaries need the same or a newer glibc), with Python 3.8 or 3.9:

```
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements_build.txt
pip install -r src/requirements-windows.txt     # pycryptodome variant, works on Linux too
python -m PyInstaller --noconfirm src/vcdNSXMigrator.spec
tar -czf vcdNSXMigrator-v1.5-linux.tar.gz -C dist vcdNSXMigrator
```

`openssl` must be available on the PATH of the machine running the tool.

---

## Security notes

- The password file stores the encryption key next to the encrypted passwords – treat it as plain text. Restrict its permissions and delete it when the migration project ends.
- Do not commit filled-in `userInput*.yml` files, logs or reports: they contain hostnames, organization names and IP addresses. The repository `.gitignore` excludes them.
- The tool's dependencies are pinned to 2021 versions for build compatibility. Run it from a dedicated, isolated migration client.
- Use `verify: True` and `CertificatePath` when your certificates are trusted, instead of disabling certificate validation.

---

## License and attribution

The original source code is Copyright © VMware, Inc. and is published and maintained by Calsoft in [Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool). Copyright headers and `open_source_licenses.txt` are kept unchanged. The Windows package includes OpenSSL binaries, distributed under the Apache License 2.0 (see `OpenSSL-license.txt` in the package).

Issues specific to v1.5 (the patches or the Windows build) can be reported in this repository's Issues. Problems that also occur with the upstream build belong in the [upstream repository](https://github.com/Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool/issues).
