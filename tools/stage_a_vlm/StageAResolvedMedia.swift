import Darwin
import CoreGraphics
import Foundation
import ImageIO

enum StageAResolvedMediaError: Error {
    case invalid
}

/// Resolve the request's fixed relative paths from the launcher's retained cwd.
/// The coordinator owns bundle identity and content hashes before and after execution.
struct StageAResolvedMedia {
    static func resolve(_ request: StageAAdapterRequest, cwd: URL) throws -> [CGImage] {
        guard cwd.isFileURL, request.mediaPaths.count == 6 else {
            throw StageAResolvedMediaError.invalid
        }
        var result: [CGImage] = []
        for path in request.mediaPaths {
            let url = cwd.appending(path: path)
            var status = stat()
            guard Darwin.lstat(url.path, &status) == 0,
                  status.st_mode & mode_t(S_IFMT) == mode_t(S_IFREG),
                  status.st_nlink == 1,
                  let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                  CGImageSourceGetType(source) as String? == "public.png",
                  CGImageSourceGetCount(source) == 1,
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
                  image.width == 960, image.height == 540 else {
                throw StageAResolvedMediaError.invalid
            }
            result.append(image)
        }
        return result
    }
}
