---
title: MCP servers
description: The graft — one key inside a file that is yours, secrets never written, and targets derived rather than declared.
---

# MCP servers

This page covers MCP: how overpower grafts a server into a configuration file it does not own, writing one key and leaving the rest of the file untouched. It covers why a secret is never written to disk by overpower, how the targets for a given server are derived from the runtime and scope rather than declared by you, and which pairs of runtime and scope actually accept a graft.
