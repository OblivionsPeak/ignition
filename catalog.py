"""Built-in catalog of sim racing apps, used only to pre-populate the list on
first run. Nothing here is required — anything can be added by hand, and an
entry that doesn't match simply doesn't appear.

Match fields, in the order detection tries them:
  registry  — substrings matched against Uninstall\\DisplayName
  shortcut  — substrings matched against Start Menu .lnk names
  exe       — filenames looked for under the `paths` globs
  paths     — glob patterns, %ENVVAR% expanded

`process` is what we match against tasklist for skip-if-running and shutdown.
Where an app's exe name is uncertain, the shortcut match carries it — that is
the most reliable signal on Windows and the reason it exists in the list.
"""

# Ordered roughly the way you'd want them launched: overlays and services
# first, the sim itself last.
CATALOG = [
    {
        'name': 'CrewChief',
        'process': 'CrewChiefV4.exe',
        'registry': ['CrewChief'],
        'shortcut': ['CrewChief'],
        'exe': ['CrewChiefV4.exe'],
        'paths': [r'%ProgramFiles(x86)%\Britton IT Ltd\*', r'%ProgramFiles%\Britton IT Ltd\*'],
        'delay': 3,
    },
    {
        'name': 'Trading Paints',
        'process': 'TradingPaints.exe',
        'registry': ['Trading Paints'],
        'shortcut': ['Trading Paints'],
        'exe': ['TradingPaints.exe', 'Trading Paints Downloader.exe'],
        'paths': [r'%LOCALAPPDATA%\TradingPaints', r'%ProgramFiles(x86)%\Trading Paints'],
        'delay': 3,
    },
    {
        # SimPro Manager 3 is a Simagic daemon plus a CEF front end. The Start
        # Menu shortcut launches simdaemon.exe with its working directory set to
        # Simpro3\bin, and the daemon brings up simpro3.exe — so both names have
        # to count as "running". Deliberately no `registry` entry: that key's
        # DisplayIcon points at the daemon without the working directory, and
        # the registry pass would win before the shortcut is ever consulted.
        'name': 'SimPro Manager 3',
        'process': 'simpro3.exe, simdaemon.exe',
        'shortcut': ['SimPro Manager 3'],
        'exe': ['simpro3.exe'],
        'paths': [r'%ProgramFiles(x86)%\SIMAGIC\Simpro3\bin',
                  r'%ProgramFiles%\SIMAGIC\Simpro3\bin'],
        'delay': 3,
    },
    {
        # The previous generation, still installed alongside 3 on plenty of
        # machines — hence off by default, since starting two wheelbase managers
        # at once helps nobody. Only the registry DisplayName separates the two
        # cleanly ("simpro SimProV2.1.8…" against "Simpro3 SimProV3.2.0…"); the
        # install directory and exe are both just "simpro".
        'name': 'SimPro Manager 2',
        'process': 'simpro.exe',
        'registry': ['SimProV2'],
        'shortcut': ['SimPro Manager'],
        'exe': ['simpro.exe'],
        'paths': [r'%ProgramFiles(x86)%\simpro\bin', r'%ProgramFiles%\simpro\bin'],
        'delay': 3,
        'enabled': False,
    },
    {
        'name': 'SimHub',
        'process': 'SimHubWPF.exe',
        'registry': ['SimHub'],
        'shortcut': ['SimHub'],
        'exe': ['SimHubWPF.exe'],
        'paths': [r'%ProgramFiles(x86)%\SimHub', r'%ProgramFiles%\SimHub'],
        'delay': 3,
    },
    {
        'name': 'Garage 61',
        'process': 'garage61.exe',
        'registry': ['Garage 61', 'Garage61'],
        'shortcut': ['Garage 61', 'Garage61'],
        'exe': ['garage61.exe', 'Garage61.exe'],
        'paths': [r'%LOCALAPPDATA%\Programs\garage61*', r'%LOCALAPPDATA%\garage61*'],
        'delay': 2,
    },
    {
        'name': 'Racelab',
        'process': 'RaceLabApps.exe',
        'registry': ['Racelab', 'Race Lab'],
        'shortcut': ['Racelab', 'Race Lab'],
        'exe': ['RaceLabApps.exe'],
        'paths': [r'%LOCALAPPDATA%\Programs\racelabapps*', r'%LOCALAPPDATA%\racelab*'],
        'delay': 2,
    },
    {
        'name': 'iOverlay',
        'process': 'iOverlay.exe',
        'registry': ['iOverlay'],
        'shortcut': ['iOverlay'],
        'exe': ['iOverlay.exe'],
        'paths': [r'%LOCALAPPDATA%\Programs\iOverlay*', r'%ProgramFiles%\iOverlay*'],
        'delay': 2,
    },
    {
        'name': 'VRS DirectForce Pro',
        'process': 'VRS DirectForce Pro.exe',
        'registry': ['VRS', 'Virtual Racing School'],
        'shortcut': ['VRS', 'Virtual Racing School'],
        'exe': ['VRS DirectForce Pro.exe'],
        'paths': [r'%LOCALAPPDATA%\Programs\vrs*', r'%ProgramFiles%\VRS*'],
        'delay': 2,
    },
    {
        'name': 'Z1 Dashboard',
        'process': 'Z1Dashboard.exe',
        'registry': ['Z1 Dashboard'],
        'shortcut': ['Z1 Dashboard'],
        'exe': ['Z1Dashboard.exe'],
        'paths': [r'%ProgramFiles(x86)%\Z1Dashboard*', r'%ProgramFiles%\Z1Dashboard*'],
        'delay': 2,
    },
    {
        'name': 'Sim Racing Studio',
        'process': 'SimRacingStudio.exe',
        'registry': ['Sim Racing Studio'],
        'shortcut': ['Sim Racing Studio'],
        'exe': ['SimRacingStudio.exe'],
        'paths': [r'%ProgramFiles(x86)%\SimRacingStudio*', r'%ProgramFiles%\SimRacingStudio*'],
        'delay': 3,
    },
    {
        'name': 'Cold Tires',
        'process': 'cold-tires.exe',
        'shortcut': ['Cold Tires', 'cold-tires'],
        'exe': ['cold-tires.exe'],
        'paths': [r'%USERPROFILE%\cold-tires\dist', r'%USERPROFILE%\cold-tires'],
        'delay': 1,
    },
    {
        'name': 'Grid Check',
        'process': 'grid-check.exe',
        'shortcut': ['Grid Check', 'grid-check'],
        'exe': ['grid-check.exe'],
        'paths': [r'%USERPROFILE%\grid-check\dist', r'%USERPROFILE%\grid-check'],
        'delay': 1,
    },
    {
        # PyInstaller build, so the exe is CamelCase while the repo is hyphenated.
        'name': 'Track Temp Overlay',
        'process': 'TrackTempOverlay.exe',
        'shortcut': ['Track Temp Overlay', 'track-temp-overlay'],
        'exe': ['TrackTempOverlay.exe'],
        'paths': [r'%USERPROFILE%\track-temp-overlay\dist', r'%USERPROFILE%\track-temp-overlay'],
        'delay': 1,
    },
    {
        'name': 'Discord',
        'process': 'Discord.exe',
        'registry': ['Discord'],
        'shortcut': ['Discord'],
        'exe': ['Update.exe'],   # Discord's launcher stub
        'paths': [r'%LOCALAPPDATA%\Discord'],
        'args': '--processStart Discord.exe',
        'delay': 4,
        'enabled': False,        # off by default — plenty of people run it already
    },
    {
        'name': 'iRacing',
        'process': 'iRacingUI.exe',
        'registry': ['iRacing'],
        'shortcut': ['iRacing'],
        'exe': ['iRacingUI.exe'],
        'paths': [r'%ProgramFiles(x86)%\iRacing', r'%ProgramFiles%\iRacing',
                  r'%LOCALAPPDATA%\Programs\iRacing*'],
        'delay': 0,
    },
]
