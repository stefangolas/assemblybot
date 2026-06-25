# 005 — A real belt PN is required before belt capture

**Decision:** Final belt capture (binding the belt into the carriage clamp / load path) requires a real
selected belt part number. The generated routed belt loop is allowed as the ONE generated flexible element, but
it must represent a real catalog belt instance (S3M, 3 mm pitch, 10 mm width, closed-loop length ≈ teeth×pitch).

**Why:** The belt is the one place generated geometry is permitted (a flexible loop fitted to the pulleys), but
a captured, load-bearing belt is a real purchased part — its pitch/profile/width and pitch-length must come
from a catalog SKU, not be assumed. Authoring a belt-capture edge against an unsourced belt would be phantom
hardware ([003](003-no-phantom-hardware.md)).

**Consequences:** The belt-clamp wiring (jaw + cap screws sandwiching the belt) is gated on selecting the real
S3M-10 belt. Until then the clamp's real parts (jaw, cap screws, plate ports) may be authored and
drawing-verified, but the belt-captured load-path edge is not instantiated. The pitch/profile/width predicates
are unambiguous for S3M-10 regardless; the open item is the exact closed-loop length PN.
