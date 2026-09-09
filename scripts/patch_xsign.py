from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('LiveContainer')

model = root / 'LiveContainerSwiftUI/Models/LCAppModel.swift'
s = model.read_text(encoding='utf-8')
marker = '        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified\n'
patch = '''        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified

        // XSign is already signed. LiveContainer patches guest executables before launch,
        // so keep the guest signature and use JIT for execution after patching.
        if appInfo.bundleIdentifier() == "co.xsign" {
            self.uiDontSign = true
            self.uiIsJITNeeded = true
            self.uiClassicMode = false
            self.uiIsMultitaskModeSpecificed = .yes
        }
'''
if 'appInfo.bundleIdentifier() == "co.xsign"' not in s:
    if marker not in s:
        raise SystemExit('LCAppModel marker not found')
    model.write_text(s.replace(marker, patch, 1), encoding='utf-8')

print('Configured co.xsign for no-resign + JIT + default multitask')
