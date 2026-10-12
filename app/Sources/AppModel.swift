import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

/// State of the app: catalog, settings (kept between launches), the running cubegen process and its results.
@MainActor
final class AppModel: ObservableObject {
    let scene = ModelScene()

    @Published var catalog: Catalog?
    @Published var catalogError = ""
    @Published var settings = GenerateSettings() { didSet { save() } }
    @Published var filter = ""
    @Published var expanded: Set<String> = []   // open categories of the type list
    @Published var log: [String] = []
    @Published var running = false
    @Published var progress: (done: Int, total: Int) = (0, 0)
    @Published var status = ""
    @Published var models: [Manifest.Model] = []
    @Published var selected: Manifest.Model? { didSet { show(selected) } }
    @Published var outputFolder: URL?
    @Published var turntable = false { didSet { scene.turntable = turntable } }
    @Published var showFloor = true { didSet { scene.showFloor = showFloor } }
    @Published var showLog = true
    @Published var exitCode: Int32?   // of the last run

    private var process: Process?
    private var reportPath: String?
    private var partial = ""
    private let persist: Bool
    private static let settingsKey = "settings.v1"

    /// ``persist``: read and keep the settings between launches (false for the command line test modes - they must
    /// not change what the user set up).
    init(persist: Bool = true) {
        self.persist = persist
        if persist, let data = UserDefaults.standard.data(forKey: Self.settingsKey),
           let saved = try? JSONDecoder().decode(GenerateSettings.self, from: data) {
            settings = saved
        }
        if settings.output.isEmpty {
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
            settings.output = docs?.appendingPathComponent("Cubegen/output").path ?? NSHomeDirectory() + "/Cubegen"
        }
        loadCatalog()
        let out = URL(fileURLWithPath: (settings.output as NSString).expandingTildeInPath)
        if persist, FileManager.default.fileExists(atPath: out.appendingPathComponent("manifest.json").path) {
            loadResults(out)  // the last run is still there: show it
        }
    }

    private func save() {
        guard persist else { return }
        if let data = try? JSONEncoder().encode(settings) { UserDefaults.standard.set(data, forKey: Self.settingsKey) }
    }

    func loadCatalog() {
        catalogError = ""
        DispatchQueue.global(qos: .userInitiated).async {
            let result = Result { try Generator.catalog() }
            DispatchQueue.main.async {
                switch result {
                case .success(let c): self.catalog = c
                case .failure(let e): self.catalogError = e.localizedDescription
                }
            }
        }
    }

    // MARK: - types

    var categories: [String] {
        Array(Set(catalog?.types.values.map(\.category) ?? [])).sorted { Names.category($0) < Names.category($1) }
    }

    func types(in category: String) -> [String] {
        let needle = filter.lowercased().trimmingCharacters(in: .whitespaces)
        return (catalog?.types ?? [:]).filter { name, info in
            info.category == category && (needle.isEmpty || name.contains(needle)
                                          || info.description.lowercased().contains(needle))
        }.keys.sorted()
    }

    func isSelected(_ type: String) -> Bool { settings.types.contains(type) }

    func toggle(_ type: String) {
        if let i = settings.types.firstIndex(of: type) { settings.types.remove(at: i) } else { settings.types.append(type) }
        settings.types.sort()
    }

    func selectVisible(_ on: Bool) {
        let visible = Set(categories.flatMap { types(in: $0) })
        var chosen = Set(settings.types)
        if on { chosen.formUnion(visible) } else { chosen.subtract(visible) }
        settings.types = chosen.sorted()
    }

    // MARK: - run

    func start(validate: Bool) {
        guard !running else { return }
        var report: String?
        if validate {
            report = FileManager.default.temporaryDirectory.appendingPathComponent("cubegen-validation-\(UUID().uuidString).json").path
        }
        let args: [String]
        do {
            args = try settings.arguments(validate: validate, report: report, catalog: catalog)
        } catch {
            status = error.localizedDescription
            return
        }
        guard let python = Generator.python() else {
            status = GeneratorError.noPython.localizedDescription
            return
        }
        let out = URL(fileURLWithPath: (settings.output as NSString).expandingTildeInPath)
        try? FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
        reportPath = report
        log = ["$ cubegen " + args.joined(separator: " ")]
        progress = (0, 0)
        status = validate ? "Prüfe …" : "Erzeuge …"
        running = true
        partial = ""

        let p = Process()
        p.executableURL = URL(fileURLWithPath: python)
        p.arguments = ["-m", "cubegen"] + args
        p.environment = Generator.environment()
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        // finish only when both arrived: the end of the output (empty read) and the end of the process - reading
        // the rest in the termination handler raced with a running readability handler (lines lost or reordered)
        let done = DispatchGroup()
        done.enter()
        done.enter()
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty {
                handle.readabilityHandler = nil
                done.leave()
                return
            }
            let text = String(decoding: data, as: UTF8.self)
            DispatchQueue.main.async { self?.receive(text) }
        }
        p.terminationHandler = { _ in done.leave() }
        done.notify(queue: .main) { [weak self] in
            self?.finish(code: p.terminationStatus, validate: validate, output: out)  // the process has exited here
        }
        do {
            try p.run()
            process = p
        } catch {
            running = false
            status = "Start fehlgeschlagen: \(error.localizedDescription)"
        }
    }

    func stop() {
        process?.terminate()
        status = "Abgebrochen"
    }

    private func receive(_ text: String) {
        partial += text
        var lines = partial.components(separatedBy: "\n")
        partial = lines.removeLast()
        for line in lines where !line.isEmpty {
            log.append(line)
            track(line)
        }
        if log.count > 4000 { log.removeFirst(log.count - 4000) }
    }

    /// Progress from the log: "Blender: … - N asset(s)" sets the total, every "…: N tris" is one model done.
    private func track(_ line: String) {
        if let r = line.range(of: #" - (\d+) asset\(s\)"#, options: .regularExpression) {
            let digits = line[r].filter(\.isNumber)
            progress = (0, Int(digits) ?? 0)
        } else if line.range(of: #": \d+ tris"#, options: .regularExpression) != nil {
            progress.done += 1
        }
    }

    private func finish(code: Int32, validate: Bool, output: URL) {
        if !partial.isEmpty { log.append(partial); partial = "" }
        running = false
        process = nil
        exitCode = code
        if code != 0 {
            status = status == "Abgebrochen" ? status : "Beendet mit Status \(code)"
        } else {
            status = "Fertig"
        }
        if validate {
            showReport()
        } else if code == 0 {
            loadResults(output)
        }
    }

    private func showReport() {
        guard let path = reportPath else { return }
        defer { try? FileManager.default.removeItem(atPath: path); reportPath = nil }
        guard let data = FileManager.default.contents(atPath: path),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let assets = json["assets"] as? [[String: Any]] else { return }
        let ranked = assets.sorted {
            let a = ($0["quality_score"] as? Double) ?? 0, b = ($1["quality_score"] as? Double) ?? 0
            if a != b { return a > b }
            return (($0["type"] as? String) ?? "", ($0["name"] as? String) ?? "")
                < (($1["type"] as? String) ?? "", ($1["name"] as? String) ?? "")
        }
        guard !ranked.isEmpty else { return }
        log.append("Qualitätsranking (höchste Punktzahl zuerst):")
        for row in ranked {
            let quality = row["quality"] as? [String: Any]
            let similar = (row["similar_to"] as? String).map { " — ähnlich zu \($0)" } ?? ""
            log.append("  \(row["type"] ?? "?") #\(row["quality_rank"] ?? "?") \(row["name"] ?? "?"): "
                       + "\(row["quality_score"] ?? 0)/100, \(row["severity"] ?? "?"), "
                       + "\(quality?["triangles"] ?? "?") Tris\(similar)")
        }
    }

    func loadResults(_ folder: URL) {
        do {
            let manifest = try Manifest.load(folder)
            outputFolder = folder
            models = manifest.models
            selected = models.first
            if let t = manifest.timings?.seconds, !t.isEmpty {
                let total = t.values.reduce(0, +)
                status = "\(models.count) Modell(e) · \(String(format: "%.1f", total)) s"
            }
        } catch {
            log.append("Manifest konnte nicht geladen werden: \(error.localizedDescription)")
        }
    }

    func url(_ relative: String?) -> URL? {
        guard let relative, let folder = outputFolder else { return nil }
        return relative.hasPrefix("/") ? URL(fileURLWithPath: relative) : folder.appendingPathComponent(relative)
    }

    private func show(_ model: Manifest.Model?) {
        guard let model, let obj = url(model.files["obj"]) else {
            scene.clear()
            return
        }
        do {
            try scene.load(obj: obj.path)
        } catch {
            status = "3D-Modell konnte nicht geladen werden: \(error.localizedDescription)"
        }
    }

    // MARK: - files

    func chooseOutput() {
        let p = NSOpenPanel()
        p.canChooseDirectories = true
        p.canChooseFiles = false
        p.canCreateDirectories = true
        if p.runModal() == .OK, let url = p.url { settings.output = url.path }
    }

    func chooseRecipe() {
        let p = NSOpenPanel()
        p.allowedContentTypes = [.json]
        if p.runModal() == .OK, let url = p.url { settings.recipe = url.path }
    }

    func revealOutput() {
        let url = outputFolder ?? URL(fileURLWithPath: (settings.output as NSString).expandingTildeInPath)
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    func screenshot() {
        let p = NSSavePanel()
        p.allowedContentTypes = [.png]
        p.nameFieldStringValue = "\(selected?.name ?? "Modell").png"
        guard p.runModal() == .OK, let url = p.url else { return }
        do {
            try scene.snapshot(size: CGSize(width: 1600, height: 1600)).pngData()?.write(to: url)
            status = "Screenshot gespeichert: \(url.lastPathComponent)"
        } catch { status = "Fehler: \(error.localizedDescription)" }
    }
}
