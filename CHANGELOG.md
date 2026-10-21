# Changelog

Community builds of the NSX Migration for VMware Cloud Director tool, based on upstream
`MT_v1.4.2.2.H001` (Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool). Details of every patch are in
[PATCHES.md](PATCHES.md); every changed line in the source is marked with its `PATCH-n` comment.

## v1.5.9 - 2026-10-21 (pre-release)

Changed
- NSX-V SNAT rules with an IP range as original address get the smallest network that covers the range;
  a warning is logged when it is larger than the range. Earlier builds used a larger network (up to the
  /24 of the range end), so tenants migrated with them can have broader SNAT sources (PATCH-17).

Fixed (PATCH-17, code paths from the upstream base)
- v2t assessment stopped on Org VDC names that were not found and dropped Org VDCs that vanished during the
  run from the report; an empty result crashed the report.
- Precheck assessment: a failed Org VDC network lookup crashed the error report; shared-network failures did
  not count in the overall result; an empty result crashed it.
- Route redistribution carried `TIER1_CONNECTED` over to later edge gateways (shared constant list).
- DHCPv6 rollback enabled SLAAC instead of disabling it.
- NAT payload creation failed on an edge without default gateway.
- Catalog owner update and sharing treated HTTP 200 as failure.
- Query API paging failed after the first page; the provider VDC lookup only searched the last page.
- Security group validation errors were lost when a group was checked again.
- NAT range conversion built lists of every address (very slow or out of memory for wide ranges).
- QoS profiles sent the bandwidth as text in the deprecated field.
- `movevapp`: a VM without a matching placement policy got the previous VM's policy.
- NSX-V password prompt checked the NSX-T password; a wrong password did not reach the retry prompt; an
  unexpected NSX-V login response counted as success.
- Running without arguments or without `--filepath` crashed before printing help or a clear error.
- Several error handlers failed themselves and hid the original error.

## v1.5.8 - 2026-10-20 (pre-release)

Added
- PATCH-14: static routes of the NSX-V edge.
  - Precheck records every route in metadata and logs its class and the planned action.
  - New `Tier1StaticRoutes`, per edge gateway under `EdgeGateways`: the edge's static routes as an explicit
    list of `{network, nextHop, adminDistance, description}`. Precheck compares it with the ESG: a route that
    is not listed, a listed route the ESG does not have, a duplicate or a different `adminDistance` fails
    the precheck. Auto-plumbed routes are not compared.
  - The listed routes are created on the tenant Tier-1 in services, scoped to the network that holds the
    next hop; existing routes for the same destination are completed instead of duplicated; rollback
    removes the routes the tool created.
  - `DmzStaticRoutes` also creates Tier-0 routes for Tier-1 static-route destinations inside its blocks (for
    example a public block a customer pfSense owns behind an internal interface).
- PATCH-15: interfaces added to the NSX-V edge outside VCD (vCenter/NSX-V UI, for example MPLS or VPN VLANs).
  - Precheck detects and logs them for every edge.
  - With the optional per-edge `ServiceUplinks`, the tool creates an NSX-T VLAN segment and a VCD external
    network `<portgroup>-v2t` (exact portgroup name) in topology, and in services disconnects the NSX-V
    interface, attaches the external network to the Tier-1 as a service interface with the same IPs, keeps
    NAT rules bound to it and adds NO_SNAT exceptions towards it. Rollback reverses all of it.
  - Every change is recorded before it is made and checked afterwards, so an interrupted run or rollback
    continues from the live state; only objects the tool created are changed or deleted.

Changed
- Precheck: an edge gateway with static routes now needs `Tier1StaticRoutes` matching them (PATCH-14).
- PATCH-11 `--movecatalog`: moved catalog items are recorded by their vApp template or media; rollback
  moves back exactly those items and refuses move records without an item list.
- Exit codes: 0 success, 1 failure, 130 aborted (PATCH-16).
- Release files include the diff against the previous release instead of the diff against H001.

Fixed (PATCH-16, code paths from the upstream base)
- DHCP and IPsec rollback could wait forever for an NSX-V edge job; the wait now has a deadline.
- Cleanup failed on uplink subnets without static pool (e.g. /30 uplinks with `EmptyIPPoolOverride`).
- Firewall rules linked to SNAT rules got the NAT rule's interface as scope (wrong NAT type field); a
  missing related rule reused the previous rule's data; NAT rules beyond the first 128 were not read.
- DNAT-to-firewall matching for non-distributed networks matched address prefixes (192.168.1.1 matched
  192.168.1.100) and failed on translated ranges.
- NAT configuration and non-distributed routing stopped at the first edge gateway that needed no change,
  skipping later edge gateways of the same Org VDC.
- Locks could stay held after an early return or exception, blocking other threads.
- Worker threads could crash on a queue race, and jobs were not always acknowledged.
- NSX-T lists were read as one page only.
- Concurrent certificate migrations shared fixed private-key file names; keys are no longer written to
  files.
- A failed certificate deletion left the tenant context header on later requests.
- Metadata values were parsed with `eval`; rollback and cleanup tasks read from metadata were executed
  without checking them.
- Application port profiles could be reused without verifying their NSX-T Manager.
- On Linux the password file was readable by others until it had been written.

## v1.5.7 - 2026-10-19 (pre-release)

Fixed
- PATCH-13: with `TransportSubnets`, when an edge's transport subnet is not migrated, SNAT rules on
  its other uplink subnets that move to the Tier-0 uplink (for example a public subnet on its own
  external network) are created with the source destination instead of being limited to that
  subnet. Uplinks that become Tier-1 service interfaces keep the original behaviour. Completes the
  SNAT fix of PATCH-12, which covered subnets on the same external network as the transport subnet.

## v1.5.6 - 2026-10-19 (not published, included in v1.5.7)

Fixed
- PATCH-12: SNAT rules whose translated IP sits on the same uplink as the edge's default route (for
  example a public /30 on the same external network as the transport subnet) were created on NSX-T
  with destination = that uplink's subnet instead of `any`. Outbound traffic to the internet was
  therefore not translated. Such rules now keep the source destination (`any`). SNAT rules on uplinks
  without the default route (private service uplinks) keep the original behaviour. Static routes
  through the default-route uplink no longer produce extra NO_SNAT rules.
- PATCH-12: `DmzStaticRoutes` did not create any Tier-0 static route. It looked for the DMZ networks
  among the source Org VDC networks after `services` had already converted them to isolated networks,
  found none and skipped silently. It now uses the target Org VDC networks connected to the Tier-1
  and logs a warning when `DmzStaticRoutes` is set but no network matches.

Upgrading
- Org VDCs migrated with v1.5.4 or v1.5.5: check SNAT rules on the target edge gateways for a
  destination equal to the uplink subnet, and check the Tier-0 for the DMZ static routes. Fix them
  manually, or roll back and migrate again with v1.5.6.

## v1.5.5 - 2026-10-06 (not published, included in v1.5.7)

Added
- PATCH-11: `--movecatalog` mode. Run after `movevapp` to move catalog items stored on the source
  Org VDC to `<catalog>-v2t` catalogs on the target (created when missing). `--rollback` moves them
  back as its last step before the target networks are deleted and removes `-v2t` catalogs it
  created; `--cleanup` deletes the old source catalogs and drops the `-v2t` suffix. Without
  `--movecatalog` the tool behaves as before.

Fixed (found in review before release)
- `moveCatalogItem` had lost its `@isSessionExpired` decorator when the PATCH-11 code was inserted,
  so long catalog moves in `--movecatalog`, rollback and the original cleanup path could run into an
  expired VCD session. The decorator is restored.
- `finalizeCatalogMoves` now saves the finished catalog list to the target Org VDC metadata.
- Removed an unused variable in `rollbackCatalogMoves`.

Documentation
- README: `TransportSubnets` and `DmzStaticRoutes` labelled as available since v1.5.4; password
  file note corrected to v1.5.1 and later; source zip reference updated to v1.5.5; new known
  limitation on rollback and vApp templates created on the target; patch tables ordered by number.
- New CHANGELOG.md.

## v1.5.4 - 2026-10-05 (pre-release)

- PATCH-10 (opt-in, per Org VDC): `TransportSubnets` leaves an edge's transport (default route)
  subnet out of the target and connects transport-only edges to the Tier-0 without uplink IPs;
  `DmzStaticRoutes` creates provider Tier-0/VRF static routes to the tenant Tier-1 for routed
  public networks, removed again by rollback.
- PATCH-10 (always on): fix for the precheck crash on policy-based IPsec without NAT rules.
- Includes PATCH-7, PATCH-8 and PATCH-9 (first published here).

## v1.5.3 (not published separately)

- PATCH-9: application port profiles are found or reused instead of colliding (upstream issue #2);
  `-<vdc>` suffix on name conflicts; only the target NSX-T Manager's profiles are reused; hashed
  names for long port lists.

## v1.5.2 (not published separately)

- PATCH-8: vApp runtime and storage lease check in precheck and assessment (new assessment column).

## v1.5.1 (not published separately)

- PATCH-7: password files protected with DPAPI on Windows; mode 600 on Linux.

## v1.5 - 2026-10-04

- PATCH-1 / 1b: null-guard for empty IP pools; never add an IP already in the target pool.
- PATCH-2: multiple address groups per vNIC (static route check, load balancer VIP maps).
- PATCH-4: readable error for missing `-v2t` networks (upstream issues #4 and #7).
- PATCH-5: pycryptodome compatibility for the Windows build.
- Build: pinned `pyinstaller-hooks-contrib`, spec cleanup, `build_windows.bat`.

Not built: PATCH-3 (containment for legacy pool lookup).
