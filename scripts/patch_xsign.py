from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('LiveContainer')

# Keep the already-signed XSign guest in no-resign/JIT mode and make it default
# to LiveContainer's multitasking launcher.
model = root / 'LiveContainerSwiftUI/Models/LCAppModel.swift'
s = model.read_text(encoding='utf-8')
marker = '        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified\n'
patch = '''        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified

        // Bundled XSign is already signed. LiveContainer patches the guest
        // executable before launch, so keep its signature and use JIT.
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

# Automatically import the bundled IPA into the normal My Apps database on
# first launch. The standard installer owns the actual app-container layout.
apps = root / 'LiveContainerSwiftUI/Views/AppList/LCAppListView.swift'
s = apps.read_text(encoding='utf-8')

appear_marker = '''            .onAppear {
                if !didAppear {
                    onAppear()
                }
            }
'''
appear_patch = '''            .onAppear {
                if !didAppear {
                    onAppear()
                }
            }
            .task {
                await installBundledXSignIfNeeded()
            }
'''
if 'installBundledXSignIfNeeded()' not in s:
    if appear_marker not in s:
        raise SystemExit('LCAppListView appear marker not found')
    s = s.replace(appear_marker, appear_patch, 1)

method_marker = '''    var JITEnablingModal : some View {
'''
method_patch = '''    @MainActor
    private func installBundledXSignIfNeeded() async {
        let defaults = LCUtils.appGroupUserDefault
        let key = "DeltaBundledXSignImported"
        guard !defaults.bool(forKey: key) else { return }
        guard let ipaURL = Bundle.main.url(forResource: "XSign-3.6.6-signed", withExtension: "ipa") else { return }

        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("XSign-3.6.6-signed.ipa")
        do {
            if FileManager.default.fileExists(atPath: tempURL.path) {
                try FileManager.default.removeItem(at: tempURL)
            }
            try FileManager.default.copyItem(at: ipaURL, to: tempURL)
            await installFromUrl(urlStr: tempURL.absoluteString)
            defaults.set(true, forKey: key)
        } catch {
            // Leave the flag unset so a later launch can retry.
        }
    }

    var JITEnablingModal : some View {
'''
if 'private func installBundledXSignIfNeeded()' not in s:
    if method_marker not in s:
        raise SystemExit('LCAppListView method marker not found')
    s = s.replace(method_marker, method_patch, 1)

apps.write_text(s, encoding='utf-8')

# Also expose XSign in Sources as a fallback. If automatic import is skipped,
# the user can select the signed IPA manually from Files.
src = root / 'LiveContainerSwiftUI/Views/LCAltStoreSourcesView.swift'
s = src.read_text(encoding='utf-8')
if 'XSign — Signed IPA' in s:
    print('XSign source entry already present')
    raise SystemExit(0)

s = s.replace('import CryptoKit\n', 'import CryptoKit\nimport UniformTypeIdentifiers\n', 1)
old = '''    init() {
        loadStoredSources()
        Task {
            await refreshAllSources()
        }
    }
'''
new = '''    init() {
        loadStoredSources()
        addBundledXSignSource()
        Task {
            await refreshAllSources()
        }
    }

    private func addBundledXSignSource() {
        let url = URL(fileURLWithPath: "/__builtin_xsign_source.json")
        guard !sources.contains(where: { $0.url == url }) else { return }
        let version = AltStoreSourceAppVersion(version: "3.6.6", buildVersion: nil, releaseDate: nil, localizedDescription: "Signed XSign IPA bundled with this LiveContainer build.", downloadURL: URL(fileURLWithPath: "/__builtin_xsign.ipa"), size: 20_228_529)
        let app = AltStoreSourceApp(name: "XSign — Signed IPA", bundleIdentifier: "co.xsign", developerName: "XSign", subtitle: "Signed guest • Multitask", description: "Signed XSign 3.6.6 bundled with this LiveContainer build.", iconURL: nil, tintColor: nil, screenshots: [], versions: [version], latestVersion: version, isBeta: false)
        let source = AltStoreSource(name: "ESign Built-in Apps", identifier: "com.deltaexploiting.esigning.builtin", subtitle: "Bundled signed guest apps", description: "Apps bundled into this LiveContainer build.", iconURL: nil, headerURL: nil, tintColor: Color.blue, website: nil, apps: [app])
        sources.insert(SourceItem(url: url, isLoading: false, source: source), at: 0)
    }
'''
if old not in s:
    raise SystemExit('sources init marker not found')
s = s.replace(old, new, 1)

if 'showXSignImporter' not in s:
    state_marker = '    @State private var isViewAppeared = false\n'
    if state_marker not in s:
        raise SystemExit('source state marker not found')
    s = s.replace(state_marker, state_marker + '    @State private var showXSignImporter = false\n', 1)

install_marker = '''        guard let downloadURL = app.latestVersion?.downloadURL else {
'''
if 'if app.bundleIdentifier == "co.xsign"' not in s:
    if install_marker not in s:
        raise SystemExit('source install marker not found')
    s = s.replace(install_marker, '''        if app.bundleIdentifier == "co.xsign" {
            showXSignImporter = true
            return
        }
        guard let downloadURL = app.latestVersion?.downloadURL else {
''', 1)

search_marker = '''        .searchable(text: $searchContext.query, placement: .navigationBarDrawer(displayMode: .always))
'''
if '.fileImporter(isPresented: $showXSignImporter' not in s:
    if search_marker not in s:
        raise SystemExit('source searchable marker not found')
    s = s.replace(search_marker, '''        .searchable(text: $searchContext.query, placement: .navigationBarDrawer(displayMode: .always))
        .fileImporter(isPresented: $showXSignImporter, allowedContentTypes: [UTType.data, UTType.archive], allowsMultipleSelection: false) { result in
            if case .success(let urls) = result, let url = urls.first {
                let accessed = url.startAccessingSecurityScopedResource()
                defer { if accessed { url.stopAccessingSecurityScopedResource() } }
                let temp = FileManager.default.temporaryDirectory.appendingPathComponent("XSign-3.6.6-signed.ipa")
                do {
                    if FileManager.default.fileExists(atPath: temp.path) { try FileManager.default.removeItem(at: temp) }
                    try FileManager.default.copyItem(at: url, to: temp)
                    DataManager.shared.model.selectedTab = .apps
                    NotificationCenter.default.post(name: NSNotification.InstallAppNotification, object: ["url": temp])
                } catch { }
            }
        }
''', 1)

src.write_text(s, encoding='utf-8')
print('Patched bundled XSign My Apps auto-import and multitask configuration')
