import Foundation

/// Runs the bundled cubegen package (`python3 -m cubegen`): finds Python, reads the catalog, builds the command line
/// the same way as the desktop window (`cubegen/gui.py`), streams the output of a run and reads its manifest.
enum Generator {
    /// Python 3.9+ - a Finder-started app does not see the shell's PATH, so the usual places are tried in order.
    static let pythonCandidates = [
        "/opt/homebrew/bin/python3", "/usr/local/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3", "/usr/bin/python3",
    ]

    static func python() -> String? {
        if let env = ProcessInfo.processInfo.environment["CUBEGEN_PYTHON"], FileManager.default.isExecutableFile(atPath: env) {
            return env
        }
        return pythonCandidates.first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    /// The folder that contains the `cubegen` package: inside the app (`Resources/python`) or, for a build run
    /// from the repository, `$CUBEGEN_ROOT`.
    static func packageRoot() -> URL? {
        if let env = ProcessInfo.processInfo.environment["CUBEGEN_ROOT"] {
            let url = URL(fileURLWithPath: env)
            if FileManager.default.fileExists(atPath: url.appendingPathComponent("cubegen/__init__.py").path) { return url }
        }
        if let res = Bundle.main.resourceURL?.appendingPathComponent("python"),
           FileManager.default.fileExists(atPath: res.appendingPathComponent("cubegen/__init__.py").path) {
            return res
        }
        return nil
    }

    static func environment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        if let root = packageRoot() { env["PYTHONPATH"] = root.path + (env["PYTHONPATH"].map { ":" + $0 } ?? "") }
        env["PYTHONUNBUFFERED"] = "1"  // the log appears line by line
        // Homebrew's ImageMagick for a Finder-started app (cubegen also looks there itself)
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (env["PATH"] ?? "/usr/bin:/bin")
        return env
    }

    /// `python3 -m cubegen <args>` to completion (catalog, version, doctor).
    static func runToEnd(_ args: [String]) throws -> (code: Int32, out: Data, err: String) {
        guard let py = python() else { throw GeneratorError.noPython }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: py)
        p.arguments = ["-m", "cubegen"] + args
        p.environment = environment()
        let out = Pipe(), err = Pipe()
        p.standardOutput = out
        p.standardError = err
        try p.run()
        let data = out.fileHandleForReading.readDataToEndOfFile()
        let errData = err.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return (p.terminationStatus, data, String(decoding: errData, as: UTF8.self))
    }

    static func catalog() throws -> Catalog {
        let r = try runToEnd(["catalog"])
        guard r.code == 0 else { throw GeneratorError.failed("cubegen catalog: \(r.err)") }
        return try JSONDecoder().decode(Catalog.self, from: r.out)
    }
}

enum GeneratorError: LocalizedError {
    case noPython, failed(String), invalid(String)

    var errorDescription: String? {
        switch self {
        case .noPython: return "Python 3 nicht gefunden (Homebrew, python.org oder Xcode-Kommandozeilenwerkzeuge)."
        case .failed(let s): return s
        case .invalid(let s): return s
        }
    }
}

// MARK: - catalog (`cubegen catalog`, one source with the game's front ends)

struct Catalog: Decodable {
    struct TypeInfo: Decodable {
        let category: String
        let description: String
        let experimental: Bool
    }

    struct Option: Decodable {
        let choices: [String]?
        let flag: String
        let help: String?
        let kind: String
    }

    struct Family: Decodable {
        let description: String
    }

    struct Palette: Decodable {
        let description: String
        let material: String
    }

    struct Paint: Decodable {
        let label: String
        let glow: String
    }

    let version: String
    let types: [String: TypeInfo]
    let options: [String: Option]
    let palettes: [String: Palette]
    let families: [String: Family]
    let paints: [String: Paint]?

    var paletteNames: [String] { palettes.keys.sorted() }
}

// MARK: - settings -> command line (mirrors cubegen/gui.py `command`)

/// Texture modes as in the desktop window (label, value of --textures).
let textureChoices: [(label: String, value: String)] = [
    ("Keine (einfarbige Spielmaterialien)", "none"), ("Kacheln (tiled)", "tiled"),
    ("Kacheln + Gebrauchsspuren (baked)", "baked"), ("Farbpalette (palette)", "palette"),
]
let textureSizes = ["256", "512", "1024", "2048"]

struct GenerateSettings: Codable, Equatable {
    var types: [String] = []
    var family = ""            // a model family's kit instead of single types
    var recipe = ""            // a JSON recipe instead of both
    var seed = ""              // empty = random
    var count = 4
    var output = ""
    var textures = "none"
    var textureSize = "512"
    var palette = ""
    var style: [String: String] = [:]   // catalog option name -> value ("" = from the seed)
    var unique = true
    var variantSet = false     // --set: the variants share variant 0's outline, differ inside
    var paint = ""             // paint scheme (cubegen catalog "paints"); implies a baked atlas
    var strict = false
    var force = false
    var noBlender = false
    var jobs = 0               // 0 = auto
    var bakeDevice = "auto"

    init() {}

    /// Missing keys keep their defaults: settings saved by an older app (or a test fixture) still load.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = GenerateSettings()
        types = try c.decodeIfPresent([String].self, forKey: .types) ?? d.types
        family = try c.decodeIfPresent(String.self, forKey: .family) ?? d.family
        recipe = try c.decodeIfPresent(String.self, forKey: .recipe) ?? d.recipe
        seed = try c.decodeIfPresent(String.self, forKey: .seed) ?? d.seed
        count = try c.decodeIfPresent(Int.self, forKey: .count) ?? d.count
        output = try c.decodeIfPresent(String.self, forKey: .output) ?? d.output
        textures = try c.decodeIfPresent(String.self, forKey: .textures) ?? d.textures
        textureSize = try c.decodeIfPresent(String.self, forKey: .textureSize) ?? d.textureSize
        palette = try c.decodeIfPresent(String.self, forKey: .palette) ?? d.palette
        style = try c.decodeIfPresent([String: String].self, forKey: .style) ?? d.style
        unique = try c.decodeIfPresent(Bool.self, forKey: .unique) ?? d.unique
        variantSet = try c.decodeIfPresent(Bool.self, forKey: .variantSet) ?? d.variantSet
        paint = try c.decodeIfPresent(String.self, forKey: .paint) ?? d.paint
        strict = try c.decodeIfPresent(Bool.self, forKey: .strict) ?? d.strict
        force = try c.decodeIfPresent(Bool.self, forKey: .force) ?? d.force
        noBlender = try c.decodeIfPresent(Bool.self, forKey: .noBlender) ?? d.noBlender
        jobs = try c.decodeIfPresent(Int.self, forKey: .jobs) ?? d.jobs
        bakeDevice = try c.decodeIfPresent(String.self, forKey: .bakeDevice) ?? d.bakeDevice
    }

    /// Arguments after `python3 -m cubegen` - the same as the desktop window builds them, plus family, style,
    /// --jobs and --bake-device.
    func arguments(validate: Bool, report: String? = nil, catalog: Catalog? = nil) throws -> [String] {
        let recipe = self.recipe.trimmingCharacters(in: .whitespaces)
        let family = self.family.trimmingCharacters(in: .whitespaces)
        if recipe.isEmpty && family.isEmpty && types.isEmpty {
            throw GeneratorError.invalid("Wähle mindestens einen Modelltyp, eine Familie oder ein Rezept aus.")
        }
        if count < 1 { throw GeneratorError.invalid("Die Variantenanzahl muss mindestens 1 sein.") }
        let output = self.output.trimmingCharacters(in: .whitespaces)
        if output.isEmpty { throw GeneratorError.invalid("Bitte gib einen Ausgabeordner an.") }

        var args = ["generate"]
        if !recipe.isEmpty {
            args += ["--recipe", recipe]
        } else if !family.isEmpty {
            args += ["--family", family]
        } else {
            args += ["--types", types.joined(separator: ","), "--count", String(count)]
        }
        let seed = self.seed.trimmingCharacters(in: .whitespaces)
        if !seed.isEmpty { args += ["--seed", seed] }
        args += ["--out", (output as NSString).standardizingPath]
        if paint.isEmpty {
            args += try textureArguments()
        } else {  // --paint implies --textures baked; the size still applies
            args += ["--paint", paint]
            if let n = Int(textureSize.trimmingCharacters(in: .whitespaces)) { args += ["--texture-size", String(n)] }
        }
        for name in style.keys.sorted() {
            guard let value = style[name], !value.isEmpty else { continue }
            let flag = catalog?.options[name]?.flag ?? "--" + name.replacingOccurrences(of: "_", with: "-")
            args += [flag, value]
        }
        if variantSet && recipe.isEmpty && family.isEmpty { args.append("--set") }
        if unique { args.append("--unique") }
        if strict { args.append("--strict") }
        if force && !validate { args.append("--force") }
        if noBlender && !validate {
            args.append("--no-blender")
        } else if !validate {
            args += ["--formats", "fbx,obj"]  // OBJ for the app's 3D view
        }
        if jobs > 0 && !validate { args += ["--jobs", String(jobs)] }
        if textures == "baked" && bakeDevice != "auto" && !validate { args += ["--bake-device", bakeDevice] }
        if validate, let report { args += ["--validate-only", "--report", report] }
        return args
    }

    /// --textures / --texture-size / --palette like `gui.texture_args`.
    func textureArguments() throws -> [String] {
        guard textureChoices.contains(where: { $0.value == textures }) else {
            throw GeneratorError.invalid("Unbekannte Texturart: \(textures)")
        }
        if textures == "none" { return [] }
        var args = ["--textures", textures]
        let size = textureSize.trimmingCharacters(in: .whitespaces)
        if !size.isEmpty {
            guard let n = Int(size), n >= 16 else {
                throw GeneratorError.invalid("Die Texturgröße muss eine ganze Zahl in Pixeln sein (mindestens 16).")
            }
            args += ["--texture-size", String(n)]
        }
        let palette = self.palette.trimmingCharacters(in: .whitespaces)
        if textures == "palette" && !palette.isEmpty { args += ["--palette", palette] }
        return args
    }
}

// MARK: - manifest of a finished run

struct Manifest: Decodable {
    struct Model: Decodable, Identifiable, Hashable {
        let name: String
        let type: String
        let files: [String: String]
        let preview: String?
        let icon: String?
        let stats: Stats?

        var id: String { name }
    }

    struct Stats: Decodable, Hashable {
        let triangles: Int?
        let dimensions_m: [Double]?
    }

    struct Timings: Decodable {
        let seconds: [String: Double]?
    }

    let version: String?
    let models: [Model]
    let timings: Timings?

    static func load(_ folder: URL) throws -> Manifest {
        try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: folder.appendingPathComponent("manifest.json")))
    }
}
