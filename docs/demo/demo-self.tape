# Synapps Demo — Self-Referential (Python)
# Alternative tape that records against Synapps's own codebase.
#
# Prerequisites:
#   1. docker compose up -d
#   2. cd ~/Dev/synapps && synapps index . --language python
#   3. Run: vhs docs/demo/demo-self.tape
#
# Use `synapps search <name>` to verify symbol names if they've changed.

Output synapps-demo.gif
Set Theme "Catppuccin Mocha"
Set FontFamily "JetBrains Mono"
Set FontSize 20
Set Width 1100
Set Height 650
Set Padding 20
Set TypingSpeed 40ms
Set PlaybackSpeed 1
Set Shell "zsh"

Type "cd ~/Dev/synapps"
Enter
Sleep 500ms

# --- Scene 1: Who calls this? ---
Sleep 300ms

Type "# Who calls the core indexing method?"
Enter
Sleep 600ms

Type "synapps callers SynappsService.index_project"
Enter
Sleep 3s

# --- Scene 2: Trace a call path ---
Sleep 1.5s

Type "# Trace the path from CLI to graph writes"
Enter
Sleep 600ms

Type "synapps trace SynappsService.index_project GraphConnection.execute"
Enter
Sleep 3.5s

# --- Scene 3: Edit context ---
Sleep 1.5s

Type "# Full context before editing"
Enter
Sleep 600ms

Type "synapps context SynappsService.index_project --scope=edit"
Enter
Sleep 5s

Sleep 3s
