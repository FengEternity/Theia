export { ApiRoutes, CopyStillToClipboardRequest, getDefaultOutLocation, OpenInFileExplorerRequest, } from '@remotion/studio-shared';
export type { AggregateRenderProgress, BundlingState, CopyingState, DownloadProgress, HotMiddlewareOptions, JobProgressCallback, ModuleMap, PackageManager, ProjectInfo, RenderingProgressInput, RenderJob, RenderJobWithCleanup, RequiredChromiumOptions, StitchingProgressInput, UiOpenGlOptions, } from '@remotion/studio-shared';
import { AnsiDiff } from './ansi-diff';
export declare const StudioServerInternals: {
    startStudio: ({ browserArgs, browserFlag, shouldOpenBrowser, fullEntryPath, logLevel, getCurrentInputProps, getEnvVariables, desiredPort, maxTimelineTracks, remotionRoot, keyboardShortcutsEnabled, experimentalClientSideRenderingEnabled, experimentalVisualModeEnabled, relativePublicDir, webpackOverride, poll, getRenderDefaults, getRenderQueue, numberOfAudioTags, queueMethods, previewEntry, gitSource, bufferStateDelayInMilliseconds, binariesDirectory, forceIPv4, audioLatencyHint, enableCrossSiteIsolation, askAIEnabled, forceNew, rspack, }: {
        browserArgs: string;
        browserFlag: string;
        logLevel: "error" | "info" | "trace" | "verbose" | "warn";
        shouldOpenBrowser: boolean;
        fullEntryPath: string;
        getCurrentInputProps: () => object;
        getEnvVariables: () => Record<string, string>;
        desiredPort: number | null;
        maxTimelineTracks: number | null;
        bufferStateDelayInMilliseconds: number | null;
        remotionRoot: string;
        keyboardShortcutsEnabled: boolean;
        experimentalClientSideRenderingEnabled: boolean;
        experimentalVisualModeEnabled: boolean;
        relativePublicDir: string | null;
        webpackOverride: import("@remotion/bundler").WebpackOverrideFn;
        poll: number | null;
        getRenderDefaults: () => import("@remotion/studio-shared").RenderDefaults;
        getRenderQueue: () => import("@remotion/studio-shared").RenderJob[];
        numberOfAudioTags: number;
        audioLatencyHint: AudioContextLatencyCategory | null;
        enableCrossSiteIsolation: boolean;
        queueMethods: import("./preview-server/api-types").QueueMethods;
        previewEntry: string;
        gitSource: import("@remotion/studio-shared").GitSource | null;
        binariesDirectory: string | null;
        forceIPv4: boolean;
        askAIEnabled: boolean;
        forceNew: boolean;
        rspack: boolean;
    }) => Promise<import("./start-studio").StartStudioResult>;
    getRemotionVersion: () => any;
    waitForLiveEventsListener: () => Promise<import("./preview-server/live-events").LiveEventsServer>;
    lockFilePaths: {
        manager: import("@remotion/studio-shared").PackageManager;
        path: string;
        installCommand: string;
        startCommand: string;
    }[];
    getPackageManager: ({ remotionRoot, packageManager, dirUp, logLevel, }: {
        remotionRoot: string;
        packageManager: string | undefined;
        dirUp: number;
        logLevel: "error" | "info" | "trace" | "verbose" | "warn";
    }) => "unknown" | {
        manager: import("@remotion/studio-shared").PackageManager;
        path: string;
        installCommand: string;
        startCommand: string;
    };
    getMaxTimelineTracks: () => number;
    setMaxTimelineTracks: (maxTracks: number) => void;
    getLatestRemotionVersion: () => Promise<any>;
    installFileWatcher: ({ file, onChange, }: {
        file: string;
        onChange: (type: "changed" | "created" | "deleted") => void;
    }) => {
        exists: boolean;
        unwatch: () => void;
    };
    AnsiDiff: typeof AnsiDiff;
    formatBytes: (number: number, options?: (Intl.NumberFormatOptions & {
        locale: string;
        bits?: boolean | undefined;
        binary?: boolean | undefined;
        signed: boolean;
    }) | undefined) => string;
    parseAndApplyCodemod: ({ input, codeMod, }: {
        input: string;
        codeMod: import("@remotion/studio-shared").RecastCodemod;
    }) => {
        newContents: string;
        changesMade: import("./codemods/recast-mods").Change[];
    };
    getInstalledDependencies: (remotionRoot: string) => {
        dependencies: string[];
        devDependencies: string[];
        optionalDependencies: string[];
        peerDependencies: string[];
    };
    getInstallCommand: ({ manager, packages, version, additionalArgs, }: {
        manager: import("@remotion/studio-shared").PackageManager;
        packages: string[];
        version: string;
        additionalArgs: string[];
    }) => string[];
    addCompletedClientRender: ({ render, remotionRoot, }: {
        render: import("@remotion/studio-shared").CompletedClientRender;
        remotionRoot: string;
    }) => void;
    getCompletedClientRenders: () => import("@remotion/studio-shared").CompletedClientRender[];
    removeCompletedClientRender: (id: string) => void;
};
