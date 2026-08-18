---
title: Shipping
description: The architecture — the modules, the flow between them, and two sibling roots with opposite invariants.
---

# Shipping

This page maps the codebase for someone about to change it: the modules, what each one is responsible for, and the path a single invocation takes through them. It also covers the two sibling content roots and why their invariants are opposites — one is vendored and must stay byte-identical to its source, the other is authored here — because most of the surprising rules in this repository descend from that split.
