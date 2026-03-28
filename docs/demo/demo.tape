# Synapps README Demo — OneOnOne project
#
# Prerequisites:
#   1. synapps index .    (oneonone project must already be indexed)
#   2. Install VHS: brew install vhs
#   3. Run from oneonone dir: cd ~/Dev/oneonone && vhs ~/Dev/synapps/docs/demo/demo.tape

# --- Settings ---
Output synapps-demo.gif
Set Theme "Catppuccin Mocha"
Set FontFamily "Menlo"
Set FontSize 16
Set LetterSpacing 0
Set Width 1200
Set Height 700
Set Padding 20
Set TypingSpeed 10ms
Set PlaybackSpeed 1
Set Shell "zsh"

# Hidden setup: activate venv so synapps is available
Hide
Type "source ~/Dev/synapps/.venv/bin/activate"
Enter
Sleep 1s
Type "clear"
Enter
Sleep 500ms
Show

# --- Scene 1: Which API endpoints reach this internal method? ---
Sleep 500ms

Type "synapps entry-points -t RecurringCadenceService.CalculateNextOccurrence"
Enter
Sleep 4s

# --- Scene 2: Trace a specific path through DI ---
Sleep 2s

Type "synapps trace -t MeetingsController.CompleteMeeting RecurringCadenceService.CalculateNextOccurrence"
Enter
Sleep 4s

# --- Scene 3: Get full edit context ---
Sleep 2s

Type "synapps context ManagedEmployeeService.GetByIdAsync --scope=edit"
Enter
Sleep 6s

# Hold final frame
Sleep 3s
