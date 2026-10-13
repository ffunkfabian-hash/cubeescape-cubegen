// Apple Vision on the previews and icons of a cubegen run (macOS only; the Neural Engine does the work).
//   vision_check <input.json>    input: {"previews": [{"name", "type", "path"}], "icons": [{"name", "type", "path"}]}
// Prints JSON: {"pairs": [{"type", "a", "b", "distance"}], "icons": [{"name", "box": [x, y, w, h], "objects": n,
// "border": pixels}], "prints": n, "seconds": {...}} - "border": pixels on the icon's edge that differ from its corner
// (the model is cut off; the saliency boxes are too coarse for that).
// A checking aid (tools/vision_report.py): the values differ between Neural Engine, GPU and CPU, so they never decide
// which variants a run writes.
import AppKit
import Foundation
import Vision

struct Item: Codable {
    let name: String
    let type: String
    let path: String
}

struct Input: Codable {
    let previews: [Item]
    let icons: [Item]
}

func image(_ path: String) -> CGImage? {
    NSImage(contentsOfFile: path)?.cgImage(forProposedRect: nil, context: nil, hints: nil)
}

func featurePrint(_ path: String) -> VNFeaturePrintObservation? {
    guard let cg = image(path) else { return nil }
    let request = VNGenerateImageFeaturePrintRequest()
    try? VNImageRequestHandler(cgImage: cg).perform([request])
    return request.results?.first
}

/// Union of the salient objects (normalised, origin bottom left) and their count.
func salient(_ path: String) -> ([Double], Int)? {
    guard let cg = image(path) else { return nil }
    let request = VNGenerateAttentionBasedSaliencyImageRequest()
    try? VNImageRequestHandler(cgImage: cg).perform([request])
    guard let objects = request.results?.first?.salientObjects, !objects.isEmpty else { return ([0, 0, 0, 0], 0) }
    var box = objects[0].boundingBox
    for o in objects.dropFirst() { box = box.union(o.boundingBox) }
    return ([box.minX, box.minY, box.width, box.height].map { Double($0) }, objects.count)
}

/// Pixels on the outermost ring that differ from the top left corner (background) by more than 10 %.
func borderPixels(_ path: String) -> Int {
    guard let cg = image(path) else { return 0 }
    let w = cg.width, h = cg.height
    var data = [UInt8](repeating: 0, count: w * h * 4)
    guard let ctx = CGContext(data: &data, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return 0 }
    ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
    func px(_ x: Int, _ y: Int) -> [Int] { let i = (y * w + x) * 4; return (0..<4).map { Int(data[i + $0]) } }
    let bg = px(0, 0)
    var count = 0
    for x in 0..<w { for y in [0, h - 1] where zip(px(x, y), bg).contains(where: { abs($0 - $1) > 25 }) { count += 1 } }
    for y in 1..<(h - 1) { for x in [0, w - 1] where zip(px(x, y), bg).contains(where: { abs($0 - $1) > 25 }) { count += 1 } }
    return count
}

let args = CommandLine.arguments
guard args.count > 1, let data = FileManager.default.contents(atPath: args[1]),
      let input = try? JSONDecoder().decode(Input.self, from: data) else {
    FileHandle.standardError.write("usage: vision_check <input.json>\n".data(using: .utf8)!)
    exit(2)
}

var t0 = Date()
var prints: [String: VNFeaturePrintObservation] = [:]
for item in input.previews {
    if let p = featurePrint(item.path) { prints[item.name] = p }
}
let printSeconds = Date().timeIntervalSince(t0)

t0 = Date()
var pairs: [[String: Any]] = []
let byType = Dictionary(grouping: input.previews, by: \.type)
for (type, items) in byType {
    for i in 0..<items.count {
        for j in (i + 1)..<max(i + 1, items.count) {
            guard let a = prints[items[i].name], let b = prints[items[j].name] else { continue }
            var distance: Float = 0
            if (try? a.computeDistance(&distance, to: b)) != nil {
                pairs.append(["type": type, "a": items[i].name, "b": items[j].name, "distance": Double(distance)])
            }
        }
    }
}
let pairSeconds = Date().timeIntervalSince(t0)

t0 = Date()
var icons: [[String: Any]] = []
for item in input.icons {
    if let (box, count) = salient(item.path) {
        icons.append(["name": item.name, "type": item.type, "box": box, "objects": count,
                      "border": borderPixels(item.path)])
    }
}
let iconSeconds = Date().timeIntervalSince(t0)

let out: [String: Any] = ["pairs": pairs, "icons": icons, "prints": prints.count,
                          "seconds": ["prints": printSeconds, "pairs": pairSeconds, "icons": iconSeconds]]
let json = try JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
FileHandle.standardOutput.write(json)
