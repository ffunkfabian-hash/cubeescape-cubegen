import AppKit
import SwiftUI

// MARK: - catalog data of the paint schemes (`cubegen catalog`: paint_schemes, paint_fields)

/// One built-in scheme as the catalog gives it: label, glow, a colour per game material, amounts (0…1) and the other
/// colours (wear, grime, dust, moss, edge glow, crystal) - the keys come from the catalog, not from a list here.
struct PaintSchemeData: Decodable {
    var label: String
    var glow: String
    var colors: [String: String]
    var amounts: [String: Double] = [:]
    var tones: [String: String] = [:]

    private struct Key: CodingKey {
        var stringValue: String
        var intValue: Int? { nil }
        init(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { return nil }
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Key.self)
        label = try c.decode(String.self, forKey: Key(stringValue: "label"))
        glow = try c.decode(String.self, forKey: Key(stringValue: "glow"))
        colors = try c.decode([String: String].self, forKey: Key(stringValue: "colors"))
        for key in c.allKeys where !["label", "glow", "colors"].contains(key.stringValue) {
            if let number = try? c.decode(Double.self, forKey: key) {
                amounts[key.stringValue] = number
            } else if let text = try? c.decode(String.self, forKey: key) {
                tones[key.stringValue] = text
            }
        }
    }
}

struct PaintFields: Decodable {
    let painted: [String]
    let amounts: [String]
    let colors: [String]
    let glow: [String]
}

// MARK: - an own scheme (the file for --paint-file)

struct OwnPaint: Equatable {
    var name = "mein_thema"
    var base = "industrial"
    var label = "Mein Thema"
    var glow = "cyan"
    var colors: [String: String] = [:]
    var amounts: [String: Double] = [:]
    var tones: [String: String] = [:]

    /// Every value from the built-in scheme ``base`` (name and label stay).
    mutating func reset(to base: String, catalog: Catalog?) {
        guard let scheme = catalog?.paint_schemes?[base] else { return }
        self.base = base
        glow = scheme.glow
        colors = scheme.colors
        amounts = scheme.amounts
        tones = scheme.tones
    }

    /// A scheme file: the values of its base first, then what the file sets (like `paint.load_scheme`).
    static func load(_ url: URL, catalog: Catalog?) throws -> OwnPaint {
        let data = try Data(contentsOf: url)
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw GeneratorError.invalid("Ein Anstrich ist ein JSON-Objekt.")
        }
        var paint = OwnPaint()
        paint.reset(to: json["base"] as? String ?? "industrial", catalog: catalog)
        paint.name = json["name"] as? String ?? url.deletingPathExtension().lastPathComponent.lowercased()
        paint.label = json["label"] as? String ?? paint.name.capitalized
        if let glow = json["glow"] as? String { paint.glow = glow }
        for (key, value) in json["colors"] as? [String: String] ?? [:] { paint.colors[key] = value }
        for (key, value) in json {
            // a JSON 0 or 1 bridges to Bool too (`value is Bool`) - only a real true/false is no amount
            if let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() {
                paint.amounts[key] = number.doubleValue
            }
            if let text = value as? String, text.hasPrefix("#") { paint.tones[key] = text }
        }
        return paint
    }

    /// The file `cubegen generate --paint-file` reads: name, base and every value (amounts to three places).
    func json() throws -> Data {
        var object: [String: Any] = ["name": name, "base": base, "label": label, "glow": glow, "colors": colors]
        for (key, value) in amounts { object[key] = (value * 1000).rounded() / 1000 }
        for (key, value) in tones { object[key] = value }
        return try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
    }

    /// Letters, digits and _ (like `paint.load_scheme`), never a built-in name.
    func problem(catalog: Catalog?) -> String? {
        let allowed = CharacterSet.lowercaseLetters.union(.decimalDigits).union(CharacterSet(charactersIn: "_"))
        if name.isEmpty || name.unicodeScalars.contains(where: { !allowed.contains($0) }) {
            return "Name: nur Kleinbuchstaben, Ziffern und _."
        }
        if catalog?.paint_schemes?[name] != nil { return "„\(name)“ ist ein eingebautes Thema – bitte ein eigener Name." }
        return nil
    }
}

/// sRGB hex <-> SwiftUI colour.
enum Hex {
    static func color(_ hex: String) -> Color {
        let digits = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        guard digits.count == 6, let value = Int(digits, radix: 16) else { return .gray }
        return Color(.sRGB, red: Double((value >> 16) & 0xff) / 255, green: Double((value >> 8) & 0xff) / 255,
                     blue: Double(value & 0xff) / 255)
    }

    static func string(_ color: Color) -> String {
        guard let c = NSColor(color).usingColorSpace(.sRGB) else { return "#808080" }
        func byte(_ v: CGFloat) -> Int { Int((min(max(v, 0), 1) * 255).rounded()) }
        return String(format: "#%02x%02x%02x", byte(c.redComponent), byte(c.greenComponent), byte(c.blueComponent))
    }
}

/// German names of the scheme keys; a new key shows its own name until it gets one.
enum PaintNames {
    static let names = [
        "M_Ground": "Grund / Boden", "M_Wall": "Wand", "M_Platform": "Plattform", "M_HazardOrange": "Akzent",
        "M_RobotBody": "Verkleidung hell", "M_RobotDark": "Verkleidung dunkel", "M_Metal": "Metall",
        "M_Warning": "Warnfarbe", "M_PortalPanel": "Portalplatte",
        "edge_light": "Kantenlicht", "wear": "Abnutzung", "grime": "Schmutz", "rising_grime": "Schmutz von unten",
        "dust": "Staub / Schnee", "moss": "Bewuchs", "edge_glow": "Kantenleuchten", "roughness": "Rauheit",
        "metal": "Metallanteil",
        "wear_color": "Abnutzung", "grime_color": "Schmutz", "dust_color": "Staub / Schnee", "moss_color": "Bewuchs",
        "edge_glow_color": "Kantenleuchten", "crystal_color": "Kristalle",
        "cyan": "Cyan", "red": "Rot", "orange": "Orange",
    ]

    static func name(_ key: String) -> String { names[key] ?? key }
}

// MARK: - editor window

struct PaintEditor: View {
    @ObservedObject var model: AppModel

    private var fields: PaintFields? { model.catalog?.paint_fields }

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    identity
                    group("Farben je Spielmaterial") {
                        ForEach(fields?.painted ?? [], id: \.self) { colorRow($0, in: \.colors) }
                    }
                    group("Spuren und Licht") {
                        ForEach(fields?.colors ?? [], id: \.self) { colorRow($0, in: \.tones) }
                        Picker("Leuchtfarbe", selection: $model.ownPaint.glow) {
                            ForEach(fields?.glow ?? [], id: \.self) { Text(PaintNames.name($0)).tag($0) }
                        }
                        .pickerStyle(.segmented)
                    }
                    group("Mengen") {
                        ForEach(fields?.amounts ?? [], id: \.self) { amountRow($0) }
                    }
                }
                .padding(14)
            }
            .frame(width: 420)
            preview
        }
        .frame(width: 960, height: 660)
        .background(Color(nsColor: .windowBackgroundColor))  // also offscreen (test snapshots), not only as a sheet
    }

    private var identity: some View {
        group("Thema") {
            TextField("Name (Datei, z. B. rust_bucket)", text: $model.ownPaint.name).textFieldStyle(.roundedBorder)
            TextField("Anzeigename", text: $model.ownPaint.label).textFieldStyle(.roundedBorder)
            Picker("Grundthema", selection: Binding(get: { model.ownPaint.base },
                                                    set: { model.ownPaint.reset(to: $0, catalog: model.catalog) })) {
                ForEach((model.catalog?.paint_schemes ?? [:]).keys.sorted(), id: \.self) { name in
                    Text(model.catalog?.paint_schemes?[name]?.label ?? name).tag(name)
                }
            }
            .help("Setzt alle Farben und Mengen auf das gewählte eingebaute Thema")
            if let problem = model.ownPaint.problem(catalog: model.catalog) {
                Text(problem).font(.caption).foregroundStyle(.red)
            }
        }
    }

    private var preview: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("VORSCHAU").font(.caption.bold()).foregroundStyle(.secondary)
            ZStack {
                RoundedRectangle(cornerRadius: 8).fill(Color(nsColor: .controlBackgroundColor))
                if let image = model.paintPreview {
                    Image(nsImage: image).resizable().scaledToFit().padding(6)
                } else {
                    Text("Modulwand, Bodenplatte, Säule und Kiste in diesem Thema – einmal neutral gebacken, dann "
                         + "zusammengesetzt (etwa 10–20 s).")
                        .font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center).padding(30)
                }
                if model.paintPreviewRunning { ProgressView() }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            if !model.paintStatus.isEmpty {
                Text(model.paintStatus).font(.caption).foregroundStyle(.secondary).lineLimit(3)
            }
            HStack {
                Button("Vorschau erzeugen") { model.previewPaint() }
                    .keyboardShortcut("p", modifiers: .command)
                    .disabled(model.paintPreviewRunning || model.ownPaint.problem(catalog: model.catalog) != nil)
                Spacer()
                Button("Abbrechen") { model.editingPaint = false }
                    .keyboardShortcut(.cancelAction)
                Button("Speichern und verwenden …") { model.savePaint() }
                    .keyboardShortcut("s", modifiers: .command)
                    .buttonStyle(.borderedProminent)
                    .disabled(model.ownPaint.problem(catalog: model.catalog) != nil)
            }
        }
        .padding(14)
    }

    private func colorRow(_ key: String, in path: WritableKeyPath<OwnPaint, [String: String]>) -> some View {
        ColorPicker(selection: Binding(get: { Hex.color(model.ownPaint[keyPath: path][key] ?? "#808080") },
                                       set: { model.ownPaint[keyPath: path][key] = Hex.string($0) }),
                    supportsOpacity: false) {
            HStack {
                Text(PaintNames.name(key))
                Spacer()
                Text(model.ownPaint[keyPath: path][key] ?? "").font(.caption.monospaced()).foregroundStyle(.secondary)
            }
        }
        .help(key)
    }

    private func amountRow(_ key: String) -> some View {
        let value = Binding(get: { model.ownPaint.amounts[key] ?? 0 }, set: { model.ownPaint.amounts[key] = $0 })
        return HStack {
            Text(PaintNames.name(key)).frame(width: 140, alignment: .leading)
            Slider(value: value, in: 0...1)
            Text(String(format: "%.2f", value.wrappedValue)).font(.caption.monospacedDigit()).frame(width: 36)
        }
        .help(key)
    }

    private func group<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.caption.bold()).foregroundStyle(.secondary)
            content()
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.6), in: RoundedRectangle(cornerRadius: 8))
    }
}
