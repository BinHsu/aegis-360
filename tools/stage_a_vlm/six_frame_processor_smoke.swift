import CoreImage
import CoreMedia
import Foundation
import MLX
import MLXLMCommon
import MLXVLM

@main
struct SixFrameProcessorSmoke {
    static func main() async {
        do {
            try await run()
        } catch {
            fputs("six-frame processing error\n", stderr)
            exit(5)
        }
    }

    static func run() async throws {
        guard CommandLine.arguments.count == 3,
              ["ordered", "reversed", "short"].contains(CommandLine.arguments[2]) else {
            fputs("usage: six-frame-processor-smoke LIBRARY ordered|reversed|short\n", stderr)
            exit(2)
        }
        GPU.metallib = URL(fileURLWithPath: CommandLine.arguments[1])
        let reversed = CommandLine.arguments[2] == "reversed"
        let images: [UserInput.Image] = (0..<6).map { index in
            let sourceIndex = reversed ? 5 - index : index
            let color = CIColor(red: CGFloat(sourceIndex + 1) / 10,
                                green: 0, blue: 0, alpha: 1)
            let image = CIImage(color: color).cropped(to: CGRect(x: 0, y: 0, width: 2, height: 2))
            return .ciImage(image)
        }
        let selectedImages = CommandLine.arguments[2] == "short" ? Array(images.dropLast()) : images
        let sequence = try StageAFrameSequence.make(images: selectedImages)
        let result = try await MediaProcessing.asProcessedSequence(
            sequence.video, processing: sequence.processing)
        guard result.frames.count == 6,
              result.timestamps.map(\.seconds) == (0..<6).map(Double.init) else {
            fputs("six-frame count or timestamp mismatch\n", stderr)
            exit(3)
        }
        let sums: [Float] = result.frames.map { $0.asArray(Float.self).reduce(0, +) }
        guard zip(sums, sums.dropFirst()).allSatisfy({ $0.0 + 0.01 < $0.1 }) else {
            fputs("six-frame order mismatch\n", stderr)
            exit(4)
        }
        print("six-frame ordered processor: 6 frames, 6 timestamps, distinct ordered pixels")
    }
}
