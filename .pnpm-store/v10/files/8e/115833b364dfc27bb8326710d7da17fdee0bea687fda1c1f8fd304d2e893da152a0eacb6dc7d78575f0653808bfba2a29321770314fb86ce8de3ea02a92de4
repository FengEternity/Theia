"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.extractFrames = extractFrames;
const mediabunny_1 = require("mediabunny");
async function extractFrames({ src, timestampsInSeconds, onVideoSample, signal, }) {
    const input = new mediabunny_1.Input({
        formats: mediabunny_1.ALL_FORMATS,
        source: new mediabunny_1.UrlSource(src),
    });
    const dispose = () => {
        input.dispose();
    };
    if (signal) {
        signal.addEventListener('abort', dispose, { once: true });
    }
    try {
        const [durationInSeconds, format, videoTrack] = await Promise.all([
            input.computeDuration(),
            input.getFormat(),
            input.getPrimaryVideoTrack(),
        ]);
        if (!videoTrack) {
            throw new Error('No video track found in the input');
        }
        const timestamps = typeof timestampsInSeconds === 'function'
            ? await timestampsInSeconds({
                track: {
                    width: videoTrack.displayWidth,
                    height: videoTrack.displayHeight,
                },
                container: format.name,
                durationInSeconds,
            })
            : timestampsInSeconds;
        if (timestamps.length === 0) {
            return;
        }
        const sink = new mediabunny_1.VideoSampleSink(videoTrack);
        for await (const videoSample of sink.samplesAtTimestamps(timestamps)) {
            if (signal === null || signal === void 0 ? void 0 : signal.aborted) {
                videoSample === null || videoSample === void 0 ? void 0 : videoSample.close();
                break;
            }
            if (!videoSample) {
                continue;
            }
            onVideoSample(videoSample);
        }
    }
    catch (error) {
        if (error instanceof mediabunny_1.InputDisposedError) {
            return;
        }
        throw error;
    }
    finally {
        dispose();
        if (signal) {
            signal.removeEventListener('abort', dispose);
        }
    }
}
