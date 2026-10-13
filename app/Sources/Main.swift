import AppKit
import SwiftUI

/// Entry point. GUI by default; command line modes for the tests (`app/test_app.sh`), like the Robot Viewer:
///   Cubegen --version                                   app and bundled package version
///   Cubegen --catalog                                   reads `cubegen catalog` through the bundled package
///   Cubegen --print-args settings.json [--validate]     the command line the app would run (JSON array)
///   Cubegen --snapshot out.png --model X.obj [--view Iso|Vorne|Seite|Oben] [--size 800x800] [--no-floor]
///   Cubegen --run settings.json [--validate]            a whole run through the app's own process runner
///   Cubegen --ui-snapshot out.png [--results <output folder>] [--size 1470x956] [--light]
///                       [--expand <category>] [--select type,type]           the window, offscreen
///                       [--paint-editor [<scheme.json>]]                     the paint editor instead
///   Cubegen --paint-roundtrip <in.json | builtin name> <out.json>     an own scheme read and written by the editor
///   Cubegen --paint-preview <scheme.json> <out.png>                   the editor's preview run (button "Vorschau")
@main
enum Main {
    @MainActor static func main() {
        let args = CommandLine.arguments
        if args.contains("--version") { exit(CommandLine.version()) }
        if args.contains("--catalog") { exit(CommandLine.catalog()) }
        if let path = CommandLine.value(args, "--print-args") { exit(CommandLine.printArgs(path, validate: args.contains("--validate"))) }
        if let out = CommandLine.value(args, "--snapshot") { exit(CommandLine.snapshot(out: out, args: args)) }
        if let path = CommandLine.value(args, "--run") { exit(CommandLine.run(path, validate: args.contains("--validate"))) }
        if let out = CommandLine.value(args, "--ui-snapshot") { exit(CommandLine.uiSnapshot(out: out, args: args)) }
        if let source = CommandLine.value(args, "--paint-roundtrip") { exit(CommandLine.paintRoundtrip(source, args: args)) }
        if let source = CommandLine.value(args, "--paint-preview") { exit(CommandLine.paintPreview(source, args: args)) }
        CubegenApp.main()
    }
}

struct CubegenApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup("Cubegen – Cube Escape Model Generator") {
            ContentView(model: model)
                .frame(minWidth: 1100, minHeight: 760)
        }
        .windowStyle(.titleBar)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

extension CommandLine {
    static func value(_ args: [String], _ key: String) -> String? {
        guard let i = args.firstIndex(of: key), i + 1 < args.count else { return nil }
        return args[i + 1]
    }

    static func fail(_ message: String, _ code: Int32 = 1) -> Int32 {
        FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
        return code
    }

    static func version() -> Int32 {
        let app = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "dev"
        do {
            let r = try Generator.runToEnd(["--version"])
            print("Cubegen.app \(app), \(String(decoding: r.out, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines))")
            return r.code
        } catch { return fail("version: \(error.localizedDescription)") }
    }

    static func catalog() -> Int32 {
        do {
            let c = try Generator.catalog()
            print("catalog \(c.version): \(c.types.count) types, \(c.palettes.count) palettes, \(c.families.count) families, "
                  + "\(c.options.count) options")
            return 0
        } catch { return fail("catalog: \(error.localizedDescription)") }
    }

    static func printArgs(_ path: String, validate: Bool) -> Int32 {
        do {
            let settings = try JSONDecoder().decode(GenerateSettings.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
            let args = try settings.arguments(validate: validate, report: validate ? "REPORT" : nil)
            let data = try JSONSerialization.data(withJSONObject: args)
            print(String(decoding: data, as: UTF8.self))
            return 0
        } catch { return fail("print-args: \(error.localizedDescription)", 2) }
    }

    /// Generates (or validates) like the button does: start, stream the log, read the manifest.
    @MainActor static func run(_ path: String, validate: Bool) -> Int32 {
        let model = AppModel(persist: false)
        do {
            model.settings = try JSONDecoder().decode(GenerateSettings.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
        } catch { return fail("run: \(error.localizedDescription)", 2) }
        let deadline = Date().addingTimeInterval(30)
        while model.catalog == nil && model.catalogError.isEmpty && Date() < deadline {  // style flags need it
            RunLoop.main.run(until: Date().addingTimeInterval(0.05))
        }
        model.start(validate: validate)
        while model.running { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
        for line in model.log { print(line) }
        print("status: \(model.status)")
        print("models: \(model.models.count)" + (model.selected.map { ", shown: \($0.name)" } ?? ""))
        print("progress: \(model.progress.done)/\(model.progress.total)")
        return model.exitCode == 0 ? 0 : 1
    }

    /// The window drawn offscreen (catalog loaded, optionally the results of a run) - for checking the layout.
    @MainActor static func uiSnapshot(out: String, args: [String]) -> Int32 {
        let app = NSApplication.shared
        app.setActivationPolicy(.prohibited)
        let model = AppModel(persist: false)
        if let folder = value(args, "--results") { model.loadResults(URL(fileURLWithPath: folder)) }
        if let open = value(args, "--expand") { model.expanded.insert(open) }   // a category of the type list
        if let types = value(args, "--select") { model.settings.types = types.split(separator: ",").map(String.init) }
        let editor = args.contains("--paint-editor")
        let dims = (value(args, "--size") ?? (editor ? "960x660" : "1470x956")).split(separator: "x").compactMap { Double($0) }
        let size = CGSize(width: dims.first ?? 1470, height: dims.last ?? 956)
        let root: AnyView = editor ? AnyView(PaintEditor(model: model)) : AnyView(ContentView(model: model))
        let host = NSHostingView(rootView: root.frame(width: size.width, height: size.height))
        let window = NSWindow(contentRect: CGRect(origin: .zero, size: size), styleMask: [.borderless],
                              backing: .buffered, defer: false)
        window.appearance = NSAppearance(named: args.contains("--light") ? .aqua : .darkAqua)
        window.backgroundColor = .windowBackgroundColor
        window.contentView = host
        let deadline = Date().addingTimeInterval(20)
        while model.catalog == nil && model.catalogError.isEmpty && Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.05))
        }
        if editor {  // the editor opened on a scheme file (or Industrial)
            if let file = value(args, "--paint-editor"), !file.hasPrefix("--") { model.settings.paintFile = file }
            model.openPaintEditor()
        }
        RunLoop.main.run(until: Date().addingTimeInterval(0.5))  // let SwiftUI lay out the loaded catalog
        host.layoutSubtreeIfNeeded()
        guard let rep = host.bitmapImageRepForCachingDisplay(in: host.bounds) else { return fail("ui-snapshot: no bitmap") }
        host.cacheDisplay(in: host.bounds, to: rep)
        guard let png = rep.representation(using: .png, properties: [:]) else { return fail("ui-snapshot: no png") }
        do { try png.write(to: URL(fileURLWithPath: out)) } catch { return fail("ui-snapshot: \(error.localizedDescription)") }
        print("ui-snapshot \(out)" + (model.catalogError.isEmpty ? "" : " (catalog: \(model.catalogError))"))
        return model.catalog == nil ? 1 : 0
    }

    /// Reads a scheme file (or a built-in scheme's values) like the editor and writes it like the editor saves it.
    @MainActor static func paintRoundtrip(_ source: String, args: [String]) -> Int32 {
        guard let i = args.firstIndex(of: source), i + 1 < args.count else { return fail("paint-roundtrip: out.json fehlt", 2) }
        let model = AppModel(persist: false)
        let deadline = Date().addingTimeInterval(30)
        while model.catalog == nil && model.catalogError.isEmpty && Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.05))
        }
        guard model.catalog?.paint_schemes != nil else { return fail("paint-roundtrip: catalog without paint_schemes") }
        var paint = OwnPaint()
        if source.hasSuffix(".json") {
            do { paint = try OwnPaint.load(URL(fileURLWithPath: source), catalog: model.catalog) } catch {
                return fail("paint-roundtrip: \(error.localizedDescription)")
            }
        } else {
            paint.reset(to: source, catalog: model.catalog)
            paint.name = "roundtrip_\(source)"
        }
        if let problem = paint.problem(catalog: model.catalog) { return fail("paint-roundtrip: \(problem)") }
        do { try paint.json().write(to: URL(fileURLWithPath: args[i + 1])) } catch {
            return fail("paint-roundtrip: \(error.localizedDescription)")
        }
        print("paint-roundtrip \(paint.name) (base \(paint.base)): \(paint.colors.count) colours, "
              + "\(paint.amounts.count) amounts, \(paint.tones.count) tones")
        return 0
    }

    @MainActor static func paintPreview(_ source: String, args: [String]) -> Int32 {
        guard let i = args.firstIndex(of: source), i + 1 < args.count else { return fail("paint-preview: out.png fehlt", 2) }
        let model = AppModel(persist: false)
        let deadline = Date().addingTimeInterval(30)
        while model.catalog == nil && model.catalogError.isEmpty && Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.05))
        }
        model.settings.paintFile = source
        model.openPaintEditor()
        model.previewPaint()
        while model.paintPreviewRunning { RunLoop.main.run(until: Date().addingTimeInterval(0.1)) }
        guard let image = model.paintPreview, let tiff = image.tiffRepresentation,
              let png = NSBitmapImageRep(data: tiff)?.representation(using: .png, properties: [:]) else {
            return fail("paint-preview: \(model.paintStatus)")
        }
        do { try png.write(to: URL(fileURLWithPath: args[i + 1])) } catch {
            return fail("paint-preview: \(error.localizedDescription)")
        }
        print("paint-preview \(model.ownPaint.name) -> \(args[i + 1])")
        return 0
    }

    @MainActor static func snapshot(out: String, args: [String]) -> Int32 {
        guard let obj = value(args, "--model") else { return fail("snapshot: --model X.obj fehlt", 2) }
        let scene = ModelScene()
        do {
            try scene.load(obj: obj)
        } catch { return fail("snapshot: \(error.localizedDescription)") }
        scene.showFloor = !args.contains("--no-floor")
        scene.setView(value(args, "--view") ?? "Iso")
        let dims = (value(args, "--size") ?? "800x800").split(separator: "x").compactMap { Double($0) }
        let img = scene.snapshot(size: CGSize(width: dims.first ?? 800, height: dims.last ?? 800))
        do {
            try img.pngData()?.write(to: URL(fileURLWithPath: out))
        } catch { return fail("snapshot: \(error.localizedDescription)") }
        print("snapshot \(out)")
        return 0
    }
}
