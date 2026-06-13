// ocr.swift — 用 macOS 自带 Vision 框架对图片做 OCR(支持简体中文+英文),零第三方依赖。
// 用法: swift ocr.swift img1.jpg img2.jpg ...   (一个进程批量 OCR,避免每张重编译)
// 输出: 每张图先打印 "=== <路径> ===",再逐行打印识别到的文本。
import Vision
import AppKit
import Foundation

func ocr(_ path: String) {
    guard let img = NSImage(contentsOfFile: path),
          let tiff = img.tiffRepresentation,
          let bmp = NSBitmapImageRep(data: tiff),
          let cg = bmp.cgImage else {
        print("(无法读取图片)")
        return
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["zh-Hans", "en-US"]
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    if let obs = req.results as? [VNRecognizedTextObservation] {
        for o in obs {
            if let top = o.topCandidates(1).first {
                print(top.string)
            }
        }
    }
}

let paths = Array(CommandLine.arguments.dropFirst())
for p in paths {
    print("=== \(p) ===")
    ocr(p)
}
