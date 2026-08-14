# Ignition

Launch your whole sim racing stack with one button.

CrewChief, Trading Paints, SimPro Manager, SimHub, your overlays, the sim itself — ticked,
ordered, and started in sequence. Then closed again when you're done.

One window. First run finds what you have installed and ticks it. If you never open the
Edit dialog, nothing is lost.

## Using it

| | |
|---|---|
| **GO** | Launches every ticked app in order, waiting the per-app delay between them, skipping anything already running |
| **SHUTDOWN** | Closes them again in reverse order — asks politely first, forces only if something won't go |
| **Click the ☑** | Tick or untick an app without removing it |
| **Drag a row** | Reorder. Put the sim last; put overlays that hook it earlier |
| **Add… / Edit… / Remove** | Any program, not just the ones in the catalog |
| **Rescan** | Look again for newly installed apps, keeping what you already have |

Order matters more than it looks. Trading Paints wants to be up before iRacing loads a
session; CrewChief doesn't care. That's what the per-app **wait** is for.

## Per-app settings

Double-click a row to open it.

| Field | |
|---|---|
| **Program** | The `.exe` or shortcut. Browse resolves a shortcut to its real target for you |
| **Arguments** | Optional command line |
| **Start in** | Working directory — blank means the program's own folder. Some apps (CrewChief) care |
| **Process name(s)** | Comma-separated. Used to skip if already running, and to shut down |
| **Wait after** | Seconds to pause before starting the next app |
| **Run as administrator** | Raises the UAC prompt for that app only |
| **Skip if it's already running** | On by default, so a second GO doesn't spawn duplicates |

## What it detects automatically

CrewChief, Trading Paints, SimPro Manager, SimHub, Garage 61, Racelab, iOverlay, VRS
DirectForce Pro, Z1 Dashboard, Sim Racing Studio, Discord, iRacing — plus
[Cold Tires](https://github.com/OblivionsPeak/cold-tires) and
[Grid Check](https://github.com/OblivionsPeak/grid-check).

Detection tries three things in order: the registry's installed-programs list, Start Menu
and Desktop shortcuts, then known install paths. The shortcut pass is the one that carries
it — plenty of these ship under an exe name nobody would guess (SimPro Manager is
`simpro.exe`, Garage 61 is `garage61-launcher.exe`), and a shortcut points at the truth.

Anything not in the catalog goes in through **Add…**. The catalog is a convenience, not a
limit.

## Install

Grab `ignition.exe` from [Releases](../../releases) and run it. No installer.

From source:

```bash
python app.py
```

Standard library only — `tkinter`, `winreg`, `subprocess`, `ctypes`. `pywin32` is used if
you happen to have it (faster shortcut resolution) and quietly skipped if you don't.

## Config

`ignition.json` is written next to the exe, so it's portable and hand-editable — but you
shouldn't need to touch it. Copying it to another machine carries your whole list over,
assuming the same install paths.

CLI: `--rescan` ignores the saved list and re-detects from scratch.

## Notes

Verified on this machine: detection found 11 of 14 catalog apps (the other three aren't
installed), both shortcut-resolution paths work, and launch → skip-if-running → shutdown
round-trips cleanly. Elevation uses `ShellExecuteW` with the `runas` verb, so declining the
UAC prompt is reported as a failed launch rather than a silent no-op.
