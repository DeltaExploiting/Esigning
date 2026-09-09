from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('LiveContainer')

# Keep XSign visible/launchable as an already-signed guest. LiveContainer patches
# guest executables before launch, so XSign uses no-resign + JIT and defaults to
# multitasking.
model = root / 'LiveContainerSwiftUI/Models/LCAppModel.swift'
s = model.read_text(encoding='utf-8')
marker = '        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified\n'
patch = '''        self.uiIsMultitaskModeSpecificed = appInfo.multitaskSpecified

        // XSign is supplied as an already-signed guest. LiveContainer patches the
        // guest executable, so this build keeps XSign in no-resign/JIT mode and
        // defaults it to multitasking.
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

# Add a built-in XSign entry to Sources. Its Import button opens the Files picker
# for the user's authorized signed XSign IPA, avoiding a fake/broken download URL.
src = root / 'LiveContainerSwiftUI/Views/LCAltStoreSourcesView.swift'
s = src.read_text(encoding='utf-8')
if 'XSign — Signed IPA' in s:
    print('XSign sources patch already present')
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

        let version = AltStoreSourceAppVersion(
            version: "3.6.6",
            buildVersion: nil,
            releaseDate: nil,
            localizedDescription: "Signed XSign IPA. Import your authorized signed IPA; LiveContainer will keep it as the guest and launch it in multitask mode.",
            downloadURL: URL(fileURLWithPath: "/__builtin_xsign.ipa"),
            size: 20_228_529
        )
        let app = AltStoreSourceApp(
            name: "XSign — Signed IPA",
            bundleIdentifier: "co.xsign",
            developerName: "XSign",
            subtitle: "Signed guest • Multitask",
            description: "Import the signed XSign 3.6.6 IPA you already own. This build is configured for LiveContainer multitasking and JIT.",
            iconURL: nil,
            tintColor: nil,
            screenshots: [],
            versions: [version],
            latestVersion: version,
            isBeta: false
        )
        let source = AltStoreSource(
            name: "ESign Built-in Apps",
            identifier: "com.deltaexploiting.esigning.builtin",
            subtitle: "Signed guest apps for this LiveContainer build",
            description: "Built-in app entries for authorized local IPA imports.",
            iconURL: nil,
            headerURL: nil,
            tintColor: Color.blue,
            website: nil,
            apps: [app]
        )
        sources.insert(SourceItem(url: url, isLoading: false, source: source), at: 0)
    }
'''
if old not in s:
    raise SystemExit('sources init marker not found')
s = s.replace(old, new, 1)

old = '    @State private var isViewAppeared = false\n'
new = '    @State private var isViewAppeared = false\n    @State private var showXSignImporter = false\n'
if old not in s:
    raise SystemExit('state marker not found')
s = s.replace(old, new, 1)

old = '''        .searchable(text: $searchContext.query, placement: .navigationBarDrawer(displayMode: .always))

        .onAppear {
'''
new = '''        .searchable(text: $searchContext.query, placement: .navigationBarDrawer(displayMode: .always))
        .fileImporter(
            isPresented: $showXSignImporter,
            allowedContentTypes: [UTType.data, UTType.archive],
            allowsMultipleSelection: false
        ) { result in
            handleXSignImport(result)
        }

        .onAppear {
'''
if old not in s:
    raise SystemExit('searchable marker not found')
s = s.replace(old, new, 1)

old = '''    @MainActor
    private func install(app: AltStoreSourceApp) {
        guard let downloadURL = app.latestVersion?.downloadURL else {
            errorMessage = "lc.sources.error.missingDownload".loc
            return
        }
'''
new = '''    @MainActor
    private func install(app: AltStoreSourceApp) {
        if app.bundleIdentifier == "co.xsign" {
            showXSignImporter = true
            return
        }
        guard let downloadURL = app.latestVersion?.downloadURL else {
            errorMessage = "lc.sources.error.missingDownload".loc
            return
        }
'''
if old not in s:
    raise SystemExit('install marker not found')
s = s.replace(old, new, 1)

old = '''    private func toggleExpansion(for id: URL) {
'''
new = '''    private func handleXSignImport(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            let accessed = url.startAccessingSecurityScopedResource()
            defer { if accessed { url.stopAccessingSecurityScopedResource() } }
            let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("XSign-3.6.6-signed.ipa")
            do {
                if FileManager.default.fileExists(atPath: tempURL.path) {
                    try FileManager.default.removeItem(at: tempURL)
                }
                try FileManager.default.copyItem(at: url, to: tempURL)
                DataManager.shared.model.selectedTab = .apps
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                    NotificationCenter.default.post(name: NSNotification.InstallAppNotification, object: ["url": tempURL])
                }
            } catch {
                errorMessage = error.localizedDescription
            }
        case .failure(let error):
            if (error as NSError).code != NSUserCancelledError {
                errorMessage = error.localizedDescription
            }
        }
    }

    private func toggleExpansion(for id: URL) {
'''
if old not in s:
    raise SystemExit('toggle marker not found')
s = s.replace(old, new, 1)

old = '''                Text("lc.common.install".loc)
                    .bold()
'''
new = '''                Text(app.bundleIdentifier == "co.xsign" ? "Import" : "lc.common.install".loc)
                    .bold()
'''
if old not in s:
    raise SystemExit('button label marker not found')
s = s.replace(old, new, 1)

src.write_text(s, encoding='utf-8')
print('Patched XSign source entry + local IPA importer + multitask config')
