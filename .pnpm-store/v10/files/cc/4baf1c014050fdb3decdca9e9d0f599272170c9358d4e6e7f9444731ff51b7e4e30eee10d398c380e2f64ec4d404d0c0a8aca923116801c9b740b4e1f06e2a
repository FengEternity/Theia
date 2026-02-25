"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getProjectInfo = void 0;
const node_fs_1 = require("node:fs");
const node_path_1 = __importDefault(require("node:path"));
const getProjectInfo = (remotionRoot, entryPoint) => {
    var _a;
    const knownPaths = [
        'src/Root.tsx',
        'src/Root.jsx',
        'remotion/Root.tsx',
        'remotion/Root.jsx',
        'app/remotion/Root.tsx',
        'src/Video.tsx',
        'src/Video.jsx',
        'src/remotion/Root.tsx',
        'src/remotion/Root.jsx',
    ];
    const pathsToLookFor = [
        ...knownPaths.map((p) => {
            return node_path_1.default.join(remotionRoot, p);
        }),
        node_path_1.default.join(entryPoint, 'Root.tsx'),
        node_path_1.default.join(entryPoint, 'Root.jsx'),
        node_path_1.default.join(entryPoint, 'remotion/Root.tsx'),
        node_path_1.default.join(entryPoint, 'remotion/Root.jsx'),
    ];
    const rootFile = (_a = pathsToLookFor.find((p) => (0, node_fs_1.existsSync)(p))) !== null && _a !== void 0 ? _a : null;
    return Promise.resolve({
        rootFile,
        relativeRootFile: rootFile ? node_path_1.default.relative(remotionRoot, rootFile) : null,
    });
};
exports.getProjectInfo = getProjectInfo;
