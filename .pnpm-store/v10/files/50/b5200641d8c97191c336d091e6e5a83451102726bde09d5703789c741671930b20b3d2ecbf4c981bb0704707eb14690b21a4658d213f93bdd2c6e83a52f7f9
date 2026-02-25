"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.handleRoutes = void 0;
const bundler_1 = require("@remotion/bundler");
const studio_shared_1 = require("@remotion/studio-shared");
const fs_1 = __importStar(require("fs"));
const node_fs_1 = require("node:fs");
const node_path_1 = __importStar(require("node:path"));
const node_url_1 = require("node:url");
const client_render_queue_1 = require("./client-render-queue");
const get_file_source_1 = require("./helpers/get-file-source");
const get_installed_installable_packages_1 = require("./helpers/get-installed-installable-packages");
const open_in_editor_1 = require("./helpers/open-in-editor");
const resolve_output_path_1 = require("./helpers/resolve-output-path");
const api_routes_1 = require("./preview-server/api-routes");
const get_package_manager_1 = require("./preview-server/get-package-manager");
const handler_1 = require("./preview-server/handler");
const parse_body_1 = require("./preview-server/parse-body");
const public_folder_1 = require("./preview-server/public-folder");
const serve_static_1 = require("./preview-server/serve-static");
const editorGuess = (0, open_in_editor_1.guessEditor)();
const static404 = (response) => {
    response.writeHead(404);
    response.end('The static/ prefix has been changed, this URL is no longer valid.');
    return Promise.resolve();
};
const output404 = (response) => {
    response.writeHead(404);
    response.end('The outputs/ prefix has been changed, this URL is no longer valid.');
    return Promise.resolve();
};
const handleRemotionConfig = (response, remotionRoot) => {
    var _a;
    response.writeHead(200, {
        'Content-Type': 'application/json',
    });
    const body = {
        isRemotion: true,
        cwd: remotionRoot,
        version: (_a = process.env.REMOTION_VERSION) !== null && _a !== void 0 ? _a : null,
    };
    response.end(JSON.stringify(body));
    return Promise.resolve();
};
const handleFallback = async ({ remotionRoot, hash, response, getCurrentInputProps, getEnvVariables, publicDir, getRenderQueue, getRenderDefaults, numberOfAudioTags, audioLatencyHint, gitSource, logLevel, enableCrossSiteIsolation, }) => {
    const [edit] = await editorGuess;
    const displayName = (0, open_in_editor_1.getDisplayNameForEditor)(edit ? edit.command : null);
    response.setHeader('content-type', 'text/html');
    if (enableCrossSiteIsolation) {
        response.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
        response.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
    }
    const packageManager = (0, get_package_manager_1.getPackageManager)({
        remotionRoot,
        packageManager: undefined,
        dirUp: 0,
        logLevel,
    });
    (0, public_folder_1.fetchFolder)({ publicDir, staticHash: hash });
    const installedDependencies = (0, get_installed_installable_packages_1.getInstalledInstallablePackages)(remotionRoot);
    response.end(bundler_1.BundlerInternals.indexHtml({
        staticHash: hash,
        publicPath: '/',
        editorName: displayName,
        envVariables: getEnvVariables(),
        inputProps: getCurrentInputProps(),
        remotionRoot,
        studioServerCommand: packageManager === 'unknown' ? null : packageManager.startCommand,
        renderQueue: getRenderQueue(),
        completedClientRenders: (0, client_render_queue_1.getCompletedClientRenders)(),
        numberOfAudioTags,
        publicFiles: (0, public_folder_1.getFiles)(),
        includeFavicon: true,
        title: 'Remotion Studio',
        renderDefaults: getRenderDefaults(),
        publicFolderExists: (0, node_fs_1.existsSync)(publicDir) ? publicDir : null,
        gitSource,
        projectName: (0, studio_shared_1.getProjectName)({
            basename: node_path_1.default.basename,
            gitSource,
            resolvedRemotionRoot: remotionRoot,
        }),
        installedDependencies,
        packageManager: packageManager === 'unknown' ? 'unknown' : packageManager.manager,
        logLevel,
        mode: 'dev',
        audioLatencyHint: audioLatencyHint !== null && audioLatencyHint !== void 0 ? audioLatencyHint : 'interactive',
    }));
};
const handleFileSource = async ({ method, remotionRoot, search, response, }) => {
    if (method === 'OPTIONS') {
        response.writeHead(200);
        response.end();
        return Promise.resolve();
    }
    if (!search.startsWith('?')) {
        throw new Error('query must start with ?');
    }
    const query = new node_url_1.URLSearchParams(search);
    const f = query.get('f');
    if (typeof f !== 'string') {
        throw new Error('must pass `f` parameter');
    }
    const data = await (0, get_file_source_1.getFileSource)(remotionRoot, decodeURIComponent(f));
    response.writeHead(200);
    response.write(data);
    response.end();
    return Promise.resolve();
};
const handleOpenInEditor = async (remotionRoot, req, res, logLevel) => {
    if (req.method === 'OPTIONS') {
        res.statusCode = 200;
        res.end();
        return;
    }
    try {
        const body = (await (0, parse_body_1.parseRequestBody)(req));
        if (!('stack' in body)) {
            throw new TypeError('Need to pass stack');
        }
        const stack = body.stack;
        const guess = await editorGuess;
        const didOpen = await (0, open_in_editor_1.launchEditor)({
            colNumber: stack.originalColumnNumber,
            editor: guess[0],
            fileName: node_path_1.default.resolve(remotionRoot, stack.originalFileName),
            lineNumber: stack.originalLineNumber,
            vsCodeNewWindow: false,
            logLevel,
        });
        res.setHeader('content-type', 'application/json');
        res.writeHead(200);
        res.end(JSON.stringify({
            success: didOpen,
        }));
    }
    catch (_a) {
        res.setHeader('content-type', 'application/json');
        res.writeHead(200);
        res.end(JSON.stringify({
            success: false,
        }));
    }
};
const validateSameOrigin = (req) => {
    const { origin, host } = req.headers;
    if (origin) {
        const originUrl = new URL(origin);
        if (originUrl.host !== host) {
            throw new Error('Request from different origin not allowed');
        }
    }
};
const handleAddAsset = ({ req, res, search, publicDir, }) => {
    try {
        validateSameOrigin(req);
        const query = new node_url_1.URLSearchParams(search);
        const filePath = query.get('filePath');
        if (typeof filePath !== 'string') {
            throw new Error('No `filePath` provided');
        }
        const absolutePath = node_path_1.default.join(publicDir, filePath);
        const relativeToPublicDir = node_path_1.default.relative(publicDir, absolutePath);
        if (relativeToPublicDir.startsWith('..')) {
            throw new Error(`Not allowed to write to ${relativeToPublicDir}`);
        }
        fs_1.default.mkdirSync(node_path_1.default.dirname(absolutePath), { recursive: true });
        const writeStream = (0, fs_1.createWriteStream)(absolutePath);
        writeStream.on('close', () => {
            res.end(JSON.stringify({ success: true }));
        });
        req.pipe(writeStream);
    }
    catch (err) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: err.message }));
    }
    return Promise.resolve();
};
const handleUploadOutput = ({ req, res, search, remotionRoot, }) => {
    try {
        validateSameOrigin(req);
        const query = new node_url_1.URLSearchParams(search);
        const filePath = query.get('filePath');
        if (typeof filePath !== 'string') {
            throw new Error('No `filePath` provided');
        }
        const absolutePath = (0, resolve_output_path_1.resolveOutputPath)(remotionRoot, filePath);
        fs_1.default.mkdirSync(node_path_1.default.dirname(absolutePath), { recursive: true });
        const writeStream = (0, fs_1.createWriteStream)(absolutePath);
        writeStream.on('close', () => {
            res.end(JSON.stringify({ success: true }));
        });
        writeStream.on('error', (err) => {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: err.message }));
        });
        req.on('error', (err) => {
            writeStream.destroy();
            res.statusCode = 500;
            res.end(JSON.stringify({ error: err.message }));
        });
        req.pipe(writeStream);
    }
    catch (err) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: err.message }));
    }
    return Promise.resolve();
};
const handleRegisterClientRender = async ({ req, res, remotionRoot, }) => {
    try {
        validateSameOrigin(req);
        const body = (await (0, parse_body_1.parseRequestBody)(req));
        (0, client_render_queue_1.addCompletedClientRender)({ render: body, remotionRoot });
        res.setHeader('content-type', 'application/json');
        res.writeHead(200);
        res.end(JSON.stringify({ success: true }));
    }
    catch (err) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: err.message }));
    }
};
const handleUnregisterClientRender = async ({ req, res, }) => {
    try {
        validateSameOrigin(req);
        const body = (await (0, parse_body_1.parseRequestBody)(req));
        (0, client_render_queue_1.removeCompletedClientRender)(body.id);
        res.setHeader('content-type', 'application/json');
        res.writeHead(200);
        res.end(JSON.stringify({ success: true }));
    }
    catch (err) {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: err.message }));
    }
};
const handleFavicon = (_, response) => {
    const filePath = node_path_1.default.join(__dirname, '..', 'web', 'favicon.png');
    const stat = (0, node_fs_1.statSync)(filePath);
    response.writeHead(200, {
        'Content-Type': 'image/png',
        'Content-Length': stat.size,
    });
    const readStream = (0, node_fs_1.createReadStream)(filePath);
    readStream.pipe(response);
    return Promise.resolve();
};
const handleBeep = (_, response) => {
    const filePath = node_path_1.default.join(__dirname, '..', 'web', 'beep.wav');
    const stat = (0, node_fs_1.statSync)(filePath);
    response.writeHead(200, {
        'Content-Type': 'audio/wav',
        'Content-Length': stat.size,
    });
    const readStream = (0, node_fs_1.createReadStream)(filePath);
    readStream.pipe(response);
    return Promise.resolve();
};
const handleWasm = (_, response) => {
    const filePath = node_path_1.default.resolve(require.resolve('source-map'), '..', 'lib', 'mappings.wasm');
    const stat = (0, node_fs_1.statSync)(filePath);
    response.writeHead(200, {
        'Content-Type': 'application/wasm',
        'Content-Length': stat.size,
    });
    const readStream = (0, node_fs_1.createReadStream)(filePath);
    readStream.pipe(response);
    return Promise.resolve();
};
const handleRoutes = ({ staticHash, staticHashPrefix, outputHash, outputHashPrefix, request, response, liveEventsServer, getCurrentInputProps, getEnvVariables, remotionRoot, entryPoint, publicDir, logLevel, getRenderQueue, getRenderDefaults, numberOfAudioTags, queueMethods: methods, gitSource, binariesDirectory, audioLatencyHint, enableCrossSiteIsolation, }) => {
    const url = new URL(request.url, 'http://localhost');
    if (url.pathname === '/api/file-source') {
        return handleFileSource({
            remotionRoot,
            search: url.search,
            method: request.method,
            response,
        });
    }
    if (url.pathname === '/api/open-in-editor') {
        return handleOpenInEditor(remotionRoot, request, response, logLevel);
    }
    if (url.pathname === `${staticHash}/api/add-asset`) {
        return handleAddAsset({
            req: request,
            res: response,
            search: url.search,
            publicDir,
        });
    }
    if (url.pathname === '/api/upload-output') {
        return handleUploadOutput({
            req: request,
            res: response,
            search: url.search,
            remotionRoot,
        });
    }
    if (url.pathname === '/api/register-client-render') {
        return handleRegisterClientRender({
            req: request,
            res: response,
            remotionRoot,
        });
    }
    if (url.pathname === '/api/unregister-client-render') {
        return handleUnregisterClientRender({
            req: request,
            res: response,
        });
    }
    for (const [key, value] of Object.entries(api_routes_1.allApiRoutes)) {
        if (url.pathname === key) {
            return (0, handler_1.handleRequest)({
                remotionRoot,
                entryPoint,
                handler: value,
                request,
                response,
                logLevel,
                methods,
                binariesDirectory,
                publicDir,
            });
        }
    }
    if (url.pathname === '/favicon.ico') {
        return handleFavicon(request, response);
    }
    if (url.pathname === '/beep.wav') {
        return handleBeep(request, response);
    }
    if (url.pathname === studio_shared_1.SOURCE_MAP_ENDPOINT) {
        return handleWasm(request, response);
    }
    if (url.pathname === '/__remotion_config') {
        return handleRemotionConfig(response, remotionRoot);
    }
    if (url.pathname === '/events') {
        return liveEventsServer.router(request, response);
    }
    if (url.pathname.startsWith(staticHash)) {
        const filename = new URL(request.url, 'http://localhost').pathname.replace(new RegExp(`^${staticHash}`), '');
        const filePath = (0, node_path_1.join)(publicDir, decodeURIComponent(filename));
        return (0, serve_static_1.serveStatic)({
            root: publicDir,
            path: filePath,
            req: request,
            res: response,
            allowOutsidePublicFolder: false,
        });
    }
    if (url.pathname.startsWith(staticHashPrefix)) {
        return static404(response);
    }
    if (url.pathname.startsWith(outputHash)) {
        const filename = new URL(request.url, 'http://localhost').pathname.replace(new RegExp(`^${outputHash}`), '');
        const filePath = (0, node_path_1.join)(remotionRoot, decodeURIComponent(filename));
        return (0, serve_static_1.serveStatic)({
            root: remotionRoot,
            path: filePath,
            req: request,
            res: response,
            allowOutsidePublicFolder: false,
        });
    }
    if (url.pathname.startsWith(outputHashPrefix)) {
        return output404(response);
    }
    return handleFallback({
        remotionRoot,
        hash: staticHash,
        response,
        getCurrentInputProps,
        getEnvVariables,
        publicDir,
        getRenderQueue,
        getRenderDefaults,
        numberOfAudioTags,
        gitSource,
        logLevel,
        audioLatencyHint,
        enableCrossSiteIsolation,
    });
};
exports.handleRoutes = handleRoutes;
