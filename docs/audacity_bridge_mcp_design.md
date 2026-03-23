# Audacity Bridge Design Note (Future MCP Wrapper)

## Current architecture

The local bridge is intentionally split into layers:

- `audacity_bridge/pipe_transport.py`: low-level mod-script-pipe transport for Windows named pipes.
- `audacity_bridge/response_parser.py`: parser for command replies and `BatchCommand` status lines.
- `audacity_bridge/commands.py`: high-level methods (`import_audio`, `select_time`, `add_silence`, etc.) plus raw passthrough.
- `audacity_bridge/cli.py`: terminal entrypoint for local workflows.
- `audacity_bridge/workflows/sample_workflow.py`: repeatable production-style sequence.

This keeps transport concerns separate from command semantics so a later wrapper can reuse the same core.

## MCP wrap strategy (later)

A future MCP server can map MCP tools directly to `AudacityBridge` methods:

- `audacity_ping` -> `AudacityBridge.ping()`
- `audacity_raw_command` -> `AudacityBridge.raw_command(...)`
- `audacity_import_audio` -> `AudacityBridge.import_audio(...)`
- `audacity_export_audio` -> `AudacityBridge.export_audio(...)`

Recommended server-side safeguards for MCP phase:

1. Keep a singleton bridge instance and serialize calls with one command at a time.
2. Expose only explicit safe tools by default; keep raw command behind an advanced flag.
3. Enforce local-path allowlists for input/output paths.
4. Return both parsed payload and raw response to preserve debugging detail.
5. Keep network off by default; do not expose unauthenticated remote access.

## Operational constraints to preserve

- Audacity scripting is effectively single-project and single-command-at-a-time.
- Some commands differ by Audacity version and installed effects.
- Window focus and UI state can affect reliability for certain commands/effects.

The current design keeps these constraints visible and explicit, so MCP can be added without rewriting core logic.
