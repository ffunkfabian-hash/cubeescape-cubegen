import AppKit
import SceneKit
import simd

/// The 3D view: one generated model (OBJ + MTL, Y up, front towards +Z like Blender's exporter), floor, lights,
/// camera presets and a turntable. Offscreen snapshots for the tests (`--snapshot`).
final class ModelScene: NSObject {
    let scene = SCNScene()
    let cameraNode = SCNNode()
    private let turntableNode = SCNNode()   // spins
    private let modelNode = SCNNode()       // the loaded model, centred on the floor
    private let floorNode = SCNNode()
    private(set) var size = SIMD3<Float>(1, 1, 1)
    private(set) var loadedPath: String?
    private var view = "Iso"

    static let views = ["Iso", "Vorne", "Seite", "Oben"]
    static let icons = ["Iso": "view_iso", "Vorne": "view_front", "Seite": "view_side", "Oben": "view_top"]

    override init() {
        super.init()
        scene.background.contents = NSColor(calibratedRed: 0.11, green: 0.12, blue: 0.14, alpha: 1)
        let cam = SCNCamera()
        cam.fieldOfView = 30
        cam.zNear = 0.01
        cam.zFar = 500
        cameraNode.camera = cam
        scene.rootNode.addChildNode(cameraNode)
        scene.rootNode.addChildNode(turntableNode)
        turntableNode.addChildNode(modelNode)

        let floor = SCNFloor()
        floor.reflectivity = 0.04
        let m = SCNMaterial()
        m.diffuse.contents = NSColor(calibratedWhite: 0.2, alpha: 1)
        m.lightingModel = .lambert
        floor.materials = [m]
        floorNode.geometry = floor
        scene.rootNode.addChildNode(floorNode)

        let sun = SCNNode()
        sun.light = SCNLight()
        sun.light?.type = .directional
        sun.light?.intensity = 900
        sun.light?.castsShadow = true
        sun.light?.shadowMode = .deferred
        sun.light?.shadowColor = NSColor(calibratedWhite: 0, alpha: 0.45)
        sun.eulerAngles = SCNVector3(-0.9, 0.6, 0)
        scene.rootNode.addChildNode(sun)
        let fill = SCNNode()
        fill.light = SCNLight()
        fill.light?.type = .ambient
        fill.light?.intensity = 420
        scene.rootNode.addChildNode(fill)
        setView("Iso")
    }

    /// Replaces the shown model. Throws when the file can't be read.
    func load(obj path: String) throws {
        let loaded = try SCNScene(url: URL(fileURLWithPath: path), options: [.checkConsistency: false])
        for child in modelNode.childNodes { child.removeFromParentNode() }
        for child in loaded.rootNode.childNodes {
            // the OBJ writer marks the low detail level _LOD1: only LOD0 is shown, like the desktop window
            if child.name?.hasSuffix("_LOD1") == true { continue }
            modelNode.addChildNode(child)
        }
        let library = Self.readMTL(obj: path)
        modelNode.enumerateHierarchy { node, _ in
            node.geometry?.materials.forEach { Self.fixMaterial($0, library[$0.name ?? ""]) }
        }
        let (lo, hi) = modelNode.boundingBox
        let low = SIMD3<Float>(Float(lo.x), Float(lo.y), Float(lo.z))
        let high = SIMD3<Float>(Float(hi.x), Float(hi.y), Float(hi.z))
        size = simd_max(high - low, SIMD3(repeating: 0.05))
        // centre on the turntable axis, standing on the floor
        modelNode.simdPosition = SIMD3(-(low.x + high.x) / 2, -low.y, -(low.z + high.z) / 2)
        turntableNode.simdEulerAngles = .zero
        loadedPath = path
        setView(view)
    }

    /// One material of an MTL file: linear colours (like Unity's material values), an optional colour map.
    struct MTLMaterial {
        var diffuse: SIMD3<Double>?
        var emission: SIMD3<Double>?
        var map: String?
    }

    /// The MTL next to an OBJ (`mtllib`), read directly: ModelIO hands SceneKit altered colours (Hazard orange
    /// 0.17 green became 0.125, 0.010 blue 0.0002) and Blender's white ambient (`Ka 1 1 1`).
    static func readMTL(obj: String) -> [String: MTLMaterial] {
        guard let text = try? String(contentsOfFile: obj, encoding: .utf8),
              let line = text.split(separator: "\n").first(where: { $0.hasPrefix("mtllib ") }) else { return [:] }
        let folder = (obj as NSString).deletingLastPathComponent
        let mtl = (folder as NSString).appendingPathComponent(String(line.dropFirst(7)).trimmingCharacters(in: .whitespaces))
        guard let lib = try? String(contentsOfFile: mtl, encoding: .utf8) else { return [:] }
        var out: [String: MTLMaterial] = [:]
        var current: String?
        for raw in lib.split(separator: "\n") {
            let parts = raw.split(separator: " ").map(String.init)
            guard let key = parts.first else { continue }
            func rgb() -> SIMD3<Double>? {
                let v = parts.dropFirst().prefix(3).compactMap(Double.init)
                return v.count == 3 ? SIMD3(v[0], v[1], v[2]) : nil
            }
            switch key {
            case "newmtl": current = parts.dropFirst().joined(separator: " "); out[current!] = MTLMaterial()
            case "Kd": if let c = current { out[c]?.diffuse = rgb() }
            case "Ke": if let c = current { out[c]?.emission = rgb() }
            case "map_Kd": if let c = current { out[c]?.map = (folder as NSString).appendingPathComponent(parts.dropFirst().joined(separator: " ")) }
            default: break
            }
        }
        return out
    }

    /// Colours from the MTL converted to sRGB; the ambient takes the material's own colour; a little specular.
    static func fixMaterial(_ m: SCNMaterial, _ source: MTLMaterial?) {
        m.lightingModel = .blinn
        if let map = source?.map, let image = NSImage(contentsOfFile: map) {
            m.diffuse.contents = image
            m.ambient.contents = image
        } else if let kd = source?.diffuse {
            let c = srgb(kd)
            m.diffuse.contents = c
            m.ambient.contents = c
        }
        if let ke = source?.emission, ke.max() > 0.001 {
            m.emission.contents = srgb(ke)
        } else {
            m.emission.contents = NSColor.black
        }
        m.specular.contents = NSColor(calibratedWhite: 0.12, alpha: 1)
        m.shininess = 0.25
    }

    static func srgb(_ linear: SIMD3<Double>) -> NSColor {
        func f(_ v: Double) -> CGFloat {
            let x = max(0, min(1, v))
            return CGFloat(x <= 0.0031308 ? x * 12.92 : 1.055 * pow(x, 1 / 2.4) - 0.055)
        }
        return NSColor(srgbRed: f(linear.x), green: f(linear.y), blue: f(linear.z), alpha: 1)
    }

    func clear() {
        for child in modelNode.childNodes { child.removeFromParentNode() }
        loadedPath = nil
    }

    func setView(_ name: String) {
        view = name
        let radius = max(simd_length(size) * 0.5, 0.25)
        let distance = radius / Float(sin(Double(cameraNode.camera?.fieldOfView ?? 30) * .pi / 360)) * 1.15
        let target = SIMD3<Float>(0, size.y * 0.5, 0)
        var dir: SIMD3<Float>
        switch name {
        case "Vorne": dir = [0, 0.12, 1]
        case "Seite": dir = [1, 0.12, 0]
        case "Oben": dir = [0, 1, 0.001]
        default:  // like the icons: 33 degrees from the right, 31 up
            let az: Float = 33 * .pi / 180, el: Float = 31 * .pi / 180
            dir = [sin(az) * cos(el), sin(el), cos(az) * cos(el)]
        }
        cameraNode.simdPosition = target + simd_normalize(dir) * distance
        cameraNode.simdLook(at: target, up: SIMD3(0, 1, 0), localFront: SCNNode.simdLocalFront)
    }

    var showFloor: Bool {
        get { !floorNode.isHidden }
        set { floorNode.isHidden = !newValue }
    }

    var turntable = false {
        didSet {
            turntableNode.removeAllActions()
            if turntable {
                turntableNode.runAction(.repeatForever(.rotateBy(x: 0, y: .pi * 2, z: 0, duration: 12)))
            }
        }
    }

    func snapshot(size: CGSize) -> NSImage {
        let r = SCNRenderer(device: MTLCreateSystemDefaultDevice(), options: nil)
        r.scene = scene
        r.pointOfView = cameraNode
        return r.snapshot(atTime: 0, with: size, antialiasingMode: .multisampling4X)
    }
}

extension NSImage {
    func pngData() -> Data? {
        guard let tiff = tiffRepresentation, let rep = NSBitmapImageRep(data: tiff) else { return nil }
        return rep.representation(using: .png, properties: [:])
    }
}
