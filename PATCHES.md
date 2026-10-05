# NSX Migration for VCD v1.5 (community build based on 1.4.2.2.H001)

Base: Calsoft-Pvt-Ltd/NSX_V2T_Migration_Tool tag MT_v1.4.2.2.H001 (release.yml build 2024-08-02).
Every changed line is marked with a `PATCH-n` comment. Full diff: patches-1.4.2.2.H001.diff

| Patch | File(s) | Change | Why |
|---|---|---|---|
| PATCH-1 | core/vcd/vcdOperations.py | Treat a null `ipRanges.values` as an empty list in the target pool update (topology), source pool cleanup and target pool rollback | VCD returns `null` for empty pools; the tool crashed with AttributeError/TypeError |
| PATCH-1b | core/vcd/vcdOperations.py (`_updateTargetExternalNetworkPool`) | Add only IPs not already in the target pool, one single-IP range each | Allows a target /30 pool to be pre-seeded with the edge's own IP without creating a duplicate range |
| PATCH-2 | core/vcd/vcdValidations.py (`staticRouteCheck`, LB vNIC map), core/vcd/vcdConfigureEdgeGatewayServices.py (LB vNIC map) | Iterate every address group on a vNIC instead of assuming exactly one | Mixed public+private uplinks have two address groups; static route check crashed, LB VIP mapping silently missed IPs |
| PATCH-4 | core/vcd/vcdValidations.py (edge uplink and shared direct network validation) | Return the intended error when the `-v2t` network does not exist | GitHub issues #4 and #7: "list index out of range" instead of a readable message |
| PATCH-5 | commonUtils/certUtils.py | Raw RSA decrypt via `pow()` and explicit `AES.MODE_ECB` | Works with pycryptodome (pycrypto does not build on Windows / Python 3.8); mathematically identical to pycrypto behaviour |

Not included: patch 3 (containment for legacy pools) - not needed if IP Spaces is used.

src/release.yml reports Build v1.5. The build version is only shown on the console and in assessment reports; it is not stored in migration metadata.

Build changes: pyinstaller-hooks-contrib pinned to 2021.3 (compatible with PyInstaller 4.5.1); spec hidden imports cleaned up; Windows requirements use pycryptodome; build_windows.bat added.
