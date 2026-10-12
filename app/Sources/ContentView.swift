import AppKit
import SceneKit
import SwiftUI

/// UI icons drawn by ImageMagick (`app/make_icons.sh`, in the app's Resources); template images take the text colour.
struct UIIcon: View {
    let name: String
    var size: CGFloat = 16
    var template = true

    var body: some View {
        if let img = Bundle.main.image(forResource: name) {
            Image(nsImage: img).renderingMode(template ? .template : .original).resizable().scaledToFit()
                .frame(width: size, height: size)
        } else {
            Color.clear.frame(width: size, height: size)
        }
    }
}

/// German names for the catalog's categories and style options; a new one shows its own name until it gets one.
enum Names {
    static let categories = ["environment": "Umgebung", "industrial": "Industrie", "nature": "Natur",
                             "props": "Requisiten", "puzzle": "Rätsel", "robots": "Roboter", "ruins": "Ruinen",
                             "tech": "Technik"]
    static let options = ["clutter": "Kleinkram", "damage": "Schaden", "detail": "Detail", "generation": "Generation",
                          "glow": "Leuchtfarbe", "material_style": "Material", "size": "Größe",
                          "warning": "Warnstreifen", "wear": "Abnutzung", "theme": "Thema", "snap": "Raster"]

    static func category(_ key: String) -> String { categories[key] ?? key }
    static func option(_ key: String) -> String {
        options[key] ?? key.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

struct SceneContainer: NSViewRepresentable {
    let scene: ModelScene

    func makeNSView(context: Context) -> SCNView {
        let v = SCNView()
        v.scene = scene.scene
        v.pointOfView = scene.cameraNode
        v.allowsCameraControl = true
        v.defaultCameraController.interactionMode = .orbitTurntable
        v.antialiasingMode = .multisampling4X
        v.rendersContinuously = true
        v.isPlaying = true
        return v
    }

    func updateNSView(_ nsView: SCNView, context: Context) {}
}

struct ContentView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        HSplitView {
            VStack(spacing: 0) {
                ZStack(alignment: .bottomLeading) {
                    SceneContainer(scene: model.scene)
                    overlay
                }
                Gallery(model: model)
                if model.showLog { LogView(lines: model.log) }
            }
            .frame(minWidth: 600)

            Sidebar(model: model)
                .frame(minWidth: 340, idealWidth: 380, maxWidth: 460)
        }
    }

    private var overlay: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                ForEach(ModelScene.views, id: \.self) { v in
                    Button { model.scene.setView(v) } label: { Label { Text(v) } icon: { UIIcon(name: ModelScene.icons[v] ?? "view_iso") } }
                }
                Divider().frame(height: 18)
                // symbols only (the names were cut off in a narrow window); the name is the tooltip
                Toggle(isOn: $model.turntable) { UIIcon(name: "action_turntable") }.toggleStyle(.button).help("Drehteller")
                Toggle(isOn: $model.showFloor) { UIIcon(name: "action_floor") }.toggleStyle(.button).help("Boden")
                Toggle(isOn: $model.showLog) { UIIcon(name: "action_log") }.toggleStyle(.button).help("Protokoll")
                Button { model.screenshot() } label: { UIIcon(name: "action_screenshot") }
                    .help("Screenshot …").disabled(model.selected == nil)
            }
            if let m = model.selected {
                Text(modelLine(m)).font(.caption).monospacedDigit()
            }
            if model.running {
                HStack {
                    if model.progress.total > 0 {
                        ProgressView(value: Double(model.progress.done), total: Double(model.progress.total))
                            .frame(width: 220)
                        Text("\(model.progress.done)/\(model.progress.total)").font(.caption).monospacedDigit()
                    } else {
                        ProgressView().controlSize(.small)
                    }
                }
            }
            if !model.status.isEmpty { Text(model.status).font(.caption).foregroundStyle(.secondary) }
        }
        .padding(10)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10))
        .padding(12)
    }

    private func modelLine(_ m: Manifest.Model) -> String {
        var parts = [m.name, m.type]
        if let t = m.stats?.triangles { parts.append("\(t) Tris") }
        if let d = m.stats?.dimensions_m, d.count == 3 {
            parts.append(String(format: "%.2f × %.2f × %.2f m", d[0], d[1], d[2]))
        }
        return parts.joined(separator: " · ")
    }
}

/// The generated models of the last run as icons; a click shows one in 3D.
struct Gallery: View {
    @ObservedObject var model: AppModel

    var body: some View {
        if !model.models.isEmpty {
            ScrollView(.horizontal) {
                LazyHStack(spacing: 6) {
                    ForEach(model.models) { m in
                        Button { model.selected = m } label: {
                            VStack(spacing: 2) {
                                thumbnail(m).frame(width: 72, height: 72)
                                Text(m.name).font(.system(size: 9)).lineLimit(1).frame(width: 80)
                            }
                            .padding(4)
                            .background(model.selected == m ? Color.accentColor.opacity(0.35) : .clear,
                                        in: RoundedRectangle(cornerRadius: 6))
                        }
                        .buttonStyle(.plain)
                        .help(m.type)
                    }
                }
                .padding(6)
            }
            .frame(height: 104)
            .background(Color(nsColor: .underPageBackgroundColor))
        }
    }

    @ViewBuilder private func thumbnail(_ m: Manifest.Model) -> some View {
        if let url = model.url(m.icon ?? m.preview), let img = NSImage(contentsOf: url) {
            Image(nsImage: img).resizable().scaledToFit()
        } else {
            UIIcon(name: "cube", size: 48, template: false).opacity(0.6)
        }
    }
}

struct LogView: View {
    let lines: [String]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 1) {
                    ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                        Text(line).font(.system(size: 11, design: .monospaced)).textSelection(.enabled).id(i)
                    }
                }
                .padding(6)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .onChange(of: lines.count) { n in proxy.scrollTo(n - 1, anchor: .bottom) }
        }
        .frame(height: 150)
        .background(Color(nsColor: .textBackgroundColor))
    }
}

struct Sidebar: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Text("Cubegen").font(.title2.bold())
                        Spacer()
                        Text("Version \(model.catalog?.version ?? "…")").foregroundStyle(.secondary)
                    }
                    if !model.catalogError.isEmpty {
                        VStack(alignment: .leading) {
                            Text(model.catalogError).foregroundStyle(.red)
                            Button("Erneut versuchen") { model.loadCatalog() }
                        }
                    }
                    source
                    build
                    textures
                    style
                    options
                }
                .padding(14)
            }
            Divider()
            actions.padding(12)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    // MARK: sections

    private var source: some View {
        section("Modelltypen") {
            HStack {
                TextField("Filter", text: $model.filter).textFieldStyle(.roundedBorder)
                Button("Alle") { model.selectVisible(true) }
                Button("Keine") { model.selectVisible(false) }
            }
            Text("\(model.settings.types.count) ausgewählt").font(.caption).foregroundStyle(.secondary)
            ScrollView {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(model.categories, id: \.self) { category in
                        let names = model.types(in: category)
                        if !names.isEmpty {
                            DisclosureGroup(isExpanded: Binding(
                                get: { model.expanded.contains(category) || !model.filter.isEmpty },
                                set: { open in
                                    if open { model.expanded.insert(category) } else { model.expanded.remove(category) }
                                })) {
                                ForEach(names, id: \.self) { name in
                                    Toggle(name, isOn: Binding(get: { model.isSelected(name) },
                                                               set: { _ in model.toggle(name) }))
                                        .frame(maxWidth: .infinity, alignment: .leading)  // not centred per name length
                                        .help(model.catalog?.types[name]?.description ?? "")
                                }
                            } label: {
                                Label { Text("\(Names.category(category)) (\(names.count))") } icon: { UIIcon(name: "category_" + category) }
                            }
                        }
                    }
                }
            }
            .frame(height: 210)
            Picker("Familie", selection: $model.settings.family) {
                Text("– keine –").tag("")
                ForEach((model.catalog?.families ?? [:]).keys.sorted(), id: \.self) { Text($0).tag($0) }
            }
            .help(model.catalog?.families[model.settings.family]?.description ?? "Ein ganzes Bau-Kit statt einzelner Typen")
            HStack {
                TextField("Rezept (optional)", text: $model.settings.recipe).textFieldStyle(.roundedBorder)
                Button("Datei …") { model.chooseRecipe() }
            }
        }
    }

    private var build: some View {
        section("Build") {
            HStack {
                TextField("Seed (leer = zufällig)", text: $model.settings.seed).textFieldStyle(.roundedBorder)
                Stepper("Varianten: \(model.settings.count)", value: $model.settings.count, in: 1...50)
            }
            HStack {
                TextField("Ausgabeordner", text: $model.settings.output).textFieldStyle(.roundedBorder)
                Button("Ordner …") { model.chooseOutput() }
                Button { model.revealOutput() } label: { UIIcon(name: "action_folder") }.help("Im Finder zeigen")
            }
        }
    }

    private var textures: some View {
        section("Texturen") {
            Picker("Texturen", selection: $model.settings.textures) {
                ForEach(textureChoices, id: \.value) { Text($0.label).tag($0.value) }
            }
            if model.settings.textures != "none" {
                Picker("Größe (px)", selection: $model.settings.textureSize) {
                    ForEach(textureSizes, id: \.self) { Text($0).tag($0) }
                }.pickerStyle(.segmented)
            }
            if model.settings.textures == "palette" {
                Picker("Farbpalette", selection: $model.settings.palette) {
                    Text("Standard").tag("")
                    ForEach((model.catalog?.paletteNames ?? []).filter { $0 != "standard" }, id: \.self) { name in
                        Text(name).tag(name).help(model.catalog?.palettes[name]?.description ?? "")
                    }
                }
            }
            if model.settings.textures == "baked" {
                Picker("Backen auf", selection: $model.settings.bakeDevice) {
                    Text("Automatisch").tag("auto")
                    Text("CPU").tag("cpu")
                    Text("GPU").tag("gpu")
                }.pickerStyle(.segmented)
                .help("Automatisch: GPU ab 1024 px, darunter ist die CPU schneller")
            }
            Text("Texturen brauchen ImageMagick; ohne Textur bleiben die Spielmaterialien M_….")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    /// Every choice option of the catalog (theme, size, damage, wear …) - no list of our own.
    private var style: some View {
        let skip: Set<String> = ["textures", "texture_size", "palette"]
        let options = (model.catalog?.options ?? [:]).filter { !skip.contains($0.key) && !($0.value.choices ?? []).isEmpty }
        return section("Stil") {
            ForEach(options.keys.sorted(), id: \.self) { name in
                Picker(Names.option(name), selection: Binding(
                    get: { model.settings.style[name] ?? "" }, set: { model.settings.style[name] = $0 })) {
                    Text("aus dem Seed").tag("")
                    ForEach(options[name]?.choices ?? [], id: \.self) { Text($0).tag($0) }
                }
                .help(options[name]?.help ?? "")
            }
        }
    }

    private var options: some View {
        section("Optionen") {
            Toggle("Ähnliche Varianten überspringen", isOn: $model.settings.unique)
            Toggle("Variantenset (gleiche Außenmaße)", isOn: $model.settings.variantSet)
                .help("Alle Varianten eines Typs behalten die Außenmaße der ersten und unterscheiden sich innen – "
                      + "Teile, die nebeneinander stehen, ohne sich zu wiederholen")
            Toggle("Strikte Qualitätsprüfung", isOn: $model.settings.strict)
            Toggle("Alles neu bauen", isOn: $model.settings.force)
            Toggle("Nur OBJ (ohne Blender)", isOn: $model.settings.noBlender)
            Picker("Blender-Prozesse", selection: $model.settings.jobs) {
                Text("Automatisch").tag(0)
                ForEach([1, 2, 3, 4, 6, 8], id: \.self) { Text("\($0)").tag($0) }
            }
            .help("Automatisch: bis Kerne − 1, nur so viele, wie sich lohnen")
        }
    }

    private var actions: some View {
        HStack {
            Button { model.start(validate: true) } label: {
                Label { Text("Vorab prüfen") } icon: { UIIcon(name: "action_validate") }
            }
            .disabled(model.running)
            Spacer()
            if model.running {
                Button { model.stop() } label: { Label { Text("Abbrechen") } icon: { UIIcon(name: "action_stop") } }
                    .keyboardShortcut(".", modifiers: .command)
            }
            Button { model.start(validate: false) } label: {
                Label { Text("Assets erzeugen") } icon: { UIIcon(name: "action_generate") }
            }
                .keyboardShortcut("r", modifiers: .command)
                .buttonStyle(.borderedProminent)
                .disabled(model.running)
        }
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased()).font(.caption.bold()).foregroundStyle(.secondary)
            content()
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.6), in: RoundedRectangle(cornerRadius: 8))
    }
}
