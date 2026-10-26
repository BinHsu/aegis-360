import Foundation

do {
    var data = Data()
    while let part = try FileHandle.standardInput.read(upToCount: 65_537 - data.count),
          !part.isEmpty {
        data.append(part)
        if data.count > 65_536 { break }
    }
    let request = try StageAAdapterRequest.parse(data)
    let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath,
                  isDirectory: true)
    let images = try StageAResolvedMedia.resolve(request, cwd: cwd)
    print("accepted \(images.count) ordered PNGs")
} catch {
    fputs("invalid adapter media\n", stderr)
    exit(3)
}
