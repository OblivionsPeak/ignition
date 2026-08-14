"""Finding, launching and stopping Windows apps.

This is where the fiddly Windows bits live, isolated from the UI:

  .lnk resolution    most sim apps only exist as Start Menu shortcuts, so a
                     shortcut has to be resolved to a real target before we can
                     match a process name against it. Uses win32com when it's
                     available, otherwise one batched PowerShell call.
  launching          ShellExecuteW handles .exe and .lnk alike and takes a
                     working directory, which several apps (CrewChief) need.
  elevation          the same call with the "runas" verb raises the UAC prompt.
  already-running    tasklist, matched on process name, so a second GO doesn't
                     spawn duplicates.
  shutdown           taskkill politely first, forcefully only if it won't go.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- subprocess helpers

def _quiet():
    """Keep console windows from flashing up in a windowed app."""
    if os.name != 'nt':
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {'startupinfo': si, 'creationflags': 0x08000000}  # CREATE_NO_WINDOW

def _run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, **_quiet())
        return p.returncode, p.stdout.decode('utf-8', 'replace')
    except Exception:
        return 1, ''

def expand(p):
    return os.path.expandvars(os.path.expanduser(p))

# ---------------------------------------------------------------- shortcut resolution

START_MENUS = [
    r'%APPDATA%\Microsoft\Windows\Start Menu\Programs',
    r'%ProgramData%\Microsoft\Windows\Start Menu\Programs',
    r'%USERPROFILE%\Desktop',
    r'%PUBLIC%\Desktop',
]

def _resolve_lnk_win32com(paths):
    """Fast path: resolve shortcuts in-process. Only if pywin32 is installed."""
    try:
        import win32com.client
    except Exception:
        return None
    try:
        shell = win32com.client.Dispatch('WScript.Shell')
    except Exception:
        return None
    out = []
    for p in paths:
        try:
            s = shell.CreateShortCut(str(p))
            out.append({'Name': Path(p).stem, 'Target': s.TargetPath or '',
                        'Args': s.Arguments or '', 'Work': s.WorkingDirectory or '',
                        'Link': str(p)})
        except Exception:
            continue
    return out

def _resolve_lnk_powershell(paths):
    """Fallback: one PowerShell call for every shortcut at once. Writes JSON to
    a temp file rather than stdout — piping through PowerShell 5.1's console
    encoding mangles non-ASCII app names."""
    if not paths:
        return []
    fd, listfile = tempfile.mkstemp(suffix='.txt'); os.close(fd)
    fd, outfile = tempfile.mkstemp(suffix='.json'); os.close(fd)
    try:
        Path(listfile).write_text('\n'.join(str(p) for p in paths), encoding='utf-8')
        ps = (
            "$ErrorActionPreference='SilentlyContinue';"
            f"$paths = Get-Content -LiteralPath '{listfile}' -Encoding UTF8;"
            "$sh = New-Object -ComObject WScript.Shell;"
            "$r = foreach ($p in $paths) { "
            "  if (-not $p) { continue }"
            "  $s = $sh.CreateShortcut($p);"
            "  [PSCustomObject]@{ Name=[IO.Path]::GetFileNameWithoutExtension($p);"
            "    Target=$s.TargetPath; Args=$s.Arguments; Work=$s.WorkingDirectory; Link=$p } };"
            f"ConvertTo-Json -InputObject @($r) -Depth 3 | Out-File -LiteralPath '{outfile}' -Encoding utf8"
        )
        _run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], timeout=120)
        raw = Path(outfile).read_text(encoding='utf-8-sig', errors='replace').strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []
    finally:
        for f in (listfile, outfile):
            try:
                os.unlink(f)
            except Exception:
                pass

def scan_shortcuts():
    """Every Start Menu / Desktop shortcut, resolved to its target."""
    links = []
    for d in START_MENUS:
        root = Path(expand(d))
        if root.is_dir():
            try:
                links.extend(root.rglob('*.lnk'))
            except Exception:
                continue
    links = links[:1500]   # a runaway Start Menu shouldn't hang the scan
    return _resolve_lnk_win32com(links) or _resolve_lnk_powershell(links)

def resolve_one(path):
    """Resolve a single shortcut the user picked. Non-.lnk passes straight through."""
    path = str(path)
    if not path.lower().endswith('.lnk'):
        return {'Target': path, 'Args': '', 'Work': str(Path(path).parent)}
    got = _resolve_lnk_win32com([path]) or _resolve_lnk_powershell([path])
    if got and got[0].get('Target'):
        return got[0]
    # Unresolvable — launch the shortcut itself; the shell knows what to do
    return {'Target': path, 'Args': '', 'Work': ''}

# ---------------------------------------------------------------- registry

def scan_registry():
    """DisplayName -> install location, from both 32- and 64-bit uninstall keys."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
    ]
    for hive, sub in roots:
        try:
            key = winreg.OpenKey(hive, sub)
        except OSError:
            continue
        try:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, name) as k:
                        def val(v):
                            try:
                                return winreg.QueryValueEx(k, v)[0]
                            except OSError:
                                return ''
                        disp = val('DisplayName')
                        if disp:
                            out.append({'name': disp, 'location': val('InstallLocation'),
                                        'icon': val('DisplayIcon')})
                except OSError:
                    continue
        finally:
            key.Close()
    return out

# ---------------------------------------------------------------- detection

def _find_exe_under(patterns, names):
    for pat in patterns:
        for base in glob.glob(expand(pat)):
            for n in names:
                hit = Path(base) / n
                if hit.is_file():
                    return hit
                try:
                    for deep in Path(base).rglob(n):
                        if deep.is_file():
                            return deep
                except Exception:
                    continue
    return None

def detect(entry, shortcuts=None, registry=None):
    """Locate one catalog entry. Returns a dict ready to become an app row, or
    None when it isn't installed."""
    shortcuts = shortcuts if shortcuts is not None else []
    registry = registry if registry is not None else []
    low = lambda s: (s or '').lower()

    # 1. registry install location
    for want in entry.get('registry', []):
        for r in registry:
            if low(want) in low(r['name']):
                loc = r.get('location') or ''
                if loc and Path(expand(loc)).is_dir():
                    hit = _find_exe_under([loc], entry.get('exe', []))
                    if hit:
                        return _row(entry, hit, '')
                icon = (r.get('icon') or '').split(',')[0].strip('"')
                if icon and icon.lower().endswith('.exe') and Path(expand(icon)).is_file():
                    return _row(entry, Path(expand(icon)), '')

    # 2. Start Menu shortcut — the most reliable signal, and the reason a
    #    wrong guess at an exe name in the catalog isn't fatal
    for want in entry.get('shortcut', []):
        for s in shortcuts:
            if low(want) in low(s.get('Name')):
                target = s.get('Target') or s.get('Link') or ''
                if target and Path(target).exists():
                    return _row(entry, Path(target), s.get('Args', ''), s.get('Work', ''))

    # 3. known install paths
    hit = _find_exe_under(entry.get('paths', []), entry.get('exe', []))
    if hit:
        return _row(entry, hit, '')
    return None

def _row(entry, target, args='', work=''):
    target = Path(target)
    # The file we actually found beats the catalog's guess at an exe name —
    # several apps ship under a name nobody would predict (SimPro Manager is
    # simpro.exe). Keep the catalog name too: launcher stubs like Discord's
    # Update.exe exit immediately and the real process has a different name,
    # so "is it running" has to match any of them.
    names = [target.name]
    for extra in process_list(entry.get('process', '')):
        if extra.lower() not in {n.lower() for n in names}:
            names.append(extra)
    return {
        'name': entry['name'],
        'path': str(target),
        'args': entry.get('args', '') or args or '',
        'workdir': work or str(target.parent),
        'process': ', '.join(names),
        'delay': entry.get('delay', 2),
        'admin': entry.get('admin', False),
        'skip_if_running': True,
        'enabled': entry.get('enabled', True),
    }

def detect_all(catalog, progress=None):
    if progress:
        progress('Reading installed programs…')
    registry = scan_registry()
    if progress:
        progress('Resolving Start Menu shortcuts…')
    shortcuts = scan_shortcuts()
    rows = []
    for entry in catalog:
        if progress:
            progress(f'Looking for {entry["name"]}…')
        got = detect(entry, shortcuts, registry)
        if got:
            rows.append(got)
    return rows

# ---------------------------------------------------------------- processes

def running_processes():
    """Lowercased set of running image names."""
    code, out = _run(['tasklist', '/fo', 'csv', '/nh'])
    names = set()
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('"'):
            names.add(line.split('","')[0].strip('"').lower())
    return names

def process_list(process):
    """Process fields hold one or more comma-separated image names."""
    return [p.strip() for p in (process or '').replace(';', ',').split(',') if p.strip()]

def is_running(process, snapshot=None):
    """True if *any* of the named processes is up."""
    names = process_list(process)
    if not names:
        return False
    snap = snapshot if snapshot is not None else running_processes()
    return any(n.lower() in snap for n in names)

def stop(process, force_after=True):
    """Ask nicely (WM_CLOSE), then insist. Returns True if they're all gone."""
    names = process_list(process)
    if not names:
        return False
    for n in names:
        _run(['taskkill', '/IM', n], timeout=15)
    if not is_running(process):
        return True
    if force_after:
        for n in names:
            _run(['taskkill', '/IM', n, '/F', '/T'], timeout=15)
    return not is_running(process)

# ---------------------------------------------------------------- launching

def launch(path, args='', workdir='', admin=False):
    """ShellExecuteW: one code path for .exe and .lnk, honours the working
    directory, and raises UAC when admin is set. Returns (ok, message)."""
    import ctypes
    path = expand(path)
    if not Path(path).exists():
        return False, 'not found'
    workdir = expand(workdir) if workdir else str(Path(path).parent)
    if not Path(workdir).is_dir():
        workdir = str(Path(path).parent)
    verb = 'runas' if admin else 'open'
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, verb, path, args or None, workdir, 1)
    except Exception as e:
        return False, str(e)
    if rc > 32:
        return True, ''
    return False, {5: 'blocked (declined elevation?)', 2: 'not found',
                   3: 'bad path', 31: 'no app associated'}.get(rc, f'ShellExecute error {rc}')
