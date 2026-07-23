import AVFoundation
import CoreImage
import Foundation

struct Crop: Decodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct Overscan: Decodable {
    let recommendedCenteredCrop: Crop
}

struct PlanFrame: Decodable {
    let timestampSeconds: Double
    let correctionHomographyRowMajor: [Double]
}

struct StabilizationPlan: Decodable {
    let schemaVersion: Int
    let frameWidth: Int
    let frameHeight: Int
    let frames: [PlanFrame]
    let overscan: Overscan
}

enum RenderError: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self {
        case .message(let value): return value
        }
    }
}

struct Arguments {
    let input: URL
    let plan: URL
    let output: URL
    let start: Double?
    let duration: Double?
}

func parseArguments() throws -> Arguments {
    var positional: [String] = []
    var start: Double?
    var duration: Double?
    var index = 1
    while index < CommandLine.arguments.count {
        let value = CommandLine.arguments[index]
        if value == "--start" || value == "--duration" {
            guard index + 1 < CommandLine.arguments.count,
                  let number = Double(CommandLine.arguments[index + 1]),
                  number.isFinite, number >= 0 else {
                throw RenderError.message("\(value) requires a finite nonnegative number")
            }
            if value == "--start" { start = number } else { duration = number }
            index += 2
        } else {
            positional.append(value)
            index += 1
        }
    }
    guard positional.count == 3 else {
        throw RenderError.message(
            "usage: flat_postwarp_renderer INPUT_VIDEO PLAN.json OUTPUT.mp4 [--start SECONDS] [--duration SECONDS]")
    }
    if let duration, duration <= 0 {
        throw RenderError.message("--duration must be greater than zero")
    }
    return Arguments(
        input: URL(fileURLWithPath: positional[0]),
        plan: URL(fileURLWithPath: positional[1]),
        output: URL(fileURLWithPath: positional[2]),
        start: start,
        duration: duration)
}

func validate(_ plan: StabilizationPlan) throws {
    guard plan.schemaVersion == 1 else { throw RenderError.message("unsupported plan schemaVersion") }
    guard plan.frameWidth > 0, plan.frameHeight > 0 else {
        throw RenderError.message("plan frame dimensions must be positive")
    }
    guard !plan.frames.isEmpty else { throw RenderError.message("plan contains no frames") }
    var prior = -Double.infinity
    for frame in plan.frames {
        guard frame.timestampSeconds.isFinite, frame.timestampSeconds >= 0,
              frame.timestampSeconds > prior else {
            throw RenderError.message("plan timestamps must be finite, nonnegative, and increasing")
        }
        guard frame.correctionHomographyRowMajor.count == 9,
              frame.correctionHomographyRowMajor.allSatisfy({ $0.isFinite }) else {
            throw RenderError.message("correction homography must contain nine finite values")
        }
        let h = frame.correctionHomographyRowMajor
        guard abs(h[6]) < 1e-9, abs(h[7]) < 1e-9, abs(h[8] - 1) < 1e-9 else {
            throw RenderError.message("only affine similarity corrections are supported")
        }
        prior = frame.timestampSeconds
    }
    let crop = plan.overscan.recommendedCenteredCrop
    guard crop.x >= 0, crop.y >= 0, crop.width > 0, crop.height > 0,
          crop.x + crop.width <= Double(plan.frameWidth) + 1e-6,
          crop.y + crop.height <= Double(plan.frameHeight) + 1e-6 else {
        throw RenderError.message("recommended crop lies outside the planned frame")
    }
}

func correction(at relativeSeconds: Double, frames: [PlanFrame]) -> [Double] {
    if relativeSeconds <= frames[0].timestampSeconds {
        return frames[0].correctionHomographyRowMajor
    }
    var low = 0
    var high = frames.count
    while low < high {
        let middle = (low + high) / 2
        if frames[middle].timestampSeconds <= relativeSeconds { low = middle + 1 } else { high = middle }
    }
    return frames[max(0, low - 1)].correctionHomographyRowMajor
}

func coreImageTransform(_ h: [Double], height: Double) -> CGAffineTransform {
    // Conjugate the plan's top-left-origin transform into CI's bottom-left coordinates.
    return CGAffineTransform(
        a: h[0], b: -h[3], c: -h[1], d: h[4],
        tx: h[1] * height + h[2],
        ty: height - h[4] * height - h[5])
}

func run(_ arguments: Arguments) throws {
    let fileManager = FileManager.default
    guard fileManager.fileExists(atPath: arguments.input.path) else {
        throw RenderError.message("input video does not exist")
    }
    guard !fileManager.fileExists(atPath: arguments.output.path) else {
        throw RenderError.message("refusing to overwrite output")
    }
    let plan = try JSONDecoder().decode(
        StabilizationPlan.self, from: Data(contentsOf: arguments.plan))
    try validate(plan)

    let asset = AVURLAsset(url: arguments.input)
    guard let videoTrack = asset.tracks(withMediaType: .video).first else {
        throw RenderError.message("input has no video track")
    }
    let natural = videoTrack.naturalSize.applying(videoTrack.preferredTransform)
    let inputWidth = Int(abs(natural.width).rounded())
    let inputHeight = Int(abs(natural.height).rounded())
    guard inputWidth == plan.frameWidth, inputHeight == plan.frameHeight else {
        throw RenderError.message(
            "plan dimensions \(plan.frameWidth)x\(plan.frameHeight) do not match video \(inputWidth)x\(inputHeight)")
    }

    let startSeconds = arguments.start ?? 0
    let start = CMTime(seconds: startSeconds, preferredTimescale: 600_000)
    let available = max(0, asset.duration.seconds - startSeconds)
    let durationSeconds = min(arguments.duration ?? available, available)
    guard durationSeconds > 0 else { throw RenderError.message("requested time range is empty") }
    let timeRange = CMTimeRange(
        start: start, duration: CMTime(seconds: durationSeconds, preferredTimescale: 600_000))

    let reader = try AVAssetReader(asset: asset)
    reader.timeRange = timeRange
    let videoOutput = AVAssetReaderTrackOutput(
        track: videoTrack,
        outputSettings: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ])
    videoOutput.alwaysCopiesSampleData = false
    guard reader.canAdd(videoOutput) else { throw RenderError.message("cannot add video reader output") }
    reader.add(videoOutput)

    let writer = try AVAssetWriter(outputURL: arguments.output, fileType: .mp4)
    let videoInput = AVAssetWriterInput(
        mediaType: .video,
        outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: plan.frameWidth,
            AVVideoHeightKey: plan.frameHeight,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: max(2_000_000, plan.frameWidth * plan.frameHeight * 6)
            ]
        ])
    videoInput.expectsMediaDataInRealTime = false
    let adaptor = AVAssetWriterInputPixelBufferAdaptor(
        assetWriterInput: videoInput,
        sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: plan.frameWidth,
            kCVPixelBufferHeightKey as String: plan.frameHeight
        ])
    guard writer.canAdd(videoInput) else { throw RenderError.message("cannot add video writer input") }
    writer.add(videoInput)

    var audioOutput: AVAssetReaderTrackOutput?
    var audioInput: AVAssetWriterInput?
    if let audioTrack = asset.tracks(withMediaType: .audio).first {
        let output = AVAssetReaderTrackOutput(track: audioTrack, outputSettings: nil)
        output.alwaysCopiesSampleData = false
        if reader.canAdd(output) {
            reader.add(output)
            let input = AVAssetWriterInput(
                mediaType: .audio, outputSettings: nil,
                sourceFormatHint: audioTrack.formatDescriptions.first as! CMFormatDescription?)
            input.expectsMediaDataInRealTime = false
            if writer.canAdd(input) {
                writer.add(input)
                audioOutput = output
                audioInput = input
            }
        }
    }

    guard writer.startWriting() else {
        throw RenderError.message("writer start failed: \(writer.error?.localizedDescription ?? "unknown")")
    }
    writer.startSession(atSourceTime: start)
    guard reader.startReading() else {
        throw RenderError.message("reader start failed: \(reader.error?.localizedDescription ?? "unknown")")
    }

    let context = CIContext(options: [.cacheIntermediates: false])
    let crop = plan.overscan.recommendedCenteredCrop
    let cropRect = CGRect(
        x: crop.x,
        y: Double(plan.frameHeight) - crop.y - crop.height,
        width: crop.width, height: crop.height)
    let outputBounds = CGRect(x: 0, y: 0, width: plan.frameWidth, height: plan.frameHeight)
    let group = DispatchGroup()
    let lock = NSLock()
    var failure: String?

    group.enter()
    videoInput.requestMediaDataWhenReady(on: DispatchQueue(label: "aegis.flat-postwarp.video")) {
        while videoInput.isReadyForMoreMediaData {
            guard let sample = videoOutput.copyNextSampleBuffer() else {
                videoInput.markAsFinished()
                group.leave()
                return
            }
            var stopped = false
            autoreleasepool {
                guard let source = CMSampleBufferGetImageBuffer(sample),
                      let destinationPool = adaptor.pixelBufferPool else {
                    lock.lock(); failure = "pixel buffer unavailable"; lock.unlock()
                    videoInput.markAsFinished(); reader.cancelReading()
                    group.leave()
                    stopped = true
                    return
                }
                let presentation = CMSampleBufferGetPresentationTimeStamp(sample)
                let relative = max(0, presentation.seconds - startSeconds)
                // Plans may use either clip-relative timestamps or an arbitrary
                // source timeline; align their first sample with the render range.
                let planTime = plan.frames[0].timestampSeconds + relative
                let h = correction(at: planTime, frames: plan.frames)
                let image = CIImage(cvPixelBuffer: source)
                    .transformed(by: coreImageTransform(h, height: Double(plan.frameHeight)))
                    .cropped(to: cropRect)
                    .transformed(by: CGAffineTransform(
                        translationX: -cropRect.minX, y: -cropRect.minY))
                    .transformed(by: CGAffineTransform(
                        scaleX: Double(plan.frameWidth) / crop.width,
                        y: Double(plan.frameHeight) / crop.height))
                    .cropped(to: outputBounds)
                var destination: CVPixelBuffer?
                guard CVPixelBufferPoolCreatePixelBuffer(
                    kCFAllocatorDefault, destinationPool, &destination) == kCVReturnSuccess,
                      let destination else {
                    lock.lock(); failure = "destination pixel buffer allocation failed"; lock.unlock()
                    videoInput.markAsFinished(); reader.cancelReading()
                    group.leave()
                    stopped = true
                    return
                }
                context.render(image, to: destination, bounds: outputBounds, colorSpace: CGColorSpaceCreateDeviceRGB())
                if !adaptor.append(destination, withPresentationTime: presentation) {
                    lock.lock()
                    failure = "video append failed: \(writer.error?.localizedDescription ?? "unknown")"
                    lock.unlock()
                    videoInput.markAsFinished(); reader.cancelReading()
                    group.leave()
                    stopped = true
                }
            }
            if stopped { return }
        }
    }

    if let audioOutput, let audioInput {
        group.enter()
        audioInput.requestMediaDataWhenReady(on: DispatchQueue(label: "aegis.flat-postwarp.audio")) {
            while audioInput.isReadyForMoreMediaData {
                guard let sample = audioOutput.copyNextSampleBuffer() else {
                    audioInput.markAsFinished()
                    group.leave()
                    return
                }
                if !audioInput.append(sample) {
                    lock.lock()
                    failure = "audio append failed: \(writer.error?.localizedDescription ?? "unknown")"
                    lock.unlock()
                    audioInput.markAsFinished(); reader.cancelReading()
                    group.leave()
                    return
                }
            }
        }
    }

    group.wait()
    if let failure { writer.cancelWriting(); throw RenderError.message(failure) }
    guard reader.status == .completed else {
        writer.cancelWriting()
        throw RenderError.message("reader failed: \(reader.error?.localizedDescription ?? "unknown")")
    }
    let finished = DispatchSemaphore(value: 0)
    writer.finishWriting { finished.signal() }
    finished.wait()
    guard writer.status == .completed else {
        throw RenderError.message("writer failed: \(writer.error?.localizedDescription ?? "unknown")")
    }
}

do {
    let arguments = try parseArguments()
    try run(arguments)
} catch {
    FileHandle.standardError.write(Data(("flat_postwarp_renderer: \(error)\n").utf8))
    exit(1)
}
