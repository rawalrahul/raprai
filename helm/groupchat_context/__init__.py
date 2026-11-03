"""
helm/groupchat_context — how RAPR manages what each AI in a group chat sees.

Every member of a group chat is run as a fresh, one-shot CLI call, so RAPR
builds that member's whole prompt itself on every reply. This package owns
that job:

  • archive.py   every chat message, kept on disk for good (nothing is lost
                 when the room's own list is trimmed)
  • blocks.py    write-once summaries in levels: level 1 covers a short run of
                 messages, level 2 merges old level-1 parts, level 3 merges
                 old level-2 parts. A summary is never rewritten.
  • budget.py    how much each member may see: at least 200K tokens for online
                 AIs (most have 1M windows), a share of the window for offline
                 models (Ollama, LM Studio…)
  • render.py    one view per member: the same history, shown in as much
                 detail as that member's budget allows (fit.py does the fitting)
  • folder.py    the background job that writes the summaries and merges them
  • summariser.py  who writes them: Claude, else the strongest paid AI set up
  • validate.py  checks a summary kept the exact names, paths and numbers, and
                 a plain recap for when no AI could write one
  • facts.py     the room's running facts: decisions, owners, requirements
  • recall.py    getting detail back: search, expand a summary, "(recall b3)"
  • meter.py     how full each member's prompt is, for the app
  • mcp_tools.py group_search / group_recall for AIs that use RAPR's MCP server

Ideas borrowed (not code) from billion-context / acp-kernel: layered,
incremental, reversible summaries that are never re-summarised wholesale, key
strings kept word for word, a model writes and the host checks, and a stable
prompt prefix so providers can reuse their prompt cache.
"""
