import Foundation
import MLX

guard CommandLine.arguments.count == 2 else {
    fputs("usage: mlx-gpu-smoke LIBRARY\n", stderr)
    exit(2)
}

GPU.metallib = URL(fileURLWithPath: CommandLine.arguments[1])
let values = Device.withDefaultDevice(.gpu) {
    let input = MLXArray([1, 2, 3])
    let output = input + input
    eval(output)
    return output.asArray(Int32.self)
}
guard values == [2, 4, 6] else {
    fputs("unexpected GPU result: \(values)\n", stderr)
    exit(3)
}
print("MLX GPU add: \(values)")
