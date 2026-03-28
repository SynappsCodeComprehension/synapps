# Recording the Synapps README GIF

## Tools

Install [VHS](https://github.com/charmbracelet/vhs) — deterministic terminal GIF recordings:

```bash
brew install vhs
```

## Tape Files

| File | Project | Description |
|------|---------|-------------|
| `demo.tape` | ~/Dev/oneonone (C# + TS) | Primary demo — callers, trace, context |
| `demo-self.tape` | ~/Dev/synapps (Python) | Self-referential demo using Synapps's own codebase |

## Demo Commands (oneonone)

The primary demo shows 3 commands against the OneOnOne C# project, each showing something grep/Serena/CodeGraphContext can't do:

1. **`synapps entry-points CalendarEventService.BuildEventRequest`** — "Which API endpoints reach this private helper?" 3 paths, the longest crossing 5 hops through 2 interfaces. Multi-hop reverse traversal through DI.

2. **`synapps trace MeetingsController.CompleteMeeting RecurringCadenceService.CalculateNextOccurrence`** — 6-hop forward call path through DI interfaces. Shows Synapps following calls through interface dispatch.

3. **`synapps context ManagedEmployeeService.GetByIdAsync --scope=edit`** — Source code, interface contract, 2 direct callers with line numbers, 9 tests. Everything needed before editing, in one call.

## Recording

```bash
# Ensure the project is indexed
cd ~/Dev/oneonone && synapps index .

# Record
cd ~/Dev/synapps/docs/demo
vhs demo.tape              # produces synapps-demo.gif

# Move to repo root for README
mv synapps-demo.gif ../../
```

## Tips

- Keep under 20 seconds — GitHub README GIFs should be fast and punchy
- Font size 20 at 1100x650 renders well on GitHub
- If output is too large: `gifsicle --optimize=3 --lossy=80 -o out.gif synapps-demo.gif`
- VHS requires `ttyd` and `ffmpeg` — `brew install` handles these automatically
