import Foundation

do {
    var data = Data()
    while let part = try FileHandle.standardInput.read(upToCount: 65_537 - data.count),
          !part.isEmpty {
        data.append(part)
        if data.count > 65_536 { break }
    }
    let request = try StageAAdapterRequest.parse(data)
    print("accepted \(request.packetID) with \(request.mediaPaths.count) rows")
} catch {
    fputs("invalid adapter request\n", stderr)
    exit(3)
}
