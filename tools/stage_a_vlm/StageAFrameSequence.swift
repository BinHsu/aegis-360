import CoreMedia
import Foundation
import MLXLMCommon

enum StageAFrameSequenceError: Error {
    case wrongImageCount
}

/// Bind the six already-validated packet images to ordinal, local-only video frames.
/// The processor samples relative to zero, so source timestamps must not enter here.
struct StageAFrameSequence {
    static let frameCount = 6

    static func make(images: [UserInput.Image]) throws ->
        (video: UserInput.Video, processing: UserInput.VideoProcessing)
    {
        guard images.count == frameCount else {
            throw StageAFrameSequenceError.wrongImageCount
        }
        let frames = images.enumerated().map { index, image in
            UserInput.VideoFrame(image: image,
                                 timeStamp: CMTime(value: Int64(index), timescale: 1))
        }
        return (.frames(frames), .init(targetFrames: frameCount))
    }
}
