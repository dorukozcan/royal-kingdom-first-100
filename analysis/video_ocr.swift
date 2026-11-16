// Extracts frames from a screen recording at a fixed rate and runs Apple's on-device OCR on each one.
// Output: one JSON object per line: {"t": seconds, "lines": [{"s": text, "x": midX, "y": midY from top, "c": confidence}]}
// Build: swiftc -O video_ocr.swift -o video_ocr    Run: ./video_ocr <video> <out.jsonl> [frames per second, default 1]
import AVFoundation
import Foundation
import Vision

func ocr(_ image: CGImage) -> [[String: Any]] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["tr-TR", "en-US"]
    try? VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    return (request.results ?? []).compactMap { o in
        guard let c = o.topCandidates(1).first else { return nil }
        let round3 = { (v: CGFloat) in (Double(v) * 1000).rounded() / 1000 }
        return ["s": c.string, "x": round3(o.boundingBox.midX), "y": round3(1 - o.boundingBox.midY), "c": Double(c.confidence)]
    }
}

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: video_ocr <video> <out.jsonl> [fps]"); exit(2) }
let fps = args.count > 3 ? (Double(args[3]) ?? 1) : 1
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let duration = CMTimeGetSeconds(asset.duration)
guard duration.isFinite, duration > 0 else { print("cannot read video: \(args[1])"); exit(1) }
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.maximumSize = CGSize(width: 1400, height: 1400)  // long side 1400 px: enough for the panels, fast to read
generator.requestedTimeToleranceBefore = CMTime(seconds: 0.2, preferredTimescale: 600)
generator.requestedTimeToleranceAfter = CMTime(seconds: 0.2, preferredTimescale: 600)
FileManager.default.createFile(atPath: args[2], contents: nil)
guard let out = FileHandle(forWritingAtPath: args[2]) else { print("cannot write \(args[2])"); exit(1) }
let started = Date()
var t = 0.0, frames = 0, failed = 0
while t < duration {
    if let image = try? generator.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        let row: [String: Any] = ["t": t, "lines": ocr(image)]
        if let data = try? JSONSerialization.data(withJSONObject: row) { out.write(data); out.write(Data("\n".utf8)) }
        frames += 1
    } else { failed += 1 }
    t += 1 / fps
}
let took = Date().timeIntervalSince(started)
print(String(format: "video %.0f s, %d frames read, %d failed, took %.1f s (%.0f ms per frame)", duration, frames, failed, took, took * 1000 / Double(max(frames, 1))))
