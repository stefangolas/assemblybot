# 004 — Rung 2 is a passive belt axis (no motor required)

**Decision:** The Rung 2 milestone is a **passive** S3M timing-belt loop on retained idlers + a structurally
mounted linear rail. A powered/motorized drive end is NOT required for this milestone.

**Why:** The capabilities Rung 2 must force — guide/slider, retained revolutes, periodic belt mesh, belt
capture, and a real load path to ground — are all exercised by a passive loop. Adding a motor/driven pulley is
scope creep that doesn't advance those capabilities and pulls in stepper/coupling parts unrelated to the goal.

**Consequences:** Both belt ends are idlers (bearing idlers on shoulder-screw axles). A plain spare drive
pulley is kept for a future driven end but is not part of this rung. "Done" = every body `HELD_CONFIRMED` + the
assembly looked at in isolation and context — not a working motor.
