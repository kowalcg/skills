// ocr.swift — Apple Vision OCR for slide images. No dependencies beyond macOS.
// Usage: ocr <image> [<image> ...]   → JSON {path: [lines top-to-bottom]} on stdout
// Compiled on first use by extract_slides.py (swiftc -O ocr.swift -o ocr).
import Foundation
import Vision
import AppKit

var result: [String: [String]] = [:]
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        result[path] = []; continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.minimumTextHeight = 0.006   // keep the tiny captions slides are full of
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    let obs = (req.results ?? []).sorted {
        // reading order: top-to-bottom, then left-to-right (Vision y is bottom-up)
        abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.01
            ? $0.boundingBox.midY > $1.boundingBox.midY
            : $0.boundingBox.minX < $1.boundingBox.minX
    }
    result[path] = obs.compactMap { $0.topCandidates(1).first?.string }
}
let data = try! JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted])
FileHandle.standardOutput.write(data)
