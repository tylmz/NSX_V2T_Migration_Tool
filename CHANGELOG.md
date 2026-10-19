# Changelog

Community builds of the NSX Migration for VMware Cloud Director tool, based on upstream
`MT_v1.4.2.2.H001` (Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool). Details of every patch are in
[PATCHES.md](PATCHES.md); every changed line in the source is marked with its `PATCH-n` comment.

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
