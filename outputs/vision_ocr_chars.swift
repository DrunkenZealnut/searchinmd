// vision_ocr_chars — Apple Vision 으로 이미지의 글자를 인식해 줄·글자 단위 좌표를 JSON 으로 낸다. 오프라인, macOS 내장 프레임워크만 쓴다.
//
//   swiftc -O -o vision_ocr_chars vision_ocr_chars.swift
//   ./vision_ocr_chars page1.png page2.png > out.json
//
// 출력: [{"path", "width", "height", "lines": [{"text", "conf", "box": [x0,y0,x1,y1], "chars": [{"c", "box"}]}]}]
//   box 는 픽셀 좌표(좌상단 원점). 글자 box 를 못 구하면 null (호출 쪽이 줄 box 로 대신한다). 실패한 이미지는 {"path", "error"}.
// highlight_pdf_occurrences.py 가 교과서 스캔본(텍스트 층 없음)의 글자 좌표를 얻으려고 빌드·호출한다.
import Foundation
import Vision
import AppKit

func pixelBox(_ b: CGRect, _ w: CGFloat, _ h: CGFloat) -> [Double] {
    // Vision 은 정규화 좌표(좌하단 원점) — 픽셀·좌상단 원점으로 뒤집는다
    return [Double(b.minX * w), Double((1 - b.maxY) * h), Double(b.maxX * w), Double((1 - b.minY) * h)]
}

func recognize(_ path: String) -> [String: Any] {
    guard let image = NSImage(contentsOfFile: path),
          let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        return ["path": path, "error": "image load failed"]
    }
    let w = CGFloat(cg.width), h = CGFloat(cg.height)
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ko-KR", "en-US"]
    request.usesLanguageCorrection = true
    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])
    } catch {
        return ["path": path, "error": "\(error)"]
    }
    var lines: [[String: Any]] = []
    for observation in request.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let text = candidate.string
        var chars: [[String: Any]] = []
        var index = text.startIndex
        while index < text.endIndex {
            let next = text.index(after: index)
            var box: Any = NSNull()
            if let r = try? candidate.boundingBox(for: index..<next) { box = pixelBox(r.boundingBox, w, h) }
            chars.append(["c": String(text[index..<next]), "box": box])
            index = next
        }
        lines.append(["text": text, "conf": Double(candidate.confidence), "box": pixelBox(observation.boundingBox, w, h), "chars": chars])
    }
    return ["path": path, "width": Int(w), "height": Int(h), "lines": lines]
}

let results = CommandLine.arguments.dropFirst().map(recognize)
let data = try JSONSerialization.data(withJSONObject: Array(results), options: [])
FileHandle.standardOutput.write(data)
