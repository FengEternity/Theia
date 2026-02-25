"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRange = exports.setFrameRangeFromCli = exports.setFrameRange = void 0;
const renderer_1 = require("@remotion/renderer");
let range = null;
const setFrameRange = (newFrameRange) => {
    renderer_1.RenderInternals.validateFrameRange(newFrameRange);
    range = newFrameRange;
};
exports.setFrameRange = setFrameRange;
const setFrameRangeFromCli = (newFrameRange) => {
    if (typeof newFrameRange === 'number') {
        if (newFrameRange < 0) {
            (0, exports.setFrameRange)([0, Math.abs(newFrameRange)]);
            return;
        }
        (0, exports.setFrameRange)(newFrameRange);
        range = newFrameRange;
        return;
    }
    if (typeof newFrameRange === 'string') {
        if (newFrameRange.trim() === '') {
            throw new Error('--frames flag must be a single number, or 2 numbers separated by `-`');
        }
        const parts = newFrameRange.split('-');
        if (parts.length > 2 || parts.length <= 0) {
            throw new Error(`--frames flag must be a number or 2 numbers separated by '-', instead got ${parts.length} numbers`);
        }
        if (parts.length === 1) {
            const value = Number(parts[0]);
            if (isNaN(value)) {
                throw new Error('--frames flag must be a single number, or 2 numbers separated by `-`');
            }
            (0, exports.setFrameRange)(value);
            return;
        }
        const [firstPart, secondPart] = parts;
        if (secondPart === '' && firstPart !== '') {
            const start = Number(firstPart);
            if (isNaN(start)) {
                throw new Error('--frames flag must be a single number, or 2 numbers separated by `-`');
            }
            (0, exports.setFrameRange)([start, null]);
            return;
        }
        const parsed = parts.map((f) => Number(f));
        const [first, second] = parsed;
        for (const value of parsed) {
            if (isNaN(value)) {
                throw new Error('--frames flag must be a single number, or 2 numbers separated by `-`');
            }
        }
        if (second < first) {
            throw new Error('The second number of the --frames flag number should be greater or equal than first number');
        }
        (0, exports.setFrameRange)([first, second]);
    }
};
exports.setFrameRangeFromCli = setFrameRangeFromCli;
const getRange = () => range;
exports.getRange = getRange;
