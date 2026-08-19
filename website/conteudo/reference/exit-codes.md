---
title: Exit codes
description: The four exit codes, and the claim each one makes.
---

# Exit codes

| Code | Meaning |
| --- | --- |
| `0` | did what was asked |
| `1` | could not run |
| `2` | you invoked me wrong |
| `3` | ran, and the answer is no |

The axis between `2` and `3` is *whose defect it is* — and that distinction is exactly what makes both usable in a script or a CI pipeline, where "fix your input" and "the input was fine and the answer is no" call for different responses.

A `--runtime` value outside the closed table is `2`: the value you typed does not exist anywhere, so the defect is in the line itself. A `--runtime` value that *is* in the table, but has no destination in the scope you asked for, is `3` instead: the value is real, the flag is real, nothing about the invocation is malformed — the destination simply does not exist for that pairing, and that is a fact about the world, not about what you typed.

A `--from` search root that could not be obtained at all — network unreachable, repository not found, no read access — is `1`, and the underlying transport's own error message is passed through unmodified, because that message is the one that actually names the problem. Once the root *was* obtained and searched, and the skill you asked for either is not there, or is there more than once and the name is ambiguous, that is `3`: the command ran to completion and the answer is negative.

`doctor` follows the same rule: an unhealthy report is `3`, never `1`, because the check itself succeeded — it computed a real answer, and the answer happens to be no.

A traceback never reaches the terminal. An exception the product does not recognise as one of its own named failures becomes an error panel instead of raw Python output, and exits `1` — which is itself a claim: it says the bug is in overpower, not in what you typed.
