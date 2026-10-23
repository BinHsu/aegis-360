import Foundation
import Metal

guard CommandLine.arguments.count == 2 else {
    fputs("usage: check_mlx_metallib LIBRARY\n", stderr)
    exit(2)
}
guard let device = MTLCreateSystemDefaultDevice() else {
    fputs("Metal device unavailable\n", stderr)
    exit(3)
}
do {
    let library = try device.makeLibrary(URL: URL(fileURLWithPath: CommandLine.arguments[1]))
    print("loaded \(library.functionNames.count) functions on \(device.name)")
    guard !library.functionNames.isEmpty else { exit(4) }
} catch {
    fputs("Metal library load failed: \(error)\n", stderr)
    exit(5)
}
