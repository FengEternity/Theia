// src/client.ts
import { NoReactInternals as NoReactInternals4 } from "remotion/no-react";

// src/browser/TimeoutSettings.ts
var DEFAULT_TIMEOUT = 30000;

class TimeoutSettings {
  #defaultTimeout;
  #defaultNavigationTimeout;
  constructor() {
    this.#defaultTimeout = null;
    this.#defaultNavigationTimeout = null;
  }
  setDefaultTimeout(timeout) {
    this.#defaultTimeout = timeout;
  }
  setDefaultNavigationTimeout(timeout) {
    this.#defaultNavigationTimeout = timeout;
  }
  navigationTimeout() {
    if (this.#defaultNavigationTimeout !== null) {
      return this.#defaultNavigationTimeout;
    }
    if (this.#defaultTimeout !== null) {
      return this.#defaultTimeout;
    }
    return DEFAULT_TIMEOUT;
  }
  timeout() {
    if (this.#defaultTimeout !== null) {
      return this.#defaultTimeout;
    }
    return DEFAULT_TIMEOUT;
  }
}

// src/codec.ts
var validCodecs = [
  "h264",
  "h265",
  "vp8",
  "vp9",
  "mp3",
  "aac",
  "wav",
  "prores",
  "h264-mkv",
  "h264-ts",
  "gif"
];
var DEFAULT_CODEC = "h264";

// src/crf.ts
var defaultCrfMap = {
  h264: 18,
  h265: 23,
  vp8: 9,
  vp9: 28,
  prores: null,
  gif: null,
  "h264-mkv": 18,
  "h264-ts": 18,
  aac: null,
  mp3: null,
  wav: null
};
var getDefaultCrfForCodec = (codec) => {
  const val = defaultCrfMap[codec];
  if (val === undefined) {
    throw new TypeError(`Got unexpected codec "${codec}"`);
  }
  return val;
};
var crfRanges = {
  h264: [1, 51],
  h265: [0, 51],
  vp8: [4, 63],
  vp9: [0, 63],
  prores: [0, 0],
  gif: [0, 0],
  "h264-mkv": [1, 51],
  "h264-ts": [1, 51],
  aac: [0, 0],
  mp3: [0, 0],
  wav: [0, 0]
};
var getValidCrfRanges = (codec) => {
  const val = crfRanges[codec];
  if (val === undefined) {
    throw new TypeError(`Got unexpected codec "${codec}"`);
  }
  return val;
};

// src/codec-supports-media.ts
var codecSupportsVideoBitrateMap = {
  "h264-mkv": true,
  "h264-ts": true,
  aac: false,
  gif: false,
  h264: true,
  h265: true,
  mp3: false,
  prores: false,
  vp8: true,
  vp9: true,
  wav: false
};
var codecSupportsCrf = (codec) => {
  const range = getValidCrfRanges(codec);
  return range[0] !== range[1];
};
var codecSupportsVideoBitrate = (codec) => {
  return codecSupportsVideoBitrateMap[codec];
};

// src/file-extensions.ts
var defaultFileExtensionMap = {
  "h264-mkv": {
    default: "mkv",
    forAudioCodec: {
      "pcm-16": { possible: ["mkv"], default: "mkv" },
      mp3: { possible: ["mkv"], default: "mkv" }
    }
  },
  "h264-ts": {
    default: "ts",
    forAudioCodec: {
      "pcm-16": { possible: ["ts"], default: "ts" },
      aac: { possible: ["ts"], default: "ts" }
    }
  },
  aac: {
    default: "aac",
    forAudioCodec: {
      aac: {
        possible: ["aac", "3gp", "m4a", "m4b", "mpg", "mpeg"],
        default: "aac"
      },
      "pcm-16": {
        possible: ["wav"],
        default: "wav"
      }
    }
  },
  gif: {
    default: "gif",
    forAudioCodec: {}
  },
  h264: {
    default: "mp4",
    forAudioCodec: {
      "pcm-16": { possible: ["mkv", "mov"], default: "mkv" },
      aac: { possible: ["mp4", "mkv", "mov"], default: "mp4" },
      mp3: { possible: ["mp4", "mkv", "mov"], default: "mp4" }
    }
  },
  h265: {
    default: "mp4",
    forAudioCodec: {
      aac: { possible: ["mp4", "mkv", "hevc"], default: "mp4" },
      "pcm-16": { possible: ["mkv"], default: "mkv" }
    }
  },
  mp3: {
    default: "mp3",
    forAudioCodec: {
      mp3: { possible: ["mp3"], default: "mp3" },
      "pcm-16": { possible: ["wav"], default: "wav" }
    }
  },
  prores: {
    default: "mov",
    forAudioCodec: {
      aac: { possible: ["mov", "mkv", "mxf"], default: "mov" },
      "pcm-16": { possible: ["mov", "mkv", "mxf"], default: "mov" }
    }
  },
  vp8: {
    default: "webm",
    forAudioCodec: {
      "pcm-16": { possible: ["mkv"], default: "mkv" },
      opus: { possible: ["webm"], default: "webm" }
    }
  },
  vp9: {
    default: "webm",
    forAudioCodec: {
      "pcm-16": { possible: ["mkv"], default: "mkv" },
      opus: { possible: ["webm"], default: "webm" }
    }
  },
  wav: {
    default: "wav",
    forAudioCodec: {
      "pcm-16": { possible: ["wav"], default: "wav" }
    }
  }
};

// src/get-extension-from-codec.ts
var getFileExtensionFromCodec = (codec, audioCodec) => {
  if (!validCodecs.includes(codec)) {
    throw new Error(`Codec must be one of the following: ${validCodecs.join(", ")}, but got ${codec}`);
  }
  const map = defaultFileExtensionMap[codec];
  if (audioCodec === null) {
    return map.default;
  }
  const typedAudioCodec = audioCodec;
  if (!(typedAudioCodec in map.forAudioCodec)) {
    throw new Error(`Audio codec ${typedAudioCodec} is not supported for codec ${codec}`);
  }
  return map.forAudioCodec[audioCodec].default;
};
var makeFileExtensionMap = () => {
  const map = {};
  Object.keys(defaultFileExtensionMap).forEach((_codec) => {
    const codec = _codec;
    const fileExtMap = defaultFileExtensionMap[codec];
    const audioCodecs = Object.keys(fileExtMap.forAudioCodec);
    const possibleExtensionsForAudioCodec = audioCodecs.map((audioCodec) => fileExtMap.forAudioCodec[audioCodec].possible);
    const allPossibleExtensions = [
      fileExtMap.default,
      ...possibleExtensionsForAudioCodec.flat(1)
    ];
    for (const extension of allPossibleExtensions) {
      if (!map[extension]) {
        map[extension] = [];
      }
      if (!map[extension].includes(codec)) {
        map[extension].push(codec);
      }
    }
  });
  return map;
};
var defaultCodecsForFileExtension = {
  "3gp": "aac",
  aac: "aac",
  gif: "gif",
  hevc: "h265",
  m4a: "aac",
  m4b: "aac",
  mkv: "h264-mkv",
  mov: "prores",
  mp3: "mp3",
  mp4: "h264",
  mpeg: "aac",
  mpg: "aac",
  mxf: "prores",
  wav: "wav",
  webm: "vp8",
  ts: "h264-ts"
};

// src/image-format.ts
var validVideoImageFormats = ["png", "jpeg", "none"];
var validStillImageFormats = ["png", "jpeg", "pdf", "webp"];

// src/jpeg-quality.ts
var DEFAULT_JPEG_QUALITY = 80;
var validateJpegQuality = (q) => {
  if (typeof q !== "undefined" && typeof q !== "number") {
    throw new Error(`JPEG Quality option must be a number or undefined. Got ${typeof q} (${JSON.stringify(q)})`);
  }
  if (typeof q === "undefined") {
    return;
  }
  if (!Number.isFinite(q)) {
    throw new RangeError(`JPEG Quality must be a finite number, but is ${q}`);
  }
  if (Number.isNaN(q)) {
    throw new RangeError(`JPEG Quality is NaN, but must be a real number`);
  }
  if (q > 100 || q < 0) {
    throw new RangeError("JPEG Quality option must be between 0 and 100.");
  }
};

// src/log-level.ts
var logLevels = ["trace", "verbose", "info", "warn", "error"];
var getNumberForLogLevel = (level) => {
  return logLevels.indexOf(level);
};
var isValidLogLevel = (level) => {
  return getNumberForLogLevel(level) > -1;
};

// src/options/api-key.tsx
import { jsx, jsxs, Fragment } from "react/jsx-runtime";
var currentApiKey = null;
var cliFlag = "api-key";
var apiKeyOption = {
  name: "API key",
  cliFlag,
  description: () => /* @__PURE__ */ jsxs(Fragment, {
    children: [
      "API key for sending a usage event using ",
      /* @__PURE__ */ jsx("code", {
        children: "@remotion/licensing"
      }),
      "."
    ]
  }),
  ssrName: "apiKey",
  docLink: "https://www.remotion.dev/docs/licensing",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag]
      };
    }
    return {
      source: "default",
      value: currentApiKey
    };
  },
  setConfig: (value) => {
    currentApiKey = value;
  },
  id: cliFlag
};

// src/options/ask-ai.tsx
import { jsx as jsx2, Fragment as Fragment2 } from "react/jsx-runtime";
var askAIEnabled = true;
var cliFlag2 = "disable-ask-ai";
var askAIOption = {
  name: "Disable or Enable the Ask AI option",
  cliFlag: cliFlag2,
  description: () => /* @__PURE__ */ jsx2(Fragment2, {
    children: "If the Cmd + I shortcut of the Ask AI modal conflicts with your Studio, you can disable it using this."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setaskaienabled",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag2] !== undefined) {
      askAIEnabled = false;
      return {
        value: askAIEnabled,
        source: "cli"
      };
    }
    return {
      value: askAIEnabled,
      source: "config"
    };
  },
  setConfig(value) {
    askAIEnabled = value;
  },
  id: cliFlag2
};

// src/options/audio-bitrate.tsx
import { jsx as jsx3, jsxs as jsxs2, Fragment as Fragment3 } from "react/jsx-runtime";
var cliFlag3 = "audio-bitrate";
var audioBitrate = null;
var audioBitrateOption = {
  name: "Audio Bitrate",
  cliFlag: cliFlag3,
  description: () => /* @__PURE__ */ jsxs2(Fragment3, {
    children: [
      "Specify the target bitrate for the generated video. The syntax for FFmpeg",
      "'",
      "s ",
      /* @__PURE__ */ jsx3("code", {
        children: "-b:a"
      }),
      " parameter should be used. FFmpeg may encode the video in a way that will not result in the exact audio bitrate specified. Example values: ",
      /* @__PURE__ */ jsx3("code", {
        children: "512K"
      }),
      " for 512 kbps, ",
      /* @__PURE__ */ jsx3("code", {
        children: "1M"
      }),
      " for 1 Mbps. Default: ",
      /* @__PURE__ */ jsx3("code", {
        children: "320k"
      })
    ]
  }),
  ssrName: "audioBitrate",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#audiobitrate-",
  type: "0",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag3]) {
      return {
        value: commandLine[cliFlag3],
        source: "cli"
      };
    }
    if (audioBitrate) {
      return {
        value: audioBitrate,
        source: "config file"
      };
    }
    return {
      value: null,
      source: "default"
    };
  },
  setConfig: (value) => {
    audioBitrate = value;
  },
  id: cliFlag3
};

// src/options/separate-audio.tsx
var DEFAULT = null;
var cliFlag4 = "separate-audio-to";
var separateAudioOption = {
  cliFlag: cliFlag4,
  description: () => `If set, the audio will not be included in the main output but rendered as a separate file at the location you pass. It is recommended to use an absolute path. If a relative path is passed, it is relative to the Remotion Root.`,
  docLink: "https://remotion.dev/docs/renderer/render-media",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag4]) {
      return {
        source: "cli",
        value: commandLine[cliFlag4]
      };
    }
    return {
      source: "default",
      value: DEFAULT
    };
  },
  name: "Separate audio to",
  setConfig: () => {
    throw new Error("Not implemented");
  },
  ssrName: "separateAudioTo",
  type: "string",
  id: cliFlag4
};

// src/options/audio-codec.tsx
var validAudioCodecs = ["pcm-16", "aac", "mp3", "opus"];
var supportedAudioCodecs = {
  h264: ["aac", "pcm-16", "mp3"],
  "h264-mkv": ["pcm-16", "mp3"],
  "h264-ts": ["pcm-16", "aac"],
  aac: ["aac", "pcm-16"],
  avi: [],
  gif: [],
  h265: ["aac", "pcm-16"],
  mp3: ["mp3", "pcm-16"],
  prores: ["aac", "pcm-16"],
  vp8: ["opus", "pcm-16"],
  vp9: ["opus", "pcm-16"],
  wav: ["pcm-16"]
};
var _satisfies = supportedAudioCodecs;
if (_satisfies) {}
var cliFlag5 = "audio-codec";
var ssrName = "audioCodec";
var defaultAudioCodecs = {
  "h264-mkv": {
    lossless: "pcm-16",
    compressed: "pcm-16"
  },
  "h264-ts": {
    lossless: "pcm-16",
    compressed: "aac"
  },
  aac: {
    lossless: "pcm-16",
    compressed: "aac"
  },
  gif: {
    lossless: null,
    compressed: null
  },
  h264: {
    lossless: "pcm-16",
    compressed: "aac"
  },
  h265: {
    lossless: "pcm-16",
    compressed: "aac"
  },
  mp3: {
    lossless: "pcm-16",
    compressed: "mp3"
  },
  prores: {
    lossless: "pcm-16",
    compressed: "pcm-16"
  },
  vp8: {
    lossless: "pcm-16",
    compressed: "opus"
  },
  vp9: {
    lossless: "pcm-16",
    compressed: "opus"
  },
  wav: {
    lossless: "pcm-16",
    compressed: "pcm-16"
  }
};
var extensionMap = {
  aac: "aac",
  mp3: "mp3",
  opus: "opus",
  "pcm-16": "wav"
};
var getExtensionFromAudioCodec = (audioCodec) => {
  if (extensionMap[audioCodec]) {
    return extensionMap[audioCodec];
  }
  throw new Error(`Unsupported audio codec: ${audioCodec}`);
};
var resolveAudioCodec = ({
  codec,
  setting,
  preferLossless,
  separateAudioTo
}) => {
  let derivedFromSeparateAudioToExtension = null;
  if (separateAudioTo) {
    const extension = separateAudioTo.split(".").pop();
    for (const [key, value] of Object.entries(extensionMap)) {
      if (value === extension) {
        derivedFromSeparateAudioToExtension = key;
        if (!supportedAudioCodecs[codec].includes(derivedFromSeparateAudioToExtension) && derivedFromSeparateAudioToExtension) {
          throw new Error(`The codec is ${codec} but the audio codec derived from --${separateAudioOption.cliFlag} is ${derivedFromSeparateAudioToExtension}. The only supported codecs are: ${supportedAudioCodecs[codec].join(", ")}`);
        }
      }
    }
  }
  if (preferLossless) {
    const selected = getDefaultAudioCodec({ codec, preferLossless });
    if (derivedFromSeparateAudioToExtension && selected !== derivedFromSeparateAudioToExtension) {
      throw new Error(`The audio codec derived from --${separateAudioOption.cliFlag} is ${derivedFromSeparateAudioToExtension}, but does not match the audio codec derived from the "Prefer lossless" option (${selected}). Remove any conflicting options.`);
    }
    return selected;
  }
  if (setting === null) {
    if (derivedFromSeparateAudioToExtension) {
      return derivedFromSeparateAudioToExtension;
    }
    return getDefaultAudioCodec({ codec, preferLossless });
  }
  if (derivedFromSeparateAudioToExtension !== setting && derivedFromSeparateAudioToExtension) {
    throw new Error(`The audio codec derived from --${separateAudioOption.cliFlag} is ${derivedFromSeparateAudioToExtension}, but does not match the audio codec derived from your ${audioCodecOption.name} setting (${setting}). Remove any conflicting options.`);
  }
  return setting;
};
var getDefaultAudioCodec = ({
  codec,
  preferLossless
}) => {
  return defaultAudioCodecs[codec][preferLossless ? "lossless" : "compressed"];
};
var _audioCodec = null;
var audioCodecOption = {
  cliFlag: cliFlag5,
  setConfig: (audioCodec) => {
    if (audioCodec === null) {
      _audioCodec = null;
      return;
    }
    if (!validAudioCodecs.includes(audioCodec)) {
      throw new Error(`Audio codec must be one of the following: ${validAudioCodecs.join(", ")}, but got ${audioCodec}`);
    }
    _audioCodec = audioCodec;
  },
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag5]) {
      const codec = commandLine[cliFlag5];
      if (!validAudioCodecs.includes(commandLine[cliFlag5])) {
        throw new Error(`Audio codec must be one of the following: ${validAudioCodecs.join(", ")}, but got ${codec}`);
      }
      return {
        source: "cli",
        value: commandLine[cliFlag5]
      };
    }
    if (_audioCodec !== null) {
      return {
        source: "config",
        value: _audioCodec
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  description: () => `Set the format of the audio that is embedded in the video. Not all codec and audio codec combinations are supported and certain combinations require a certain file extension and container format. See the table in the docs to see possible combinations.`,
  docLink: "https://www.remotion.dev/docs/encoding/#audio-codec",
  name: "Audio Codec",
  ssrName,
  type: "aac",
  id: cliFlag5
};

// src/options/beep-on-finish.tsx
import { jsx as jsx4, Fragment as Fragment4 } from "react/jsx-runtime";
var beepOnFinish = false;
var cliFlag6 = "beep-on-finish";
var beepOnFinishOption = {
  name: "Beep on finish",
  cliFlag: cliFlag6,
  description: () => /* @__PURE__ */ jsx4(Fragment4, {
    children: "Whether the Remotion Studio tab should beep when the render is finished."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setbeeponfinish",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag6] !== undefined) {
      return {
        value: commandLine[cliFlag6],
        source: "cli"
      };
    }
    if (beepOnFinish !== false) {
      return {
        value: beepOnFinish,
        source: "config"
      };
    }
    return {
      value: false,
      source: "default"
    };
  },
  setConfig(value) {
    beepOnFinish = value;
  },
  id: cliFlag6
};

// src/options/binaries-directory.tsx
import { jsx as jsx5, jsxs as jsxs3, Fragment as Fragment5 } from "react/jsx-runtime";
var cliFlag7 = "binaries-directory";
var currentDirectory = null;
var binariesDirectoryOption = {
  name: "Binaries Directory",
  cliFlag: cliFlag7,
  description: () => /* @__PURE__ */ jsxs3(Fragment5, {
    children: [
      "The directory where the platform-specific binaries and libraries that Remotion needs are located. Those include an ",
      /* @__PURE__ */ jsx5("code", {
        children: "ffmpeg"
      }),
      " and",
      " ",
      /* @__PURE__ */ jsx5("code", {
        children: "ffprobe"
      }),
      " binary, a Rust binary for various tasks, and various shared libraries. If the value is set to ",
      /* @__PURE__ */ jsx5("code", {
        children: "null"
      }),
      ", which is the default, then the path of a platform-specific package located at",
      " ",
      /* @__PURE__ */ jsx5("code", {
        children: "node_modules/@remotion/compositor-*"
      }),
      " is selected.",
      /* @__PURE__ */ jsx5("br", {}),
      "This option is useful in environments where Remotion is not officially supported to run like bundled serverless functions or Electron."
    ]
  }),
  ssrName: "binariesDirectory",
  docLink: "https://www.remotion.dev/docs/renderer",
  type: "",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag7] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag7]
      };
    }
    if (currentDirectory !== null) {
      return {
        source: "config",
        value: currentDirectory
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    currentDirectory = value;
  },
  id: cliFlag7
};

// src/options/browser.tsx
import { jsx as jsx6, jsxs as jsxs4, Fragment as Fragment6 } from "react/jsx-runtime";
var cliFlag8 = "browser";
var browserOption = {
  name: "Browser",
  cliFlag: cliFlag8,
  description: () => /* @__PURE__ */ jsxs4(Fragment6, {
    children: [
      "Specify the browser which should be used for opening a tab. The default browser will be used by default. Pass an absolute path or",
      " ",
      /* @__PURE__ */ jsx6("code", {
        children: '"chrome"'
      }),
      " to use Chrome. If Chrome is selected as the browser and you are on macOS, Remotion will try to reuse an existing tab."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/studio#--browser",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag8] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag8]
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: () => {
    throw new Error("setBrowser is not supported. Pass --browser via the CLI instead.");
  },
  type: "",
  id: cliFlag8
};

// src/options/browser-executable.tsx
import { jsx as jsx7, Fragment as Fragment7 } from "react/jsx-runtime";
var currentBrowserExecutablePath = null;
var cliFlag9 = "browser-executable";
var browserExecutableOption = {
  name: "Browser executable",
  cliFlag: cliFlag9,
  description: () => /* @__PURE__ */ jsx7(Fragment7, {
    children: "Set a custom Chrome or Chromium executable path. By default Remotion will try to find an existing version of Chrome on your system and if not found, it will download one. This flag is useful if you don't have Chrome installed in a standard location and you want to prevent downloading an additional browser or need support for the H264 codec."
  }),
  ssrName: "browserExecutable",
  docLink: "https://www.remotion.dev/docs/config#setbrowserexecutable",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag9] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag9]
      };
    }
    if (currentBrowserExecutablePath !== null) {
      return {
        source: "config",
        value: currentBrowserExecutablePath
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    currentBrowserExecutablePath = value;
  },
  id: cliFlag9
};

// src/options/bundle-cache.tsx
import { jsx as jsx8, jsxs as jsxs5, Fragment as Fragment8 } from "react/jsx-runtime";
var cliFlag10 = "bundle-cache";
var cachingEnabled = true;
var bundleCacheOption = {
  name: "Webpack Bundle Caching",
  cliFlag: cliFlag10,
  description: () => /* @__PURE__ */ jsxs5(Fragment8, {
    children: [
      "Enable or disable Webpack caching. This flag is enabled by default, use",
      " ",
      /* @__PURE__ */ jsx8("code", {
        children: "--bundle-cache=false"
      }),
      " to disable caching."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setcachingenabled",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag10] !== undefined && commandLine[cliFlag10] !== null) {
      return {
        source: "cli",
        value: Boolean(commandLine[cliFlag10])
      };
    }
    return {
      source: cachingEnabled ? "default" : "config",
      value: cachingEnabled
    };
  },
  setConfig: (value) => {
    if (typeof value !== "boolean") {
      throw new TypeError(`Value for "${cliFlag10}" must be a boolean, but got ${typeof value}.`);
    }
    cachingEnabled = value;
  },
  type: true,
  id: cliFlag10
};

// src/options/chrome-mode.tsx
import { jsx as jsx9, jsxs as jsxs6, Fragment as Fragment9 } from "react/jsx-runtime";
var validChromeModeOptions = [
  "headless-shell",
  "chrome-for-testing"
];
var cliFlag11 = "chrome-mode";
var configSelection = null;
var chromeModeOption = {
  cliFlag: cliFlag11,
  name: "Chrome Mode",
  ssrName: "chromeMode",
  description: () => {
    return /* @__PURE__ */ jsxs6(Fragment9, {
      children: [
        "One of",
        " ",
        validChromeModeOptions.map((option, i) => /* @__PURE__ */ jsxs6("code", {
          children: [
            option,
            i === validChromeModeOptions.length - 1 ? "" : ", "
          ]
        }, option)),
        ". Default ",
        /* @__PURE__ */ jsx9("code", {
          children: "headless-shell"
        }),
        ".",
        " ",
        /* @__PURE__ */ jsxs6("a", {
          href: "https://remotion.dev/docs/miscellaneous/chrome-headless-shell",
          children: [
            "Use ",
            /* @__PURE__ */ jsx9("code", {
              children: "chrome-for-testing"
            }),
            " to take advantage of GPU drivers on Linux."
          ]
        })
      ]
    });
  },
  docLink: "https://www.remotion.dev/chrome-for-testing",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag11]) {
      if (!validChromeModeOptions.includes(commandLine[cliFlag11])) {
        throw new Error(`Invalid \`--${cliFlag11}\` value passed. Accepted values: ${validChromeModeOptions.map((l) => `'${l}'`).join(", ")}.`);
      }
      return {
        value: commandLine[cliFlag11],
        source: "cli"
      };
    }
    if (configSelection !== null) {
      return {
        value: configSelection,
        source: "config"
      };
    }
    return {
      value: "headless-shell",
      source: "default"
    };
  },
  setConfig: (newChromeMode) => {
    configSelection = newChromeMode;
  },
  type: "headless-shell",
  id: cliFlag11
};

// src/options/color-space.tsx
import { NoReactInternals } from "remotion/no-react";
import { jsx as jsx10, jsxs as jsxs7, Fragment as Fragment10 } from "react/jsx-runtime";
var validV4ColorSpaces = ["default", "bt601", "bt709", "bt2020-ncl"];
var validV5ColorSpaces = ["bt601", "bt709", "bt2020-ncl"];
var validColorSpaces = NoReactInternals.ENABLE_V5_BREAKING_CHANGES ? validV5ColorSpaces : validV4ColorSpaces;
var DEFAULT_COLOR_SPACE = NoReactInternals.ENABLE_V5_BREAKING_CHANGES ? "bt709" : "default";
var colorSpace = DEFAULT_COLOR_SPACE;
var cliFlag12 = "color-space";
var colorSpaceOption = {
  name: "Color space",
  cliFlag: "color-space",
  description: () => /* @__PURE__ */ jsxs7(Fragment10, {
    children: [
      "Color space to use for the video. Acceptable values:",
      " ",
      /* @__PURE__ */ jsxs7("code", {
        children: [
          '"',
          DEFAULT_COLOR_SPACE,
          '"'
        ]
      }),
      "(default since 5.0),",
      " ",
      NoReactInternals.ENABLE_V5_BREAKING_CHANGES ? /* @__PURE__ */ jsxs7("code", {
        children: [
          '"',
          "bt601",
          '"',
          ", "
        ]
      }) : /* @__PURE__ */ jsxs7(Fragment10, {
        children: [
          /* @__PURE__ */ jsxs7("code", {
            children: [
              '"',
              "bt601",
              '"'
            ]
          }),
          " ",
          "(same as",
          " ",
          /* @__PURE__ */ jsxs7("code", {
            children: [
              '"',
              "default",
              '"'
            ]
          }),
          ", since v4.0.424),",
          " ",
          /* @__PURE__ */ jsxs7("code", {
            children: [
              '"',
              "bt709",
              '"'
            ]
          }),
          " ",
          "(since v4.0.28),",
          " "
        ]
      }),
      /* @__PURE__ */ jsxs7("code", {
        children: [
          '"',
          "bt2020-ncl",
          '"'
        ]
      }),
      " ",
      "(since v4.0.88),",
      " ",
      /* @__PURE__ */ jsxs7("code", {
        children: [
          '"',
          "bt2020-cl",
          '"'
        ]
      }),
      " ",
      "(since v4.0.88), .",
      /* @__PURE__ */ jsx10("br", {}),
      "For best color accuracy, it is recommended to also use",
      " ",
      /* @__PURE__ */ jsxs7("code", {
        children: [
          '"',
          "png",
          '"'
        ]
      }),
      " ",
      "as the image format to have accurate color transformations throughout.",
      /* @__PURE__ */ jsx10("br", {}),
      "Only since v4.0.83, colorspace conversion is actually performed, previously it would only tag the metadata of the video."
    ]
  }),
  docLink: "https://www.remotion.dev/docs/renderer/render-media#colorspace",
  ssrName: "colorSpace",
  type: DEFAULT_COLOR_SPACE,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag12] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag12]
      };
    }
    if (colorSpace !== DEFAULT_COLOR_SPACE) {
      return {
        source: "config",
        value: colorSpace
      };
    }
    return {
      source: "default",
      value: DEFAULT_COLOR_SPACE
    };
  },
  setConfig: (value) => {
    colorSpace = value ?? DEFAULT_COLOR_SPACE;
  },
  id: cliFlag12
};

// src/options/concurrency.tsx
import { jsx as jsx11, jsxs as jsxs8, Fragment as Fragment11 } from "react/jsx-runtime";
var currentConcurrency = null;
var cliFlag13 = "concurrency";
var validateConcurrencyValue = (value, setting) => {
  if (typeof value === "undefined" || value === null) {
    return;
  }
  if (typeof value !== "number" && typeof value !== "string") {
    throw new Error(setting + " must a number or a string but is " + value);
  }
  if (typeof value === "number") {
    if (value % 1 !== 0) {
      throw new Error(setting + " must be an integer, but is " + value);
    }
  } else if (!/^\d+(\.\d+)?%$/.test(value)) {
    throw new Error(`${setting} must be a number or percentage, but is ${JSON.stringify(value)}`);
  }
};
var concurrencyOption = {
  name: "Concurrency",
  cliFlag: cliFlag13,
  description: () => /* @__PURE__ */ jsxs8(Fragment11, {
    children: [
      "How many CPU threads to use. Minimum 1. The maximum is the amount of threads you have (In Node.JS ",
      /* @__PURE__ */ jsx11("code", {
        children: "os.cpus().length"
      }),
      "). You can also provide a percentage value (e.g. ",
      /* @__PURE__ */ jsx11("code", {
        children: "50%"
      }),
      ")."
    ]
  }),
  ssrName: "concurrency",
  docLink: "https://www.remotion.dev/docs/config#setconcurrency",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag13] !== undefined) {
      const value = commandLine[cliFlag13];
      validateConcurrencyValue(value, "concurrency");
      return {
        source: "cli",
        value
      };
    }
    if (currentConcurrency !== null) {
      return {
        source: "config",
        value: currentConcurrency
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    validateConcurrencyValue(value, "Config.setConcurrency");
    currentConcurrency = value;
  },
  id: cliFlag13
};

// src/options/config.tsx
import { jsx as jsx12, Fragment as Fragment12 } from "react/jsx-runtime";
var cliFlag14 = "config";
var configOption = {
  name: "Config file",
  cliFlag: cliFlag14,
  description: () => /* @__PURE__ */ jsx12(Fragment12, {
    children: "Specify a location for the Remotion config file."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag14] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag14]
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: () => {
    throw new Error("setConfig is not supported. Pass --config via the CLI instead.");
  },
  type: "",
  id: cliFlag14
};

// src/options/crf.tsx
import { jsx as jsx13, Fragment as Fragment13 } from "react/jsx-runtime";
var currentCrf;
var validateCrf = (newCrf) => {
  if (typeof newCrf !== "number" && newCrf !== undefined) {
    throw new TypeError("The CRF must be a number or undefined.");
  }
};
var cliFlag15 = "crf";
var crfOption = {
  name: "CRF",
  cliFlag: cliFlag15,
  description: () => /* @__PURE__ */ jsx13(Fragment13, {
    children: "No matter which codec you end up using, there's always a tradeoff between file size and video quality. You can control it by setting the CRF (Constant Rate Factor). The lower the number, the better the quality, the higher the number, the smaller the file is – of course at the cost of quality."
  }),
  ssrName: "crf",
  docLink: "https://www.remotion.dev/docs/encoding/#controlling-quality-using-the-crf-setting",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag15] !== undefined) {
      validateCrf(commandLine[cliFlag15]);
      return {
        source: "cli",
        value: commandLine[cliFlag15]
      };
    }
    if (currentCrf !== null) {
      return {
        source: "config",
        value: currentCrf
      };
    }
    return {
      source: "default",
      value: undefined
    };
  },
  setConfig: (crf) => {
    validateCrf(crf);
    currentCrf = crf;
  },
  id: cliFlag15
};

// src/options/cross-site-isolation.tsx
import { jsx as jsx14, jsxs as jsxs9, Fragment as Fragment14 } from "react/jsx-runtime";
var enableCrossSiteIsolation = false;
var cliFlag16 = "cross-site-isolation";
var enableCrossSiteIsolationOption = {
  name: "Enable Cross-Site Isolation",
  cliFlag: cliFlag16,
  description: () => /* @__PURE__ */ jsxs9(Fragment14, {
    children: [
      "Enable Cross-Site Isolation in the Studio (sets Cross-Origin-Opener-Policy and Cross-Origin-Embedder-Policy HTTP headers, required for",
      " ",
      /* @__PURE__ */ jsx14("code", {
        children: "@remotion/whisper-web"
      }),
      ")."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setenablecrosssiteisolation",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag16] !== undefined) {
      return {
        value: commandLine[cliFlag16],
        source: "cli"
      };
    }
    return {
      value: enableCrossSiteIsolation,
      source: "config"
    };
  },
  setConfig(value) {
    enableCrossSiteIsolation = value;
  },
  id: cliFlag16
};

// src/options/dark-mode.tsx
import { jsx as jsx15, jsxs as jsxs10, Fragment as Fragment15 } from "react/jsx-runtime";
var DEFAULT_VALUE = false;
var darkMode = DEFAULT_VALUE;
var cliFlag17 = "dark-mode";
var darkModeOption = {
  name: "Dark Mode",
  cliFlag: cliFlag17,
  description: () => /* @__PURE__ */ jsxs10(Fragment15, {
    children: [
      "Whether Chromium should pretend to be in dark mode by emulating the media feature 'prefers-color-scheme: dark'. Default is",
      " ",
      /* @__PURE__ */ jsx15("code", {
        children: String(DEFAULT_VALUE)
      }),
      "."
    ]
  }),
  ssrName: "darkMode",
  docLink: "https://www.remotion.dev/docs/chromium-flags#--dark-mode",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag17] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag17]
      };
    }
    if (darkMode !== DEFAULT_VALUE) {
      return {
        source: "config",
        value: darkMode
      };
    }
    return {
      source: "default",
      value: DEFAULT_VALUE
    };
  },
  setConfig: (value) => {
    darkMode = value;
  },
  id: cliFlag17
};

// src/options/delete-after.tsx
import { jsx as jsx16, jsxs as jsxs11, Fragment as Fragment16 } from "react/jsx-runtime";
var cliFlag18 = "delete-after";
var deleteAfter = null;
var deleteAfterOption = {
  name: "Lambda render expiration",
  cliFlag: cliFlag18,
  description: () => {
    return /* @__PURE__ */ jsxs11(Fragment16, {
      children: [
        "Automatically delete the render after a certain period. Accepted values are ",
        /* @__PURE__ */ jsx16("code", {
          children: "1-day"
        }),
        ", ",
        /* @__PURE__ */ jsx16("code", {
          children: "3-days"
        }),
        ", ",
        /* @__PURE__ */ jsx16("code", {
          children: "7-days"
        }),
        " and",
        " ",
        /* @__PURE__ */ jsx16("code", {
          children: "30-days"
        }),
        ".",
        /* @__PURE__ */ jsx16("br", {}),
        " For this to work, your bucket needs to have",
        " ",
        /* @__PURE__ */ jsx16("a", {
          href: "/docs/lambda/autodelete",
          children: "lifecycles enabled"
        }),
        "."
      ]
    });
  },
  ssrName: "deleteAfter",
  docLink: "https://www.remotion.dev/docs/lambda/autodelete",
  type: "1-day",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag18] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag18]
      };
    }
    if (deleteAfter !== null) {
      return {
        source: "config",
        value: deleteAfter
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    deleteAfter = value;
  },
  id: cliFlag18
};

// src/options/disable-git-source.tsx
var DEFAULT2 = false;
var cliFlag19 = "disable-git-source";
var disableGitSourceOption = {
  cliFlag: cliFlag19,
  description: () => `Disables the Git Source being connected to the Remotion Studio. Clicking on stack traces and certain menu items will be disabled.`,
  docLink: "https://remotion.dev/docs/bundle",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag19]) {
      return {
        source: "cli",
        value: commandLine[cliFlag19]
      };
    }
    return {
      source: "default",
      value: DEFAULT2
    };
  },
  name: "Disable Git source",
  setConfig: () => {
    throw new Error("Not implemented");
  },
  ssrName: "disableGitSource",
  type: false,
  id: cliFlag19
};

// src/options/disable-web-security.tsx
import { jsx as jsx17, Fragment as Fragment17 } from "react/jsx-runtime";
var disableWebSecurity = false;
var cliFlag20 = "disable-web-security";
var disableWebSecurityOption = {
  name: "Disable web security",
  cliFlag: cliFlag20,
  description: () => /* @__PURE__ */ jsx17(Fragment17, {
    children: "This will most notably disable CORS in Chrome among other security features."
  }),
  ssrName: "disableWebSecurity",
  docLink: "https://www.remotion.dev/docs/chromium-flags#--disable-web-security",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag20] !== undefined) {
      return {
        source: "cli",
        value: Boolean(commandLine[cliFlag20])
      };
    }
    if (disableWebSecurity) {
      return {
        source: "config",
        value: disableWebSecurity
      };
    }
    return {
      source: "default",
      value: false
    };
  },
  setConfig: (value) => {
    disableWebSecurity = value;
  },
  id: cliFlag20
};

// src/options/disallow-parallel-encoding.tsx
import { jsx as jsx18, Fragment as Fragment18 } from "react/jsx-runtime";
var disallowParallelEncoding = false;
var cliFlag21 = "disallow-parallel-encoding";
var disallowParallelEncodingOption = {
  name: "Disallow parallel encoding",
  cliFlag: cliFlag21,
  description: () => /* @__PURE__ */ jsx18(Fragment18, {
    children: "Disallows the renderer from doing rendering frames and encoding at the same time. This makes the rendering process more memory-efficient, but possibly slower."
  }),
  ssrName: "disallowParallelEncoding",
  docLink: "https://www.remotion.dev/docs/config#setdisallowparallelencoding",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag21] !== undefined) {
      return {
        value: commandLine[cliFlag21],
        source: "cli"
      };
    }
    if (disallowParallelEncoding !== false) {
      return {
        value: disallowParallelEncoding,
        source: "config"
      };
    }
    return {
      value: false,
      source: "default"
    };
  },
  setConfig(value) {
    disallowParallelEncoding = value;
  },
  id: cliFlag21
};

// src/options/enable-lambda-insights.tsx
import { jsx as jsx19, jsxs as jsxs12, Fragment as Fragment19 } from "react/jsx-runtime";
var cliFlag22 = "enable-lambda-insights";
var option = false;
var enableLambdaInsights = {
  name: "Enable Lambda Insights",
  cliFlag: cliFlag22,
  description: () => /* @__PURE__ */ jsxs12(Fragment19, {
    children: [
      "Enable",
      " ",
      /* @__PURE__ */ jsx19("a", {
        href: "https://remotion.dev/docs/lambda/insights",
        children: "Lambda Insights in AWS CloudWatch"
      }),
      ". For this to work, you may have to update your role permission."
    ]
  }),
  ssrName: "enableLambdaInsights",
  docLink: "https://www.remotion.dev/docs/lambda/insights",
  type: false,
  setConfig: (value) => {
    option = value;
  },
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag22] !== undefined) {
      return {
        value: commandLine[cliFlag22],
        source: "cli"
      };
    }
    if (option) {
      return {
        value: option,
        source: "config"
      };
    }
    return {
      value: false,
      source: "default"
    };
  },
  id: cliFlag22
};

// src/options/enable-multiprocess-on-linux.tsx
import { jsx as jsx20, jsxs as jsxs13, Fragment as Fragment20 } from "react/jsx-runtime";
var DEFAULT_VALUE2 = true;
var multiProcessOnLinux = DEFAULT_VALUE2;
var cliFlag23 = "enable-multiprocess-on-linux";
var enableMultiprocessOnLinuxOption = {
  name: "Enable Multiprocess on Linux",
  cliFlag: cliFlag23,
  description: () => /* @__PURE__ */ jsxs13(Fragment20, {
    children: [
      "Removes the ",
      /* @__PURE__ */ jsx20("code", {
        children: "--single-process"
      }),
      " flag that gets passed to Chromium on Linux by default. This will make the render faster because multiple processes can be used, but may cause issues with some Linux distributions or if window server libraries are missing.",
      /* @__PURE__ */ jsx20("br", {}),
      "Default: ",
      /* @__PURE__ */ jsx20("code", {
        children: "false"
      }),
      " until v4.0.136, then ",
      /* @__PURE__ */ jsx20("code", {
        children: "true"
      }),
      " from v4.0.137 on because newer Chrome versions ",
      "don't",
      " allow rendering with the ",
      /* @__PURE__ */ jsx20("code", {
        children: "--single-process"
      }),
      " flag. ",
      /* @__PURE__ */ jsx20("br", {}),
      "This flag will be removed in Remotion v5.0."
    ]
  }),
  ssrName: "chromiumOptions.enableMultiprocessOnLinux",
  docLink: "https://www.remotion.dev/docs/chromium-flags",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag23] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag23]
      };
    }
    if (multiProcessOnLinux !== false) {
      return {
        source: "config",
        value: multiProcessOnLinux
      };
    }
    return {
      source: "default",
      value: DEFAULT_VALUE2
    };
  },
  setConfig: (value) => {
    multiProcessOnLinux = value;
  },
  id: cliFlag23
};

// src/options/encoding-buffer-size.tsx
import { jsx as jsx21, jsxs as jsxs14, Fragment as Fragment21 } from "react/jsx-runtime";
var encodingBufferSize = null;
var setEncodingBufferSize = (bitrate) => {
  encodingBufferSize = bitrate;
};
var cliFlag24 = "buffer-size";
var encodingBufferSizeOption = {
  name: "FFmpeg -bufsize flag",
  cliFlag: cliFlag24,
  description: () => /* @__PURE__ */ jsxs14(Fragment21, {
    children: [
      "The value for the ",
      /* @__PURE__ */ jsx21("code", {
        children: "-bufsize"
      }),
      " flag of FFmpeg. Should be used in conjunction with the encoding max rate flag."
    ]
  }),
  ssrName: "encodingBufferSize",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#encodingbuffersize",
  type: "",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag24] !== undefined) {
      return {
        value: commandLine[cliFlag24],
        source: "cli"
      };
    }
    if (encodingBufferSize !== null) {
      return {
        value: encodingBufferSize,
        source: "config"
      };
    }
    return {
      value: null,
      source: "default"
    };
  },
  setConfig: setEncodingBufferSize,
  id: cliFlag24
};

// src/options/encoding-max-rate.tsx
import { jsx as jsx22, jsxs as jsxs15, Fragment as Fragment22 } from "react/jsx-runtime";
var encodingMaxRate = null;
var cliFlag25 = "max-rate";
var encodingMaxRateOption = {
  name: "FFmpeg -maxrate flag",
  cliFlag: cliFlag25,
  description: () => /* @__PURE__ */ jsxs15(Fragment22, {
    children: [
      "The value for the ",
      /* @__PURE__ */ jsx22("code", {
        children: "-maxrate"
      }),
      " flag of FFmpeg. Should be used in conjunction with the encoding buffer size flag."
    ]
  }),
  ssrName: "encodingMaxRate",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#encodingmaxrate",
  type: "",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag25] !== undefined) {
      return {
        value: commandLine[cliFlag25],
        source: "cli"
      };
    }
    if (encodingMaxRate !== null) {
      return {
        value: encodingMaxRate,
        source: "config"
      };
    }
    return {
      value: null,
      source: "default"
    };
  },
  setConfig: (newMaxRate) => {
    encodingMaxRate = newMaxRate;
  },
  id: cliFlag25
};

// src/options/enforce-audio.tsx
import { jsx as jsx23, Fragment as Fragment23 } from "react/jsx-runtime";
var DEFAULT_ENFORCE_AUDIO_TRACK = false;
var enforceAudioTrackState = DEFAULT_ENFORCE_AUDIO_TRACK;
var cliFlag26 = "enforce-audio-track";
var enforceAudioOption = {
  name: "Enforce Audio Track",
  cliFlag: cliFlag26,
  description: () => /* @__PURE__ */ jsx23(Fragment23, {
    children: "Render a silent audio track if there would be none otherwise."
  }),
  ssrName: "enforceAudioTrack",
  docLink: "https://www.remotion.dev/docs/config#setenforceaudiotrack-",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag26]) {
      return {
        source: "cli",
        value: true
      };
    }
    if (enforceAudioTrackState !== DEFAULT_ENFORCE_AUDIO_TRACK) {
      return {
        source: "config",
        value: enforceAudioTrackState
      };
    }
    return {
      source: "default",
      value: DEFAULT_ENFORCE_AUDIO_TRACK
    };
  },
  setConfig: (value) => {
    enforceAudioTrackState = value;
  },
  id: cliFlag26
};

// src/options/env-file.tsx
import { jsx as jsx24, jsxs as jsxs16, Fragment as Fragment24 } from "react/jsx-runtime";
var cliFlag27 = "env-file";
var envFileLocation = null;
var envFileOption = {
  name: "Env File",
  cliFlag: cliFlag27,
  description: () => /* @__PURE__ */ jsxs16(Fragment24, {
    children: [
      "Specify a location for a dotenv file. Default ",
      /* @__PURE__ */ jsx24("code", {
        children: ".env"
      }),
      "."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/render#--env-file",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag27] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag27]
      };
    }
    if (envFileLocation !== null) {
      return {
        source: "config",
        value: envFileLocation
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    envFileLocation = value;
  },
  type: "",
  id: cliFlag27
};

// src/options/every-nth-frame.tsx
import { jsx as jsx25, jsxs as jsxs17, Fragment as Fragment25 } from "react/jsx-runtime";
var DEFAULT_EVERY_NTH_FRAME = 1;
var everyNthFrame = DEFAULT_EVERY_NTH_FRAME;
var cliFlag28 = "every-nth-frame";
var everyNthFrameOption = {
  name: "Every nth frame",
  cliFlag: cliFlag28,
  description: () => /* @__PURE__ */ jsxs17(Fragment25, {
    children: [
      "This option may only be set when rendering GIFs. It determines how many frames are rendered, while the other ones get skipped in order to lower the FPS of the GIF. For example, if the ",
      /* @__PURE__ */ jsx25("code", {
        children: "fps"
      }),
      " is 30, and",
      " ",
      /* @__PURE__ */ jsx25("code", {
        children: "everyNthFrame"
      }),
      " is 2, the FPS of the GIF is ",
      /* @__PURE__ */ jsx25("code", {
        children: "15"
      }),
      "."
    ]
  }),
  ssrName: "everyNthFrame",
  docLink: "https://www.remotion.dev/docs/config#seteverynthframe",
  type: DEFAULT_EVERY_NTH_FRAME,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag28] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag28]
      };
    }
    if (everyNthFrame !== DEFAULT_EVERY_NTH_FRAME) {
      return {
        source: "config",
        value: everyNthFrame
      };
    }
    return {
      source: "default",
      value: DEFAULT_EVERY_NTH_FRAME
    };
  },
  setConfig: (value) => {
    everyNthFrame = value;
  },
  id: cliFlag28
};

// src/options/experimental-client-side-rendering.tsx
import { jsx as jsx26, Fragment as Fragment26 } from "react/jsx-runtime";
var experimentalClientSideRenderingEnabled = false;
var cliFlag29 = "enable-experimental-client-side-rendering";
var experimentalClientSideRenderingOption = {
  name: "Enable Experimental Client-Side Rendering",
  cliFlag: cliFlag29,
  description: () => /* @__PURE__ */ jsx26(Fragment26, {
    children: "Enable WIP client-side rendering in the Remotion Studio. See https://www.remotion.dev/docs/client-side-rendering/ for notes."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/client-side-rendering",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag29] !== null) {
      return {
        value: commandLine[cliFlag29],
        source: "cli"
      };
    }
    return {
      value: experimentalClientSideRenderingEnabled,
      source: "config"
    };
  },
  setConfig(value) {
    experimentalClientSideRenderingEnabled = value;
  },
  id: cliFlag29
};

// src/options/experimental-visual-mode.tsx
import { jsx as jsx27, Fragment as Fragment27 } from "react/jsx-runtime";
var experimentalVisualModeEnabled = false;
var cliFlag30 = "experimental-visual-mode";
var experimentalVisualModeOption = {
  name: "Experimental Visual Mode",
  cliFlag: cliFlag30,
  description: () => /* @__PURE__ */ jsx27(Fragment27, {
    children: "Nothing here yet, but this is our playground for experiments."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setexperimentalvisualmode",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag30] !== null) {
      return {
        value: commandLine[cliFlag30],
        source: "cli"
      };
    }
    return {
      value: experimentalVisualModeEnabled,
      source: "config"
    };
  },
  setConfig(value) {
    experimentalVisualModeEnabled = value;
  },
  id: cliFlag30
};

// src/options/folder-expiry.tsx
import { jsx as jsx28, jsxs as jsxs18, Fragment as Fragment28 } from "react/jsx-runtime";
var enableFolderExpiry = null;
var cliFlag31 = "enable-folder-expiry";
var folderExpiryOption = {
  name: "Lambda render expiration",
  cliFlag: cliFlag31,
  description: () => {
    return /* @__PURE__ */ jsxs18(Fragment28, {
      children: [
        "When deploying sites, enable or disable S3 Lifecycle policies which allow for renders to auto-delete after a certain time. Default is",
        " ",
        /* @__PURE__ */ jsx28("code", {
          children: "null"
        }),
        ", which does not change any lifecycle policies of the S3 bucket. See: ",
        /* @__PURE__ */ jsx28("a", {
          href: "/docs/lambda/autodelete",
          children: "Lambda autodelete"
        }),
        "."
      ]
    });
  },
  ssrName: "enableFolderExpiry",
  docLink: "https://www.remotion.dev/docs/lambda/autodelete",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag31] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag31]
      };
    }
    if (enableFolderExpiry !== null) {
      return {
        source: "config",
        value: enableFolderExpiry
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    enableFolderExpiry = value;
  },
  id: cliFlag31
};

// src/options/for-seamless-aac-concatenation.tsx
import { jsx as jsx29, jsxs as jsxs19, Fragment as Fragment29 } from "react/jsx-runtime";
var DEFAULT3 = false;
var forSeamlessAacConcatenation = DEFAULT3;
var cliFlag32 = "for-seamless-aac-concatenation";
var forSeamlessAacConcatenationOption = {
  name: "For seamless AAC concatenation",
  cliFlag: cliFlag32,
  description: () => /* @__PURE__ */ jsxs19(Fragment29, {
    children: [
      "If enabled, the audio is trimmed to the nearest AAC frame, which is required for seamless concatenation of AAC files. This is a requirement if you later want to combine multiple video snippets seamlessly.",
      /* @__PURE__ */ jsx29("br", {}),
      /* @__PURE__ */ jsx29("br", {}),
      " This option is used internally. There is currently no documentation yet for to concatenate the audio chunks."
    ]
  }),
  docLink: "https://remotion.dev/docs/renderer",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag32]) {
      return {
        source: "cli",
        value: true
      };
    }
    if (forSeamlessAacConcatenation !== DEFAULT3) {
      return {
        source: "config",
        value: forSeamlessAacConcatenation
      };
    }
    return {
      source: "default",
      value: DEFAULT3
    };
  },
  setConfig: (value) => {
    forSeamlessAacConcatenation = value;
  },
  ssrName: "forSeamlessAacConcatenation",
  type: false,
  id: cliFlag32
};

// src/options/force-new-studio.tsx
import { jsx as jsx30, Fragment as Fragment30 } from "react/jsx-runtime";
var forceNewEnabled = false;
var cliFlag33 = "force-new";
var forceNewStudioOption = {
  name: "Force New Studio",
  cliFlag: cliFlag33,
  description: () => /* @__PURE__ */ jsx30(Fragment30, {
    children: "Forces starting a new Studio instance even if one is already running on the same port for the same project."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setforcenewstudioenabled",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag33] !== undefined) {
      return {
        value: commandLine[cliFlag33],
        source: "cli"
      };
    }
    return {
      value: forceNewEnabled,
      source: "config"
    };
  },
  setConfig(value) {
    forceNewEnabled = value;
  },
  id: cliFlag33
};

// src/frame-range.ts
var validateFrameRange = (frameRange) => {
  if (frameRange === null) {
    return;
  }
  if (typeof frameRange === "number") {
    if (frameRange < 0) {
      throw new TypeError("Frame must be a non-negative number, got " + frameRange);
    }
    if (!Number.isFinite(frameRange)) {
      throw new TypeError("Frame must be a finite number, got " + frameRange);
    }
    if (!Number.isInteger(frameRange)) {
      throw new Error(`Frame must be an integer, but got a float (${frameRange})`);
    }
    return;
  }
  if (Array.isArray(frameRange)) {
    if (frameRange.length !== 2) {
      throw new TypeError("Frame range must be a tuple, got an array with length " + frameRange.length);
    }
    const [first, second] = frameRange;
    if (typeof first !== "number") {
      throw new Error(`The first value of frame range must be a number, but got ${typeof first} (${JSON.stringify(first)})`);
    }
    if (!Number.isFinite(first)) {
      throw new TypeError("The first value of frame range must be finite, but got " + first);
    }
    if (!Number.isInteger(first)) {
      throw new Error(`The first value of frame range must be an integer, but got a float (${first})`);
    }
    if (first < 0) {
      throw new Error(`The first value of frame range must be non-negative, but got ${first}`);
    }
    if (second === null) {
      return;
    }
    if (typeof second !== "number") {
      throw new Error(`The second value of frame range must be a number or null, but got ${typeof second} (${JSON.stringify(second)})`);
    }
    if (!Number.isFinite(second)) {
      throw new TypeError("The second value of frame range must be finite, but got " + second);
    }
    if (!Number.isInteger(second)) {
      throw new Error(`The second value of frame range must be an integer, but got a float (${second})`);
    }
    if (second < 0) {
      throw new Error(`The second value of frame range must be non-negative, but got ${second}`);
    }
    if (second < first) {
      throw new Error("The second value of frame range must be not smaller than the first one, but got " + frameRange.join("-"));
    }
    return;
  }
  throw new TypeError("Frame range must be a number or a tuple of numbers, but got object of type " + typeof frameRange);
};

// src/options/frames.tsx
import { jsx as jsx31, jsxs as jsxs20, Fragment as Fragment31 } from "react/jsx-runtime";
var cliFlag34 = "frames";
var frameRange = null;
var parseFrameRangeFromCli = (newFrameRange) => {
  if (typeof newFrameRange === "number") {
    if (newFrameRange < 0) {
      return [0, Math.abs(newFrameRange)];
    }
    return newFrameRange;
  }
  if (typeof newFrameRange === "string") {
    if (newFrameRange.trim() === "") {
      throw new Error("--frames flag must be a single number, or 2 numbers separated by `-`");
    }
    const parts = newFrameRange.split("-");
    if (parts.length > 2 || parts.length <= 0) {
      throw new Error(`--frames flag must be a number or 2 numbers separated by '-', instead got ${parts.length} numbers`);
    }
    if (parts.length === 1) {
      const value = Number(parts[0]);
      if (isNaN(value)) {
        throw new Error("--frames flag must be a single number, or 2 numbers separated by `-`");
      }
      return value;
    }
    const [firstPart, secondPart] = parts;
    if (secondPart === "" && firstPart !== "") {
      const start = Number(firstPart);
      if (isNaN(start)) {
        throw new Error("--frames flag must be a single number, or 2 numbers separated by `-`");
      }
      return [start, null];
    }
    const parsed = parts.map((f) => Number(f));
    const [first, second] = parsed;
    for (const value of parsed) {
      if (isNaN(value)) {
        throw new Error("--frames flag must be a single number, or 2 numbers separated by `-`");
      }
    }
    if (second < first) {
      throw new Error("The second number of the --frames flag number should be greater or equal than first number");
    }
    return [first, second];
  }
  throw new Error("--frames flag must be a single number, or 2 numbers separated by `-`");
};
var framesOption = {
  name: "Frame Range",
  cliFlag: cliFlag34,
  description: () => /* @__PURE__ */ jsxs20(Fragment31, {
    children: [
      "Render a subset of a video. Pass a single number to render a still, or a range (e.g. ",
      /* @__PURE__ */ jsx31("code", {
        children: "0-9"
      }),
      ") to render a subset of frames. Pass",
      " ",
      /* @__PURE__ */ jsx31("code", {
        children: "100-"
      }),
      " to render from frame 100 to the end."
    ]
  }),
  ssrName: "frameRange",
  docLink: "https://www.remotion.dev/docs/config#setframerange",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag34] !== undefined) {
      const value = parseFrameRangeFromCli(commandLine[cliFlag34]);
      validateFrameRange(value);
      return {
        source: "cli",
        value
      };
    }
    return {
      source: "config",
      value: frameRange
    };
  },
  setConfig: (value) => {
    if (value !== null) {
      validateFrameRange(value);
    }
    frameRange = value;
  },
  id: cliFlag34
};

// src/options/gl.tsx
import { jsx as jsx32, jsxs as jsxs21, Fragment as Fragment32 } from "react/jsx-runtime";
var validOpenGlRenderers = [
  "swangle",
  "angle",
  "egl",
  "swiftshader",
  "vulkan",
  "angle-egl"
];
var DEFAULT_OPENGL_RENDERER = null;
var openGlRenderer = DEFAULT_OPENGL_RENDERER;
var AngleChangelog = () => {
  return /* @__PURE__ */ jsxs21("details", {
    style: { fontSize: "0.9em", marginBottom: "1em" },
    children: [
      /* @__PURE__ */ jsx32("summary", {
        children: "Changelog"
      }),
      /* @__PURE__ */ jsxs21("ul", {
        children: [
          /* @__PURE__ */ jsxs21("li", {
            children: [
              "From Remotion v2.6.7 until v3.0.7, the default for Remotion Lambda was",
              " ",
              /* @__PURE__ */ jsx32("code", {
                children: "swiftshader"
              }),
              ", but from v3.0.8 the default is",
              " ",
              /* @__PURE__ */ jsx32("code", {
                children: "swangle"
              }),
              " (Swiftshader on Angle) since Chrome 101 added support for it."
            ]
          }),
          /* @__PURE__ */ jsxs21("li", {
            children: [
              "From Remotion v2.4.3 until v2.6.6, the default was ",
              /* @__PURE__ */ jsx32("code", {
                children: "angle"
              }),
              ", however it turns out to have a small memory leak that could crash long Remotion renders."
            ]
          })
        ]
      })
    ]
  });
};
var cliFlag35 = "gl";
var glOption = {
  cliFlag: cliFlag35,
  docLink: "https://www.remotion.dev/docs/chromium-flags#--gl",
  name: "OpenGL renderer",
  type: "angle",
  ssrName: "gl",
  description: () => {
    return /* @__PURE__ */ jsxs21(Fragment32, {
      children: [
        /* @__PURE__ */ jsx32(AngleChangelog, {}),
        /* @__PURE__ */ jsxs21("p", {
          children: [
            "Select the OpenGL renderer backend for Chromium. ",
            /* @__PURE__ */ jsx32("br", {}),
            "Accepted values:"
          ]
        }),
        /* @__PURE__ */ jsxs21("ul", {
          children: [
            /* @__PURE__ */ jsx32("li", {
              children: /* @__PURE__ */ jsx32("code", {
                children: '"angle"'
              })
            }),
            /* @__PURE__ */ jsx32("li", {
              children: /* @__PURE__ */ jsx32("code", {
                children: '"egl"'
              })
            }),
            /* @__PURE__ */ jsx32("li", {
              children: /* @__PURE__ */ jsx32("code", {
                children: '"swiftshader"'
              })
            }),
            /* @__PURE__ */ jsx32("li", {
              children: /* @__PURE__ */ jsx32("code", {
                children: '"swangle"'
              })
            }),
            /* @__PURE__ */ jsxs21("li", {
              children: [
                /* @__PURE__ */ jsx32("code", {
                  children: '"vulkan"'
                }),
                " (",
                /* @__PURE__ */ jsx32("em", {
                  children: "from Remotion v4.0.41"
                }),
                ")"
              ]
            }),
            /* @__PURE__ */ jsxs21("li", {
              children: [
                /* @__PURE__ */ jsx32("code", {
                  children: '"angle-egl"'
                }),
                " (",
                /* @__PURE__ */ jsx32("em", {
                  children: "from Remotion v4.0.51"
                }),
                ")"
              ]
            })
          ]
        }),
        /* @__PURE__ */ jsxs21("p", {
          children: [
            "The default is ",
            /* @__PURE__ */ jsx32("code", {
              children: "null"
            }),
            ", letting Chrome decide, except on Lambda where the default is ",
            /* @__PURE__ */ jsx32("code", {
              children: '"swangle"'
            })
          ]
        })
      ]
    });
  },
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag35]) {
      validateOpenGlRenderer(commandLine[cliFlag35]);
      return {
        value: commandLine[cliFlag35],
        source: "cli"
      };
    }
    if (openGlRenderer !== DEFAULT_OPENGL_RENDERER) {
      return {
        value: openGlRenderer,
        source: "config"
      };
    }
    return {
      value: DEFAULT_OPENGL_RENDERER,
      source: "default"
    };
  },
  setConfig: (value) => {
    validateOpenGlRenderer(value);
    openGlRenderer = value;
  },
  id: cliFlag35
};
var validateOpenGlRenderer = (option2) => {
  if (option2 === null) {
    return null;
  }
  if (!validOpenGlRenderers.includes(option2)) {
    throw new TypeError(`${option2} is not a valid GL backend. Accepted values: ${validOpenGlRenderers.join(", ")}`);
  }
  return option2;
};

// src/options/hardware-acceleration.tsx
var hardwareAccelerationOptions = [
  "disable",
  "if-possible",
  "required"
];
var cliFlag36 = "hardware-acceleration";
var currentValue = null;
var hardwareAccelerationOption = {
  name: "Hardware Acceleration",
  cliFlag: cliFlag36,
  description: () => `
			One of
			${new Intl.ListFormat("en", { type: "disjunction" }).format(hardwareAccelerationOptions.map((a) => JSON.stringify(a)))}
			. Default "disable". Encode using a hardware-accelerated encoder if
			available. If set to "required" and no hardware-accelerated encoder is
			available, then the render will fail.
		`,
  ssrName: "hardwareAcceleration",
  docLink: "https://www.remotion.dev/docs/encoding",
  type: "disable",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag36] !== undefined) {
      const value = commandLine[cliFlag36];
      if (!hardwareAccelerationOptions.includes(value)) {
        throw new Error(`Invalid value for --${cliFlag36}: ${value}`);
      }
      return {
        source: "cli",
        value
      };
    }
    if (currentValue !== null) {
      return {
        source: "config",
        value: currentValue
      };
    }
    return {
      source: "default",
      value: "disable"
    };
  },
  setConfig: (value) => {
    if (!hardwareAccelerationOptions.includes(value)) {
      throw new Error(`Invalid value for --${cliFlag36}: ${value}`);
    }
    currentValue = value;
  },
  id: cliFlag36
};

// src/options/headless.tsx
import { jsx as jsx33, jsxs as jsxs22, Fragment as Fragment33 } from "react/jsx-runtime";
var DEFAULT4 = true;
var headlessMode = DEFAULT4;
var cliFlag37 = "disable-headless";
var headlessOption = {
  name: "Disable Headless Mode",
  cliFlag: cliFlag37,
  description: () => /* @__PURE__ */ jsxs22(Fragment33, {
    children: [
      "Deprecated - will be removed in 5.0.0. With the migration to",
      " ",
      /* @__PURE__ */ jsx33("a", {
        href: "/docs/miscellaneous/chrome-headless-shell",
        children: "Chrome Headless Shell"
      }),
      ", this option is not functional anymore.",
      /* @__PURE__ */ jsx33("br", {}),
      /* @__PURE__ */ jsx33("br", {}),
      " If disabled, the render will open an actual Chrome window where you can see the render happen. The default is headless mode."
    ]
  }),
  ssrName: "headless",
  docLink: "https://www.remotion.dev/docs/chromium-flags#--disable-headless",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag37] !== undefined) {
      return {
        source: "cli",
        value: !commandLine[cliFlag37]
      };
    }
    if (headlessMode !== DEFAULT4) {
      return {
        source: "config",
        value: headlessMode
      };
    }
    return {
      source: "default",
      value: headlessMode
    };
  },
  setConfig: (value) => {
    headlessMode = value;
  },
  id: cliFlag37
};

// src/options/ignore-certificate-errors.tsx
import { jsx as jsx34, Fragment as Fragment34 } from "react/jsx-runtime";
var ignoreCertificateErrors = false;
var cliFlag38 = "ignore-certificate-errors";
var ignoreCertificateErrorsOption = {
  name: "Ignore certificate errors",
  cliFlag: cliFlag38,
  description: () => /* @__PURE__ */ jsx34(Fragment34, {
    children: "Results in invalid SSL certificates in Chrome, such as self-signed ones, being ignored."
  }),
  ssrName: "ignoreCertificateErrors",
  docLink: "https://www.remotion.dev/docs/chromium-flags#--ignore-certificate-errors",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag38] !== undefined) {
      return {
        source: "cli",
        value: Boolean(commandLine[cliFlag38])
      };
    }
    if (ignoreCertificateErrors) {
      return {
        source: "config",
        value: ignoreCertificateErrors
      };
    }
    return {
      source: "default",
      value: false
    };
  },
  setConfig: (value) => {
    ignoreCertificateErrors = value;
  },
  id: cliFlag38
};

// src/options/image-sequence.tsx
import { jsx as jsx35, jsxs as jsxs23, Fragment as Fragment35 } from "react/jsx-runtime";
var cliFlag39 = "sequence";
var imageSequence = false;
var imageSequenceOption = {
  name: "Image Sequence",
  cliFlag: cliFlag39,
  description: () => /* @__PURE__ */ jsxs23(Fragment35, {
    children: [
      "Pass this flag to output an image sequence instead of a video. The default image format is JPEG. See",
      " ",
      /* @__PURE__ */ jsx35("a", {
        href: "/docs/config#setimagesequence",
        children: /* @__PURE__ */ jsx35("code", {
          children: "setImageSequence()"
        })
      }),
      " ",
      "for more details."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setimagesequence",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag39] !== undefined) {
      return {
        source: "cli",
        value: Boolean(commandLine[cliFlag39])
      };
    }
    return {
      source: imageSequence ? "config" : "default",
      value: imageSequence
    };
  },
  setConfig: (value) => {
    imageSequence = value;
  },
  type: false,
  id: cliFlag39
};

// src/options/image-sequence-pattern.tsx
import { jsx as jsx36, jsxs as jsxs24, Fragment as Fragment36 } from "react/jsx-runtime";
var cliFlag40 = "image-sequence-pattern";
var currentImageSequencePattern = null;
var imageSequencePatternOption = {
  name: "Image Sequence Pattern",
  cliFlag: cliFlag40,
  ssrName: "imageSequencePattern",
  description: () => /* @__PURE__ */ jsxs24(Fragment36, {
    children: [
      "Pattern for naming image sequence files. Supports ",
      /* @__PURE__ */ jsx36("code", {
        children: "[frame]"
      }),
      " for the zero-padded frame number and ",
      /* @__PURE__ */ jsx36("code", {
        children: "[ext]"
      }),
      " for the file extension."
    ]
  }),
  docLink: null,
  type: "string",
  getValue: ({ commandLine }) => {
    if (currentImageSequencePattern !== null) {
      return {
        value: currentImageSequencePattern,
        source: "config"
      };
    }
    return {
      value: commandLine[cliFlag40],
      source: "cli"
    };
  },
  setConfig: (pattern) => {
    currentImageSequencePattern = pattern;
  },
  id: cliFlag40
};

// src/options/ipv4.tsx
import { jsx as jsx37, Fragment as Fragment37 } from "react/jsx-runtime";
var forceIPv4 = false;
var cliFlag41 = "ipv4";
var ipv4Option = {
  name: "IPv4",
  cliFlag: cliFlag41,
  description: () => /* @__PURE__ */ jsx37(Fragment37, {
    children: "Forces Remotion to bind to an IPv4 interface for the Studio server."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/studio",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag41] !== undefined) {
      return {
        value: commandLine[cliFlag41],
        source: "cli"
      };
    }
    return {
      value: forceIPv4,
      source: "config"
    };
  },
  setConfig(value) {
    forceIPv4 = value;
  },
  id: cliFlag41
};

// src/options/is-production.tsx
import { jsx as jsx38, jsxs as jsxs25, Fragment as Fragment38 } from "react/jsx-runtime";
var cliFlag42 = "is-production";
var currentIsProductionKey = null;
var isProductionOption = {
  name: "Is Production",
  cliFlag: cliFlag42,
  description: () => /* @__PURE__ */ jsxs25(Fragment38, {
    children: [
      "Pass ",
      /* @__PURE__ */ jsx38("code", {
        children: "false"
      }),
      " if this a development render to not count it as a billable render on remotion.pro. Only can be used in conjuction with",
      " ",
      /* @__PURE__ */ jsx38("code", {
        children: "licenseKey"
      }),
      "."
    ]
  }),
  ssrName: "isProduction",
  docLink: "https://www.remotion.dev/docs/licensing",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag42] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag42]
      };
    }
    if (currentIsProductionKey !== null) {
      return {
        source: "config",
        value: currentIsProductionKey
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value) => {
    currentIsProductionKey = value;
  },
  type: false,
  id: cliFlag42
};

// src/options/jpeg-quality.tsx
import { jsx as jsx39, Fragment as Fragment39 } from "react/jsx-runtime";
var defaultValue = DEFAULT_JPEG_QUALITY;
var quality = defaultValue;
var setJpegQuality = (q) => {
  validateJpegQuality(q);
  if (q === 0 || q === undefined) {
    quality = defaultValue;
    return;
  }
  quality = q;
};
var cliFlag43 = "jpeg-quality";
var jpegQualityOption = {
  name: "JPEG Quality",
  cliFlag: cliFlag43,
  description: () => /* @__PURE__ */ jsx39(Fragment39, {
    children: "Sets the quality of the generated JPEG images. Must be an integer between 0 and 100. Default: 80."
  }),
  ssrName: "jpegQuality",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#jpeg-quality",
  type: 0,
  setConfig: setJpegQuality,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag43] !== undefined) {
      validateJpegQuality(commandLine[cliFlag43]);
      return {
        source: "cli",
        value: commandLine[cliFlag43]
      };
    }
    if (quality !== defaultValue) {
      return {
        source: "config",
        value: quality
      };
    }
    return {
      source: "default",
      value: defaultValue
    };
  },
  id: cliFlag43
};

// src/options/keyboard-shortcuts.tsx
import { jsx as jsx40, Fragment as Fragment40 } from "react/jsx-runtime";
var keyboardShortcutsEnabled = true;
var cliFlag44 = "disable-keyboard-shortcuts";
var keyboardShortcutsOption = {
  name: "Disable or Enable keyboard shortcuts",
  cliFlag: cliFlag44,
  description: () => /* @__PURE__ */ jsx40(Fragment40, {
    children: "Enable or disable keyboard shortcuts in the Remotion Studio."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setkeyboardshortcutsenabled",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag44] !== undefined) {
      keyboardShortcutsEnabled = commandLine[cliFlag44] === false;
      return {
        value: keyboardShortcutsEnabled,
        source: "cli"
      };
    }
    return {
      value: keyboardShortcutsEnabled,
      source: "config"
    };
  },
  setConfig(value) {
    keyboardShortcutsEnabled = value;
  },
  id: cliFlag44
};

// src/options/latency-hint.tsx
import { jsx as jsx41, jsxs as jsxs26, Fragment as Fragment41 } from "react/jsx-runtime";
var cliFlag45 = "audio-latency-hint";
var value = null;
var audioLatencyHintOption = {
  name: "Audio Latency Hint",
  cliFlag: cliFlag45,
  description: () => /* @__PURE__ */ jsxs26(Fragment41, {
    children: [
      "Sets the",
      " ",
      /* @__PURE__ */ jsx41("a", {
        href: "https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/AudioContext",
        children: "audio latency"
      }),
      " ",
      "hint for the global ",
      /* @__PURE__ */ jsx41("code", {
        children: "AudioContext"
      }),
      " context that Remotion uses to play audio.",
      /* @__PURE__ */ jsx41("br", {}),
      "Possible values: ",
      /* @__PURE__ */ jsx41("code", {
        children: "interactive"
      }),
      ", ",
      /* @__PURE__ */ jsx41("code", {
        children: "balanced"
      }),
      ",",
      " ",
      /* @__PURE__ */ jsx41("code", {
        children: "playback"
      })
    ]
  }),
  ssrName: "audioLatencyHint",
  docLink: "https://www.remotion.dev/docs/renderer/render-media",
  type: "interactive",
  getValue: ({ commandLine }) => {
    const val = commandLine[cliFlag45];
    if (typeof val !== "undefined") {
      return { value: val, source: "cli" };
    }
    if (value !== null) {
      return { value, source: "config" };
    }
    return { value: null, source: "default" };
  },
  setConfig: (profile) => {
    value = profile;
  },
  id: cliFlag45
};

// src/options/license-key.tsx
import { jsx as jsx42, jsxs as jsxs27, Fragment as Fragment42 } from "react/jsx-runtime";
var currentLicenseKey = null;
var cliFlag46 = "license-key";
var licenseKeyOption = {
  name: "License key",
  cliFlag: cliFlag46,
  description: () => /* @__PURE__ */ jsxs27(Fragment42, {
    children: [
      "License key for sending a usage event using",
      " ",
      /* @__PURE__ */ jsx42("code", {
        children: "@remotion/licensing"
      }),
      "."
    ]
  }),
  ssrName: "licenseKey",
  docLink: "https://www.remotion.dev/docs/licensing",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag46] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag46]
      };
    }
    return {
      source: "default",
      value: currentLicenseKey
    };
  },
  setConfig: (value2) => {
    currentLicenseKey = value2;
  },
  id: cliFlag46
};

// src/options/log-level.tsx
import { jsx as jsx43, jsxs as jsxs28, Fragment as Fragment43 } from "react/jsx-runtime";
var logLevel = "info";
var cliFlag47 = "log";
var logLevelOption = {
  cliFlag: cliFlag47,
  name: "Log Level",
  ssrName: "logLevel",
  description: () => /* @__PURE__ */ jsxs28(Fragment43, {
    children: [
      "One of ",
      /* @__PURE__ */ jsx43("code", {
        children: "trace"
      }),
      ", ",
      /* @__PURE__ */ jsx43("code", {
        children: "verbose"
      }),
      ", ",
      /* @__PURE__ */ jsx43("code", {
        children: "info"
      }),
      ",",
      " ",
      /* @__PURE__ */ jsx43("code", {
        children: "warn"
      }),
      ", ",
      /* @__PURE__ */ jsx43("code", {
        children: "error"
      }),
      ".",
      /* @__PURE__ */ jsx43("br", {}),
      " Determines how much info is being logged to the console.",
      /* @__PURE__ */ jsx43("br", {}),
      /* @__PURE__ */ jsx43("br", {}),
      " Default ",
      /* @__PURE__ */ jsx43("code", {
        children: "info"
      }),
      "."
    ]
  }),
  docLink: "https://www.remotion.dev/docs/troubleshooting/debug-failed-render",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag47]) {
      if (!isValidLogLevel(commandLine[cliFlag47])) {
        throw new Error(`Invalid \`--log\` value passed. Accepted values: ${logLevels.map((l) => `'${l}'`).join(", ")}.`);
      }
      return { value: commandLine[cliFlag47], source: "cli" };
    }
    if (logLevel !== "info") {
      return { value: logLevel, source: "config" };
    }
    return { value: "info", source: "default" };
  },
  setConfig: (newLogLevel) => {
    logLevel = newLogLevel;
  },
  type: "error",
  id: cliFlag47
};

// src/options/metadata.tsx
import { jsx as jsx44, jsxs as jsxs29, Fragment as Fragment44 } from "react/jsx-runtime";
var metadata = {};
var cliFlag48 = "metadata";
var metadataOption = {
  name: "Metadata",
  cliFlag: cliFlag48,
  description: (mode) => {
    if (mode === "ssr") {
      return /* @__PURE__ */ jsxs29(Fragment44, {
        children: [
          "An object containing metadata to be embedded in the video. See",
          " ",
          /* @__PURE__ */ jsx44("a", {
            href: "/docs/metadata",
            children: "here"
          }),
          " for which metadata is accepted."
        ]
      });
    }
    return /* @__PURE__ */ jsxs29(Fragment44, {
      children: [
        "Metadata to be embedded in the video. See",
        " ",
        /* @__PURE__ */ jsx44("a", {
          href: "/docs/metadata",
          children: "here"
        }),
        " for which metadata is accepted.",
        /* @__PURE__ */ jsx44("br", {}),
        "The parameter must be in the format of ",
        /* @__PURE__ */ jsx44("code", {
          children: "--metadata key=value"
        }),
        " ",
        "and can be passed multiple times."
      ]
    });
  },
  docLink: "https://www.remotion.dev/docs/metadata",
  type: {},
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag48] !== undefined) {
      const val = commandLine[cliFlag48];
      const array = typeof val === "string" ? [val] : val;
      const keyValues = array.map((a) => {
        if (!a.includes("=")) {
          throw new Error(`"metadata" must be in the format of key=value, but got ${a}`);
        }
        const splitted = a.split("=");
        if (splitted.length !== 2) {
          throw new Error(`"metadata" must be in the format of key=value, but got ${a}`);
        }
        return [splitted[0], splitted[1]];
      });
      const value2 = Object.fromEntries(keyValues);
      return {
        source: "config",
        value: value2
      };
    }
    return {
      source: "config",
      value: metadata
    };
  },
  setConfig: (newMetadata) => {
    metadata = newMetadata;
  },
  ssrName: "metadata",
  id: cliFlag48
};

// src/options/mute.tsx
import { jsx as jsx45, Fragment as Fragment45 } from "react/jsx-runtime";
var DEFAULT_MUTED_STATE = false;
var mutedState = DEFAULT_MUTED_STATE;
var cliFlag49 = "muted";
var mutedOption = {
  name: "Muted",
  cliFlag: cliFlag49,
  description: () => /* @__PURE__ */ jsx45(Fragment45, {
    children: "The Audio of the video will be omitted."
  }),
  ssrName: "muted",
  docLink: "https://www.remotion.dev/docs/audio/muting",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag49] !== null) {
      return {
        source: "cli",
        value: commandLine[cliFlag49]
      };
    }
    if (mutedState !== DEFAULT_MUTED_STATE) {
      return {
        source: "config",
        value: mutedState
      };
    }
    return {
      source: "config",
      value: mutedState
    };
  },
  setConfig: () => {
    mutedState = true;
  },
  id: cliFlag49
};

// src/options/no-open.tsx
import { jsx as jsx46, Fragment as Fragment46 } from "react/jsx-runtime";
var shouldOpenBrowser = true;
var cliFlag50 = "no-open";
var noOpenOption = {
  name: "Disable browser auto-open",
  cliFlag: cliFlag50,
  description: () => /* @__PURE__ */ jsx46(Fragment46, {
    children: "If specified, Remotion will not open a browser window when starting the Studio."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/studio#--no-open",
  type: false,
  getValue: ({ commandLine }) => {
    const cliValue = commandLine.open;
    if (cliValue === false) {
      return { value: true, source: "cli" };
    }
    if (!shouldOpenBrowser) {
      return { value: true, source: "config" };
    }
    return { value: false, source: "default" };
  },
  setConfig: (shouldOpen) => {
    shouldOpenBrowser = shouldOpen;
  },
  id: cliFlag50
};

// src/options/number-of-gif-loops.tsx
import { jsx as jsx47, jsxs as jsxs30, Fragment as Fragment47 } from "react/jsx-runtime";
var currentLoop = null;
var validate = (newLoop) => {
  if (newLoop !== null && typeof newLoop !== "number") {
    throw new Error("--number-of-gif-loops flag must be a number.");
  }
};
var cliFlag51 = "number-of-gif-loops";
var numberOfGifLoopsOption = {
  name: "Number of GIF loops",
  cliFlag: cliFlag51,
  description: () => {
    return /* @__PURE__ */ jsxs30(Fragment47, {
      children: [
        "Allows you to set the number of loops as follows:",
        /* @__PURE__ */ jsxs30("ul", {
          children: [
            /* @__PURE__ */ jsxs30("li", {
              children: [
                /* @__PURE__ */ jsx47("code", {
                  children: "null"
                }),
                " (or omitting in the CLI) plays the GIF indefinitely."
              ]
            }),
            /* @__PURE__ */ jsxs30("li", {
              children: [
                /* @__PURE__ */ jsx47("code", {
                  children: "0"
                }),
                " disables looping"
              ]
            }),
            /* @__PURE__ */ jsxs30("li", {
              children: [
                /* @__PURE__ */ jsx47("code", {
                  children: "1"
                }),
                " loops the GIF once (plays twice in total)"
              ]
            }),
            /* @__PURE__ */ jsxs30("li", {
              children: [
                /* @__PURE__ */ jsx47("code", {
                  children: "2"
                }),
                " loops the GIF twice (plays three times in total) and so on."
              ]
            })
          ]
        })
      ]
    });
  },
  ssrName: "numberOfGifLoops",
  docLink: "https://www.remotion.dev/docs/render-as-gif#changing-the-number-of-loops",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag51] !== undefined) {
      validate(commandLine[cliFlag51]);
      return {
        value: commandLine[cliFlag51],
        source: "cli"
      };
    }
    if (currentLoop !== null) {
      return {
        value: currentLoop,
        source: "config"
      };
    }
    return {
      value: null,
      source: "default"
    };
  },
  setConfig: (newLoop) => {
    validate(newLoop);
    currentLoop = newLoop;
  },
  id: cliFlag51
};

// src/options/number-of-shared-audio-tags.tsx
import { jsx as jsx48, jsxs as jsxs31, Fragment as Fragment48 } from "react/jsx-runtime";
var numberOfSharedAudioTags = 0;
var cliFlag52 = "number-of-shared-audio-tags";
var numberOfSharedAudioTagsOption = {
  name: "Number of shared audio tags",
  cliFlag: cliFlag52,
  description: () => /* @__PURE__ */ jsxs31(Fragment48, {
    children: [
      "Set number of shared audio tags. See",
      " ",
      /* @__PURE__ */ jsx48("a", {
        href: "https://www.remotion.dev/docs/player/autoplay#using-the-numberofsharedaudiotags-prop",
        children: "Using the numberOfSharedAudioTags prop"
      }),
      " ",
      "for more information."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setnumberofsharedaudiotags",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag52] !== undefined) {
      return {
        value: commandLine[cliFlag52],
        source: "cli"
      };
    }
    return {
      value: numberOfSharedAudioTags,
      source: "config"
    };
  },
  setConfig(value2) {
    numberOfSharedAudioTags = value2;
  },
  id: cliFlag52
};

// src/options/offthreadvideo-cache-size.tsx
import { jsx as jsx49, jsxs as jsxs32, Fragment as Fragment49 } from "react/jsx-runtime";
var offthreadVideoCacheSizeInBytes = null;
var cliFlag53 = "offthreadvideo-cache-size-in-bytes";
var offthreadVideoCacheSizeInBytesOption = {
  name: "OffthreadVideo cache size",
  cliFlag: cliFlag53,
  description: () => /* @__PURE__ */ jsxs32(Fragment49, {
    children: [
      "From v4.0, Remotion has a cache for",
      " ",
      /* @__PURE__ */ jsx49("a", {
        href: "https://remotion.dev/docs/offthreadvideo",
        children: /* @__PURE__ */ jsx49("code", {
          children: "<OffthreadVideo>"
        })
      }),
      " ",
      "frames. The default is ",
      /* @__PURE__ */ jsx49("code", {
        children: "null"
      }),
      ", corresponding to half of the system memory available when the render starts.",
      /* @__PURE__ */ jsx49("br", {}),
      " This option allows to override the size of the cache. The higher it is, the faster the render will be, but the more memory will be used.",
      /* @__PURE__ */ jsx49("br", {}),
      "The used value will be printed when running in verbose mode.",
      /* @__PURE__ */ jsx49("br", {}),
      "Default: ",
      /* @__PURE__ */ jsx49("code", {
        children: "null"
      })
    ]
  }),
  ssrName: "offthreadVideoCacheSizeInBytes",
  docLink: "https://www.remotion.dev/docs/offthreadvideo",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag53] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag53]
      };
    }
    if (offthreadVideoCacheSizeInBytes !== null) {
      return {
        source: "config",
        value: offthreadVideoCacheSizeInBytes
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (size) => {
    offthreadVideoCacheSizeInBytes = size ?? null;
  },
  id: cliFlag53
};

// src/options/offthreadvideo-threads.tsx
import { jsx as jsx50, jsxs as jsxs33, Fragment as Fragment50 } from "react/jsx-runtime";
var value2 = null;
var cliFlag54 = "offthreadvideo-video-threads";
var offthreadVideoThreadsOption = {
  name: "OffthreadVideo threads",
  cliFlag: cliFlag54,
  description: () => /* @__PURE__ */ jsxs33(Fragment50, {
    children: [
      "The number of threads that",
      /* @__PURE__ */ jsx50("a", {
        href: "https://remotion.dev/docs/offthreadvideo",
        children: /* @__PURE__ */ jsx50("code", {
          children: "<OffthreadVideo>"
        })
      }),
      " ",
      "can start to extract frames. The default is",
      " ",
      DEFAULT_RENDER_FRAMES_OFFTHREAD_VIDEO_THREADS,
      ". Increase carefully, as too many threads may cause instability."
    ]
  }),
  ssrName: "offthreadVideoThreads",
  docLink: "https://www.remotion.dev/docs/offthreadvideo",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag54] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag54]
      };
    }
    if (value2 !== null) {
      return {
        source: "config",
        value: value2
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (size) => {
    value2 = size ?? null;
  },
  id: cliFlag54
};
var DEFAULT_RENDER_FRAMES_OFFTHREAD_VIDEO_THREADS = 2;

// src/options/on-browser-download.tsx
import { jsx as jsx51, jsxs as jsxs34, Fragment as Fragment51 } from "react/jsx-runtime";
var cliFlag55 = "on-browser-download";
var onBrowserDownloadOption = {
  name: "Browser download callback function",
  cliFlag: cliFlag55,
  description: () => /* @__PURE__ */ jsxs34(Fragment51, {
    children: [
      "Gets called when no compatible local browser is detected on the system and this API needs to download a browser. Return a callback to observe progress.",
      " ",
      /* @__PURE__ */ jsx51("a", {
        href: "/docs/renderer/ensure-browser#onbrowserdownload",
        children: "See here for how to use this option."
      })
    ]
  }),
  ssrName: "onBrowserDownload",
  docLink: "https://www.remotion.dev/docs/renderer/ensure-browser",
  type: undefined,
  getValue: () => {
    throw new Error("does not support config file");
  },
  setConfig: () => {
    throw new Error("does not support config file");
  },
  id: cliFlag55
};

// src/options/out-dir.tsx
import { jsx as jsx52, jsxs as jsxs35, Fragment as Fragment52 } from "react/jsx-runtime";
var cliFlag56 = "out-dir";
var currentOutDir = null;
var outDirOption = {
  name: "Output Directory",
  cliFlag: cliFlag56,
  description: () => {
    return /* @__PURE__ */ jsxs35(Fragment52, {
      children: [
        "Define the location of the resulting bundle. By default it is a folder called ",
        /* @__PURE__ */ jsx52("code", {
          children: "build"
        }),
        ", adjacent to the",
        " ",
        /* @__PURE__ */ jsx52("a", {
          href: "/docs/terminology/remotion-root",
          children: "Remotion Root"
        }),
        "."
      ]
    });
  },
  ssrName: "outDir",
  docLink: "https://www.remotion.dev/docs/cli/bundle#--out-dir",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag56] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag56]
      };
    }
    if (currentOutDir !== null) {
      return {
        source: "config",
        value: currentOutDir
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    currentOutDir = value3;
  },
  type: "",
  id: cliFlag56
};

// src/validate.ts
import { NoReactInternals as NoReactInternals2 } from "remotion/no-react";
var validateFps = NoReactInternals2.validateFps;
var validateDimension = NoReactInternals2.validateDimension;
var validateDurationInFrames = NoReactInternals2.validateDurationInFrames;

// src/options/override-duration.tsx
import { jsx as jsx53, Fragment as Fragment53 } from "react/jsx-runtime";
var currentDuration = null;
var cliFlag57 = "duration";
var overrideDurationOption = {
  name: "Override Duration",
  cliFlag: cliFlag57,
  description: () => /* @__PURE__ */ jsx53(Fragment53, {
    children: "Overrides the duration in frames of the composition."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#overrideduration",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag57] !== undefined) {
      const value3 = commandLine[cliFlag57];
      validateDurationInFrames(value3, {
        component: "in --duration flag",
        allowFloats: false
      });
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentDuration !== null) {
      return {
        source: "config",
        value: currentDuration
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (duration) => {
    validateDurationInFrames(duration, {
      component: "in Config.overrideDuration()",
      allowFloats: false
    });
    currentDuration = duration;
  },
  id: cliFlag57
};

// src/options/override-fps.tsx
import { jsx as jsx54, Fragment as Fragment54 } from "react/jsx-runtime";
var currentFps = null;
var cliFlag58 = "fps";
var overrideFpsOption = {
  name: "Override FPS",
  cliFlag: cliFlag58,
  description: () => /* @__PURE__ */ jsx54(Fragment54, {
    children: "Overrides the frames per second of the composition."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#overridefps",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag58] !== undefined) {
      const value3 = commandLine[cliFlag58];
      validateFps(value3, "in --fps flag", false);
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentFps !== null) {
      return {
        source: "config",
        value: currentFps
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (fps) => {
    validateFps(fps, "in Config.overrideFps()", false);
    currentFps = fps;
  },
  id: cliFlag58
};

// src/options/override-height.tsx
import { jsx as jsx55, Fragment as Fragment55 } from "react/jsx-runtime";
var currentHeight = null;
var cliFlag59 = "height";
var overrideHeightOption = {
  name: "Override Height",
  cliFlag: cliFlag59,
  description: () => /* @__PURE__ */ jsx55(Fragment55, {
    children: "Overrides the height of the composition."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#overrideheight",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag59] !== undefined) {
      const value3 = commandLine[cliFlag59];
      validateDimension(value3, "height", "in --height flag");
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentHeight !== null) {
      return {
        source: "config",
        value: currentHeight
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (height) => {
    validateDimension(height, "height", "in Config.overrideHeight()");
    currentHeight = height;
  },
  id: cliFlag59
};

// src/options/override-width.tsx
import { jsx as jsx56, Fragment as Fragment56 } from "react/jsx-runtime";
var currentWidth = null;
var cliFlag60 = "width";
var overrideWidthOption = {
  name: "Override Width",
  cliFlag: cliFlag60,
  description: () => /* @__PURE__ */ jsx56(Fragment56, {
    children: "Overrides the width of the composition."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#overridewidth",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag60] !== undefined) {
      const value3 = commandLine[cliFlag60];
      validateDimension(value3, "width", "in --width flag");
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentWidth !== null) {
      return {
        source: "config",
        value: currentWidth
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (width) => {
    validateDimension(width, "width", "in Config.overrideWidth()");
    currentWidth = width;
  },
  id: cliFlag60
};

// src/options/overwrite.tsx
import { jsx as jsx57, jsxs as jsxs36, Fragment as Fragment57 } from "react/jsx-runtime";
var shouldOverwrite = null;
var cliFlag61 = "overwrite";
var validate2 = (value3) => {
  if (typeof value3 !== "boolean") {
    throw new Error(`overwriteExisting must be a boolean but got ${typeof value3} (${value3})`);
  }
};
var overwriteOption = {
  name: "Overwrite output",
  cliFlag: cliFlag61,
  description: () => /* @__PURE__ */ jsxs36(Fragment57, {
    children: [
      "If set to ",
      /* @__PURE__ */ jsx57("code", {
        children: "false"
      }),
      ", will prevent rendering to a path that already exists. Default is ",
      /* @__PURE__ */ jsx57("code", {
        children: "true"
      }),
      "."
    ]
  }),
  ssrName: "overwrite",
  docLink: "https://www.remotion.dev/docs/config#setoverwriteoutput",
  type: false,
  getValue: ({ commandLine }, defaultValue2) => {
    if (commandLine[cliFlag61] !== undefined) {
      validate2(commandLine[cliFlag61]);
      return {
        source: "cli",
        value: commandLine[cliFlag61]
      };
    }
    if (shouldOverwrite !== null) {
      return {
        source: "config",
        value: shouldOverwrite
      };
    }
    return {
      source: "default",
      value: defaultValue2
    };
  },
  setConfig: (value3) => {
    validate2(value3);
    shouldOverwrite = value3;
  },
  id: cliFlag61
};

// src/options/package-manager.tsx
import { jsx as jsx58, jsxs as jsxs37, Fragment as Fragment58 } from "react/jsx-runtime";
var cliFlag62 = "package-manager";
var currentPackageManager = null;
var packageManagerOption = {
  name: "Package Manager",
  cliFlag: cliFlag62,
  description: () => {
    return /* @__PURE__ */ jsxs37(Fragment58, {
      children: [
        "Forces a specific package manager to be used. By default, Remotion will auto-detect the package manager based on your lockfile.",
        /* @__PURE__ */ jsx58("br", {}),
        "Acceptable values are ",
        /* @__PURE__ */ jsx58("code", {
          children: "npm"
        }),
        ", ",
        /* @__PURE__ */ jsx58("code", {
          children: "yarn"
        }),
        ",",
        " ",
        /* @__PURE__ */ jsx58("code", {
          children: "pnpm"
        }),
        " and ",
        /* @__PURE__ */ jsx58("code", {
          children: "bun"
        }),
        "."
      ]
    });
  },
  ssrName: "packageManager",
  docLink: "https://www.remotion.dev/docs/cli/upgrade#--package-manager",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag62] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag62]
      };
    }
    if (currentPackageManager !== null) {
      return {
        source: "config",
        value: currentPackageManager
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    currentPackageManager = value3;
  },
  type: "",
  id: cliFlag62
};

// src/pixel-format.ts
var validPixelFormats = [
  "yuv420p",
  "yuva420p",
  "yuv422p",
  "yuv444p",
  "yuv420p10le",
  "yuv422p10le",
  "yuv444p10le",
  "yuva444p10le"
];
var DEFAULT_PIXEL_FORMAT = "yuv420p";
var validPixelFormatsForCodec = (codec) => {
  if (codec === "vp8" || codec === "vp9") {
    return validPixelFormats;
  }
  return validPixelFormats.filter((format) => format !== "yuva420p");
};

// src/options/pixel-format.tsx
import { jsx as jsx59, jsxs as jsxs38, Fragment as Fragment59 } from "react/jsx-runtime";
var currentPixelFormat = DEFAULT_PIXEL_FORMAT;
var cliFlag63 = "pixel-format";
var pixelFormatOption = {
  name: "Pixel format",
  cliFlag: cliFlag63,
  description: () => /* @__PURE__ */ jsxs38(Fragment59, {
    children: [
      "Sets the pixel format in FFmpeg. See",
      " ",
      /* @__PURE__ */ jsx59("a", {
        href: "https://trac.ffmpeg.org/wiki/Chroma%20Subsampling",
        children: "the FFmpeg docs for an explanation"
      }),
      ". Acceptable values: ",
      validPixelFormats.map((f) => `"${f}"`).join(", "),
      "."
    ]
  }),
  ssrName: "pixelFormat",
  docLink: "https://www.remotion.dev/docs/config#setpixelformat",
  type: DEFAULT_PIXEL_FORMAT,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag63] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag63]
      };
    }
    if (currentPixelFormat !== DEFAULT_PIXEL_FORMAT) {
      return {
        source: "config",
        value: currentPixelFormat
      };
    }
    return {
      source: "default",
      value: DEFAULT_PIXEL_FORMAT
    };
  },
  setConfig: (value3) => {
    if (!validPixelFormats.includes(value3)) {
      throw new TypeError(`Value ${value3} is not valid as a pixel format.`);
    }
    currentPixelFormat = value3;
  },
  id: cliFlag63
};

// src/options/port.tsx
import { jsx as jsx60, Fragment as Fragment60 } from "react/jsx-runtime";
var cliFlag64 = "port";
var currentPort = null;
var portOption = {
  name: "Port",
  cliFlag: cliFlag64,
  description: () => /* @__PURE__ */ jsx60(Fragment60, {
    children: "Set a custom HTTP server port for the Studio or the render process. If not defined, Remotion will try to find a free port."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setstudioport",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag64] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag64]
      };
    }
    if (currentPort !== null) {
      return {
        source: "config",
        value: currentPort
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    currentPort = value3;
  },
  type: 0,
  id: cliFlag64
};

// src/options/prefer-lossless.tsx
import { jsx as jsx61, jsxs as jsxs39, Fragment as Fragment61 } from "react/jsx-runtime";
var cliFlag65 = "prefer-lossless";
var input = false;
var preferLosslessAudioOption = {
  name: "Prefer lossless",
  cliFlag: cliFlag65,
  description: () => /* @__PURE__ */ jsxs39(Fragment61, {
    children: [
      "Uses a lossless audio codec, if one is available for the codec. If you set",
      /* @__PURE__ */ jsx61("code", {
        children: "audioCodec"
      }),
      ", it takes priority over",
      " ",
      /* @__PURE__ */ jsx61("code", {
        children: "preferLossless"
      }),
      "."
    ]
  }),
  docLink: "https://www.remotion.dev/docs/encoding",
  type: false,
  ssrName: "preferLossless",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag65]) {
      return { value: true, source: "cli" };
    }
    if (input === true) {
      return { value: true, source: "config" };
    }
    return { value: false, source: "default" };
  },
  setConfig: (val) => {
    input = val;
  },
  id: cliFlag65
};

// src/options/props.tsx
import { jsx as jsx62, jsxs as jsxs40, Fragment as Fragment62 } from "react/jsx-runtime";
var cliFlag66 = "props";
var propsOption = {
  name: "Input Props",
  cliFlag: cliFlag66,
  description: () => /* @__PURE__ */ jsxs40(Fragment62, {
    children: [
      "Input Props to pass to the selected composition of your video. Must be a serialized JSON string (",
      /* @__PURE__ */ jsxs40("code", {
        children: [
          "--props='",
          "{",
          '"hello": "world"',
          "}",
          "'"
        ]
      }),
      ") or a path to a JSON file (",
      /* @__PURE__ */ jsx62("code", {
        children: "./path/to/props.json"
      }),
      ")."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/passing-props#passing-input-props-in-the-cli",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag66] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag66]
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: () => {
    throw new Error("setProps is not supported. Pass --props via the CLI instead.");
  },
  type: "",
  id: cliFlag66
};

// src/options/prores-profile.tsx
import { jsx as jsx63, jsxs as jsxs41, Fragment as Fragment63 } from "react/jsx-runtime";
var validProResProfiles = [
  "4444-xq",
  "4444",
  "hq",
  "standard",
  "light",
  "proxy"
];
var proResProfile;
var cliFlag67 = "prores-profile";
var proResProfileOption = {
  name: "ProRes profile",
  cliFlag: cliFlag67,
  description: () => /* @__PURE__ */ jsxs41(Fragment63, {
    children: [
      "Set the ProRes profile. This option is only valid if the codec has been set to ",
      /* @__PURE__ */ jsx63("code", {
        children: "prores"
      }),
      ". Possible values:",
      " ",
      validProResProfiles.map((p) => `"${p}"`).join(", "),
      ". Default:",
      " ",
      /* @__PURE__ */ jsx63("code", {
        children: '"hq"'
      }),
      ". See",
      " ",
      /* @__PURE__ */ jsx63("a", {
        href: "https://video.stackexchange.com/a/14715",
        children: "here"
      }),
      " for an explanation of possible values."
    ]
  }),
  ssrName: "proResProfile",
  docLink: "https://www.remotion.dev/docs/config#setproresprofile",
  type: undefined,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag67] !== undefined) {
      return {
        source: "cli",
        value: String(commandLine[cliFlag67])
      };
    }
    if (proResProfile !== undefined) {
      return {
        source: "config",
        value: proResProfile
      };
    }
    return {
      source: "default",
      value: undefined
    };
  },
  setConfig: (value3) => {
    proResProfile = value3;
  },
  id: cliFlag67
};

// src/options/public-dir.tsx
import { jsx as jsx64, jsxs as jsxs42, Fragment as Fragment64 } from "react/jsx-runtime";
var cliFlag68 = "public-dir";
var currentPublicDir = null;
var publicDirOption = {
  name: "Public Directory",
  cliFlag: cliFlag68,
  description: () => {
    return /* @__PURE__ */ jsxs42(Fragment64, {
      children: [
        "Define the location of the",
        " ",
        /* @__PURE__ */ jsx64("a", {
          href: "/docs/terminology/public-dir",
          children: /* @__PURE__ */ jsx64("code", {
            children: "public/ directory"
          })
        }),
        ". If not defined, Remotion will assume the location is the `public` folder in your Remotion root."
      ]
    });
  },
  ssrName: "publicDir",
  docLink: "https://www.remotion.dev/docs/terminology/public-dir",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag68] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag68]
      };
    }
    if (currentPublicDir !== null) {
      return {
        source: "config",
        value: currentPublicDir
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    currentPublicDir = value3;
  },
  type: "",
  id: cliFlag68
};

// src/options/public-license-key.tsx
import { jsx as jsx65, jsxs as jsxs43, Fragment as Fragment65 } from "react/jsx-runtime";
var cliFlag69 = "public-license-key";
var currentPublicLicenseKey = null;
var publicLicenseKeyOption = {
  name: "Public License Key",
  cliFlag: cliFlag69,
  description: () => /* @__PURE__ */ jsxs43(Fragment65, {
    children: [
      'The public license key for your company license, obtained from the "Usage" tab on ',
      /* @__PURE__ */ jsx65("a", {
        href: "https://remotion.pro/dashboard",
        children: "remotion.pro"
      }),
      '. If you are eligible for the free license, pass "free-license".'
    ]
  }),
  ssrName: "publicLicenseKey",
  docLink: "https://www.remotion.dev/docs/licensing",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag69] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag69]
      };
    }
    if (currentPublicLicenseKey !== null) {
      return {
        source: "config",
        value: currentPublicLicenseKey
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    if (value3 && value3 !== "free-license" && !value3.startsWith("rm_pub_")) {
      throw new Error('Invalid public license key. It must start with "rm_pub_" or be "free-license".');
    }
    currentPublicLicenseKey = value3;
  },
  type: null,
  id: cliFlag69
};

// src/options/public-path.tsx
import { jsx as jsx66, jsxs as jsxs44, Fragment as Fragment66 } from "react/jsx-runtime";
var cliFlag70 = "public-path";
var currentPublicPath = null;
var publicPathOption = {
  name: "Public Path",
  cliFlag: cliFlag70,
  description: () => {
    return /* @__PURE__ */ jsxs44(Fragment66, {
      children: [
        "The path of the URL where the bundle is going to be hosted. By default it is ",
        /* @__PURE__ */ jsx66("code", {
          children: "/"
        }),
        ", meaning that the bundle is going to be hosted at the root of the domain (e.g. ",
        /* @__PURE__ */ jsx66("code", {
          children: "https://localhost:3000/"
        }),
        "). If you are deploying to a subdirectory (e.g. ",
        /* @__PURE__ */ jsx66("code", {
          children: "/sites/my-site/"
        }),
        "), you should set this to the subdirectory."
      ]
    });
  },
  ssrName: "publicPath",
  docLink: "https://www.remotion.dev/docs/renderer",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag70] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag70]
      };
    }
    if (currentPublicPath !== null) {
      return {
        source: "config",
        value: currentPublicPath
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    currentPublicPath = value3;
  },
  type: "",
  id: cliFlag70
};

// src/options/repro.tsx
import { jsx as jsx67, Fragment as Fragment67 } from "react/jsx-runtime";
var enableRepro = false;
var setRepro = (should) => {
  enableRepro = should;
};
var cliFlag71 = "repro";
var reproOption = {
  name: "Create reproduction",
  cliFlag: cliFlag71,
  description: () => /* @__PURE__ */ jsx67(Fragment67, {
    children: "Create a ZIP that you can submit to Remotion if asked for a reproduction."
  }),
  ssrName: "repro",
  docLink: "https://www.remotion.dev/docs/render-media#repro",
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag71] !== undefined) {
      return {
        value: commandLine[cliFlag71],
        source: "cli"
      };
    }
    if (enableRepro) {
      return {
        value: enableRepro,
        source: "config"
      };
    }
    return {
      value: false,
      source: "default"
    };
  },
  setConfig: setRepro,
  id: cliFlag71
};

// src/options/rspack.tsx
import { jsx as jsx68, Fragment as Fragment68 } from "react/jsx-runtime";
var rspackEnabled = false;
var cliFlag72 = "experimental-rspack";
var rspackOption = {
  name: "Experimental Rspack",
  cliFlag: cliFlag72,
  description: () => /* @__PURE__ */ jsx68(Fragment68, {
    children: "Uses Rspack instead of Webpack as the bundler for the Studio or bundle."
  }),
  ssrName: null,
  docLink: null,
  type: false,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag72] !== undefined) {
      rspackEnabled = true;
      return {
        value: commandLine[cliFlag72],
        source: "cli"
      };
    }
    return {
      value: rspackEnabled,
      source: "config"
    };
  },
  setConfig(value3) {
    rspackEnabled = value3;
  },
  id: cliFlag72
};

// src/options/runs.tsx
import { jsx as jsx69, jsxs as jsxs45, Fragment as Fragment69 } from "react/jsx-runtime";
var DEFAULT_RUNS = 3;
var currentRuns = DEFAULT_RUNS;
var cliFlag73 = "runs";
var runsOption = {
  name: "Benchmark runs",
  cliFlag: cliFlag73,
  description: () => /* @__PURE__ */ jsxs45(Fragment69, {
    children: [
      "Specify how many times the video should be rendered during a benchmark. Default ",
      /* @__PURE__ */ jsx69("code", {
        children: DEFAULT_RUNS
      }),
      "."
    ]
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/benchmark#--runs",
  type: DEFAULT_RUNS,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag73] !== undefined) {
      const value3 = Number(commandLine[cliFlag73]);
      if (isNaN(value3) || value3 < 1) {
        throw new Error(`--runs must be a positive number, but got ${commandLine[cliFlag73]}`);
      }
      return { value: value3, source: "cli" };
    }
    if (currentRuns !== DEFAULT_RUNS) {
      return { value: currentRuns, source: "config" };
    }
    return { value: DEFAULT_RUNS, source: "default" };
  },
  setConfig: (value3) => {
    if (typeof value3 !== "number" || isNaN(value3) || value3 < 1) {
      throw new Error(`Runs must be a positive number, but got ${value3}`);
    }
    currentRuns = value3;
  },
  id: cliFlag73
};

// src/options/scale.tsx
import { jsx as jsx70, jsxs as jsxs46, Fragment as Fragment70 } from "react/jsx-runtime";
var currentScale = 1;
var cliFlag74 = "scale";
var validateScale = (value3) => {
  if (typeof value3 !== "number") {
    throw new Error("scale must be a number.");
  }
};
var scaleOption = {
  name: "Scale",
  cliFlag: cliFlag74,
  description: () => /* @__PURE__ */ jsxs46(Fragment70, {
    children: [
      "Scales the output dimensions by a factor. For example, a 1280x720px frame will become a 1920x1080px frame with a scale factor of ",
      /* @__PURE__ */ jsx70("code", {
        children: "1.5"
      }),
      ". See ",
      /* @__PURE__ */ jsx70("a", {
        href: "https://www.remotion.dev/docs/scaling",
        children: "Scaling"
      }),
      " for more details."
    ]
  }),
  ssrName: "scale",
  docLink: "https://www.remotion.dev/docs/scaling",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag74] !== undefined) {
      validateScale(commandLine[cliFlag74]);
      return {
        source: "cli",
        value: commandLine[cliFlag74]
      };
    }
    if (currentScale !== null) {
      return {
        source: "config",
        value: currentScale
      };
    }
    return {
      source: "default",
      value: 1
    };
  },
  setConfig: (scale) => {
    currentScale = scale;
  },
  id: cliFlag74
};

// src/options/still-frame.tsx
import { NoReactInternals as NoReactInternals3 } from "remotion/no-react";
import { jsx as jsx71, jsxs as jsxs47, Fragment as Fragment71 } from "react/jsx-runtime";
var cliFlag75 = "frame";
var currentFrame = null;
var validate3 = (frame) => {
  NoReactInternals3.validateFrame({
    frame,
    durationInFrames: Infinity,
    allowFloats: false
  });
};
var stillFrameOption = {
  name: "Frame",
  cliFlag: cliFlag75,
  description: () => /* @__PURE__ */ jsxs47(Fragment71, {
    children: [
      "Which frame should be rendered when rendering a still. Default",
      " ",
      /* @__PURE__ */ jsx71("code", {
        children: "0"
      }),
      ". From v3.2.27, negative values are allowed, with",
      " ",
      /* @__PURE__ */ jsx71("code", {
        children: "-1"
      }),
      " being the last frame."
    ]
  }),
  ssrName: "frame",
  docLink: "https://www.remotion.dev/docs/cli/still#--frame",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag75] !== undefined) {
      const frame = Number(commandLine[cliFlag75]);
      validate3(frame);
      return {
        source: "cli",
        value: frame
      };
    }
    if (currentFrame !== null) {
      return {
        source: "config",
        value: currentFrame
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    if (value3 !== null) {
      validate3(value3);
    }
    currentFrame = value3;
  },
  type: 0,
  id: cliFlag75
};

// src/options/still-image-format.tsx
import { jsx as jsx72, jsxs as jsxs48, Fragment as Fragment72 } from "react/jsx-runtime";
var currentStillImageFormat = null;
var cliFlag76 = "image-format";
var stillImageFormatOption = {
  name: "Still Image Format",
  cliFlag: cliFlag76,
  description: () => /* @__PURE__ */ jsxs48(Fragment72, {
    children: [
      "The image format to use when rendering a still. Must be one of",
      " ",
      validStillImageFormats.map((f) => `"${f}"`).join(", "),
      ". Default:",
      " ",
      /* @__PURE__ */ jsx72("code", {
        children: '"png"'
      }),
      "."
    ]
  }),
  ssrName: "imageFormat",
  docLink: "https://www.remotion.dev/docs/renderer/render-still#imageformat",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag76] !== undefined) {
      const value3 = commandLine[cliFlag76];
      if (!validStillImageFormats.includes(value3)) {
        throw new Error(`Invalid still image format: ${value3}. Must be one of: ${validStillImageFormats.join(", ")}`);
      }
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentStillImageFormat !== null) {
      return {
        source: "config",
        value: currentStillImageFormat
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    if (value3 === null) {
      currentStillImageFormat = null;
      return;
    }
    if (!validStillImageFormats.includes(value3)) {
      throw new TypeError([
        `Value ${value3} is not valid as a still image format.`,
        value3 === "jpg" ? 'Did you mean "jpeg"?' : null
      ].filter(Boolean).join(" "));
    }
    currentStillImageFormat = value3;
  },
  id: "still-image-format"
};

// src/options/throw-if-site-exists.tsx
var DEFAULT5 = false;
var cliFlag77 = "throw-if-site-exists";
var throwIfSiteExistsOption = {
  cliFlag: cliFlag77,
  description: () => `Prevents accidential update of an existing site. If there are any files in the subfolder where the site should be placed, the function will throw.`,
  docLink: "https://remotion.dev/docs/lambda/deploy-site",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag77]) {
      return {
        source: "cli",
        value: commandLine[cliFlag77]
      };
    }
    return {
      source: "default",
      value: DEFAULT5
    };
  },
  name: "Throw if site exists",
  setConfig: () => {
    throw new Error("Not implemented");
  },
  ssrName: "throwIfSiteExists",
  type: false,
  id: cliFlag77
};

// src/options/timeout.tsx
import { jsx as jsx73, jsxs as jsxs49, Fragment as Fragment73 } from "react/jsx-runtime";
var currentTimeout = DEFAULT_TIMEOUT;
var validate4 = (value3) => {
  if (typeof value3 !== "number") {
    throw new Error("--timeout flag / setDelayRenderTimeoutInMilliseconds() must be a number, but got " + JSON.stringify(value3));
  }
};
var cliFlag78 = "timeout";
var delayRenderTimeoutInMillisecondsOption = {
  name: "delayRender() timeout",
  cliFlag: cliFlag78,
  description: () => /* @__PURE__ */ jsxs49(Fragment73, {
    children: [
      "A number describing how long the render may take to resolve all",
      " ",
      /* @__PURE__ */ jsx73("a", {
        href: "https://remotion.dev/docs/delay-render",
        children: /* @__PURE__ */ jsx73("code", {
          children: "delayRender()"
        })
      }),
      " ",
      "calls",
      " ",
      /* @__PURE__ */ jsx73("a", {
        style: { fontSize: "inherit" },
        href: "https://remotion.dev/docs/timeout",
        children: "before it times out"
      }),
      ". Default: ",
      /* @__PURE__ */ jsx73("code", {
        children: "30000"
      })
    ]
  }),
  ssrName: "timeoutInMilliseconds",
  docLink: "https://www.remotion.dev/docs/timeout",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag78] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag78]
      };
    }
    if (currentTimeout !== null) {
      validate4(currentTimeout);
      return {
        source: "config",
        value: currentTimeout
      };
    }
    return {
      source: "default",
      value: DEFAULT_TIMEOUT
    };
  },
  setConfig: (value3) => {
    validate4(value3);
    currentTimeout = value3;
  },
  id: cliFlag78
};

// src/options/user-agent.tsx
import { jsx as jsx74, Fragment as Fragment74 } from "react/jsx-runtime";
var userAgent = null;
var cliFlag79 = "user-agent";
var userAgentOption = {
  name: "User agent",
  cliFlag: cliFlag79,
  description: () => /* @__PURE__ */ jsx74(Fragment74, {
    children: "Lets you set a custom user agent that the headless Chrome browser assumes."
  }),
  ssrName: "userAgent",
  docLink: "https://www.remotion.dev/docs/chromium-flags#--user-agent",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag79] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag79]
      };
    }
    if (userAgent !== null) {
      return {
        source: "config",
        value: userAgent
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    userAgent = value3;
  },
  id: cliFlag79
};

// src/options/version-flag.tsx
import { jsx as jsx75, Fragment as Fragment75 } from "react/jsx-runtime";
var cliFlag80 = "version";
var versionFlagOption = {
  name: "Version",
  cliFlag: cliFlag80,
  description: () => /* @__PURE__ */ jsx75(Fragment75, {
    children: "Install a specific version. Also enables downgrading to an older version."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/cli/upgrade#--version",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag80] !== undefined) {
      return {
        source: "cli",
        value: String(commandLine[cliFlag80])
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: () => {
    throw new Error("Cannot set version via config file");
  },
  type: "",
  id: cliFlag80
};

// src/options/video-bitrate.tsx
import { jsx as jsx76, jsxs as jsxs50, Fragment as Fragment76 } from "react/jsx-runtime";
var videoBitrate = null;
var cliFlag81 = "video-bitrate";
var videoBitrateOption = {
  name: "Video Bitrate",
  cliFlag: cliFlag81,
  description: () => /* @__PURE__ */ jsxs50(Fragment76, {
    children: [
      "Specify the target bitrate for the generated video. The syntax for FFmpeg",
      "'",
      "s",
      /* @__PURE__ */ jsx76("code", {
        children: "-b:v"
      }),
      " parameter should be used. FFmpeg may encode the video in a way that will not result in the exact video bitrate specified. Example values: ",
      /* @__PURE__ */ jsx76("code", {
        children: "512K"
      }),
      " for 512 kbps, ",
      /* @__PURE__ */ jsx76("code", {
        children: "1M"
      }),
      " for 1 Mbps."
    ]
  }),
  ssrName: "videoBitrate",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#videobitrate",
  type: "",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag81] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag81]
      };
    }
    if (videoBitrate !== null) {
      return {
        source: "config",
        value: videoBitrate
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (bitrate) => {
    videoBitrate = bitrate;
  },
  id: cliFlag81
};

// src/options/video-cache-size.tsx
import { jsx as jsx77, jsxs as jsxs51, Fragment as Fragment77 } from "react/jsx-runtime";
var mediaCacheSizeInBytes = null;
var cliFlag82 = "media-cache-size-in-bytes";
var mediaCacheSizeInBytesOption = {
  name: "@remotion/media cache size",
  cliFlag: cliFlag82,
  description: () => /* @__PURE__ */ jsxs51(Fragment77, {
    children: [
      "Specify the maximum size of the cache that ",
      /* @__PURE__ */ jsx77("code", {
        children: "<Video>"
      }),
      " and",
      " ",
      /* @__PURE__ */ jsx77("code", {
        children: "<Audio>"
      }),
      " from ",
      /* @__PURE__ */ jsx77("code", {
        children: "@remotion/media"
      }),
      " may use combined, in bytes. ",
      /* @__PURE__ */ jsx77("br", {}),
      "The default is half of the available system memory when the render starts."
    ]
  }),
  ssrName: "mediaCacheSizeInBytes",
  docLink: "https://www.remotion.dev/docs/media/video#setting-the-cache-size",
  type: 0,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag82] !== undefined) {
      return {
        source: "cli",
        value: commandLine[cliFlag82]
      };
    }
    if (mediaCacheSizeInBytes !== null) {
      return {
        source: "config",
        value: mediaCacheSizeInBytes
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (size) => {
    mediaCacheSizeInBytes = size ?? null;
  },
  id: cliFlag82
};

// src/path-normalize.ts
var SLASH = 47;
var DOT = 46;
var assertPath = (path) => {
  const t = typeof path;
  if (t !== "string") {
    throw new TypeError(`Expected a string, got a ${t}`);
  }
};
var posixNormalize = (path, allowAboveRoot) => {
  let res = "";
  let lastSegmentLength = 0;
  let lastSlash = -1;
  let dots = 0;
  let code;
  for (let i = 0;i <= path.length; ++i) {
    if (i < path.length) {
      code = path.charCodeAt(i);
    } else if (code === SLASH) {
      break;
    } else {
      code = SLASH;
    }
    if (code === SLASH) {
      if (lastSlash === i - 1 || dots === 1) {} else if (lastSlash !== i - 1 && dots === 2) {
        if (res.length < 2 || lastSegmentLength !== 2 || res.charCodeAt(res.length - 1) !== DOT || res.charCodeAt(res.length - 2) !== DOT) {
          if (res.length > 2) {
            const lastSlashIndex = res.lastIndexOf("/");
            if (lastSlashIndex !== res.length - 1) {
              if (lastSlashIndex === -1) {
                res = "";
                lastSegmentLength = 0;
              } else {
                res = res.slice(0, lastSlashIndex);
                lastSegmentLength = res.length - 1 - res.lastIndexOf("/");
              }
              lastSlash = i;
              dots = 0;
              continue;
            }
          } else if (res.length === 2 || res.length === 1) {
            res = "";
            lastSegmentLength = 0;
            lastSlash = i;
            dots = 0;
            continue;
          }
        }
        if (allowAboveRoot) {
          if (res.length > 0) {
            res += "/..";
          } else {
            res = "..";
          }
          lastSegmentLength = 2;
        }
      } else {
        if (res.length > 0) {
          res += "/" + path.slice(lastSlash + 1, i);
        } else {
          res = path.slice(lastSlash + 1, i);
        }
        lastSegmentLength = i - lastSlash - 1;
      }
      lastSlash = i;
      dots = 0;
    } else if (code === DOT && dots !== -1) {
      ++dots;
    } else {
      dots = -1;
    }
  }
  return res;
};
var decode = (s) => {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
};
var pathNormalize = (p) => {
  assertPath(p);
  let path = p;
  if (path.length === 0) {
    return ".";
  }
  const isAbsolute = path.charCodeAt(0) === SLASH;
  const trailingSeparator = path.charCodeAt(path.length - 1) === SLASH;
  path = decode(path);
  path = posixNormalize(path, !isAbsolute);
  if (path.length === 0 && !isAbsolute) {
    path = ".";
  }
  if (path.length > 0 && trailingSeparator) {
    path += "/";
  }
  if (isAbsolute) {
    return "/" + path;
  }
  return path;
};

// src/get-extension-of-filename.ts
var getExtensionOfFilename = (filename) => {
  if (filename === null) {
    return null;
  }
  const filenameArr = pathNormalize(filename).split(".");
  const hasExtension = filenameArr.length >= 2;
  const filenameArrLength = filenameArr.length;
  const extension = hasExtension ? filenameArr[filenameArrLength - 1] : null;
  return extension;
};

// src/options/video-codec.tsx
import { jsx as jsx78, Fragment as Fragment78 } from "react/jsx-runtime";
var codec;
var setCodec = (newCodec) => {
  if (newCodec === undefined) {
    codec = undefined;
    return;
  }
  if (!validCodecs.includes(newCodec)) {
    throw new Error(`Codec must be one of the following: ${validCodecs.join(", ")}, but got ${newCodec}`);
  }
  codec = newCodec;
};
var getOutputCodecOrUndefined = () => {
  return codec;
};
var deriveCodecsFromFilename = (extension) => {
  if (extension === null) {
    return { possible: [], default: null };
  }
  return {
    default: defaultCodecsForFileExtension[extension] ?? null,
    possible: makeFileExtensionMap()[extension] ?? []
  };
};
var cliFlag83 = "codec";
var videoCodecOption = {
  name: "Codec",
  cliFlag: cliFlag83,
  description: () => /* @__PURE__ */ jsx78(Fragment78, {
    children: "H264 works well in most cases, but sometimes it's worth going for a different codec. WebM achieves higher compression but is slower to render. WebM, GIF and ProRes support transparency."
  }),
  ssrName: "codec",
  docLink: "https://www.remotion.dev/docs/encoding/#choosing-a-codec",
  type: "",
  getValue: ({ commandLine }, {
    compositionCodec,
    configFile,
    downloadName,
    outName,
    uiCodec
  }) => {
    if (uiCodec) {
      return { value: uiCodec, source: "via UI" };
    }
    const downloadNameExtension = getExtensionOfFilename(downloadName);
    const outNameExtension = getExtensionOfFilename(outName);
    const derivedDownloadCodecs = deriveCodecsFromFilename(downloadNameExtension);
    const derivedOutNameCodecs = deriveCodecsFromFilename(outNameExtension);
    if (derivedDownloadCodecs.possible.length > 0 && derivedOutNameCodecs.possible.length > 0 && derivedDownloadCodecs.possible.join("") !== derivedOutNameCodecs.possible.join("")) {
      throw new TypeError(`The download name is ${downloadName} but the output name is ${outName}. The file extensions must match`);
    }
    const cliArgument = commandLine[cliFlag83];
    if (cliArgument) {
      if (derivedDownloadCodecs.possible.length > 0 && derivedDownloadCodecs.possible.indexOf(cliArgument) === -1) {
        throw new TypeError(`The download name is ${downloadName} but --codec=${cliArgument} was passed. The download name implies a codec of ${derivedDownloadCodecs.possible.join(" or ")} which does not align with the --codec flag.`);
      }
      if (derivedOutNameCodecs.possible.length > 0 && derivedOutNameCodecs.possible.indexOf(cliArgument) === -1) {
        throw new TypeError(`The out name is ${outName} but --codec=${cliArgument} was passed. The out name implies a codec of ${derivedOutNameCodecs.possible.join(" or ")} which does not align with the --codec flag.`);
      }
      return { value: cliArgument, source: "from --codec flag" };
    }
    if (derivedDownloadCodecs.possible.length > 0) {
      return {
        value: derivedDownloadCodecs.default,
        source: "derived from download name"
      };
    }
    if (derivedOutNameCodecs.possible.length > 0) {
      if (compositionCodec && derivedOutNameCodecs.possible.includes(compositionCodec)) {
        return {
          value: compositionCodec,
          source: "derived from out name + compositionCodec from calculateMetadata"
        };
      }
      if (configFile && derivedOutNameCodecs.possible.includes(configFile)) {
        return {
          value: configFile,
          source: "derived from out name + config file"
        };
      }
      return {
        value: derivedOutNameCodecs.default,
        source: "derived from out name"
      };
    }
    if (compositionCodec) {
      return { value: compositionCodec, source: "via calculateMetadata" };
    }
    if (configFile) {
      return {
        value: configFile,
        source: "Config file"
      };
    }
    return { value: DEFAULT_CODEC, source: "default" };
  },
  setConfig: setCodec,
  id: cliFlag83
};

// src/options/video-image-format.tsx
import { jsx as jsx79, jsxs as jsxs52, Fragment as Fragment79 } from "react/jsx-runtime";
var currentVideoImageFormat = null;
var cliFlag84 = "image-format";
var videoImageFormatOption = {
  name: "Video Image Format",
  cliFlag: cliFlag84,
  description: () => /* @__PURE__ */ jsxs52(Fragment79, {
    children: [
      "The image format to use when rendering frames for a video. Must be one of",
      " ",
      validVideoImageFormats.map((f) => `"${f}"`).join(", "),
      ". Default:",
      " ",
      /* @__PURE__ */ jsx79("code", {
        children: '"jpeg"'
      }),
      ". JPEG is faster, but does not support transparency."
    ]
  }),
  ssrName: "imageFormat",
  docLink: "https://www.remotion.dev/docs/renderer/render-media#imageformat",
  type: null,
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag84] !== undefined) {
      const value3 = commandLine[cliFlag84];
      if (!validVideoImageFormats.includes(value3)) {
        throw new Error(`Invalid video image format: ${value3}. Must be one of: ${validVideoImageFormats.join(", ")}`);
      }
      return {
        source: "cli",
        value: value3
      };
    }
    if (currentVideoImageFormat !== null) {
      return {
        source: "config",
        value: currentVideoImageFormat
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    if (value3 === null) {
      currentVideoImageFormat = null;
      return;
    }
    if (!validVideoImageFormats.includes(value3)) {
      throw new TypeError([
        `Value ${value3} is not valid as a video image format.`,
        value3 === "jpg" ? 'Did you mean "jpeg"?' : null
      ].filter(Boolean).join(" "));
    }
    currentVideoImageFormat = value3;
  },
  id: "video-image-format"
};

// src/options/webhook-custom-data.tsx
import { jsxs as jsxs53, Fragment as Fragment80 } from "react/jsx-runtime";
var cliFlag85 = "webhook-custom-data";
var webhookCustomDataOption = {
  name: "Webhook custom data",
  cliFlag: cliFlag85,
  description: (type) => /* @__PURE__ */ jsxs53(Fragment80, {
    children: [
      "Pass up to 1,024 bytes of a JSON-serializable object to the webhook. This data will be included in the webhook payload.",
      " ",
      type === "cli" ? "Alternatively, pass a file path pointing to a JSON file" : null
    ]
  }),
  ssrName: "customData",
  docLink: "https://www.remotion.dev/docs/lambda/webhooks",
  type: {},
  getValue: () => {
    throw new Error("Option resolution not implemented");
  },
  setConfig: () => {
    throw new Error("Not implemented");
  },
  id: cliFlag85
};

// src/options/webpack-poll.tsx
import { jsx as jsx80, Fragment as Fragment81 } from "react/jsx-runtime";
var cliFlag86 = "webpack-poll";
var webpackPolling = null;
var webpackPollOption = {
  name: "Webpack Polling",
  cliFlag: cliFlag86,
  description: () => /* @__PURE__ */ jsx80(Fragment81, {
    children: "Enables Webpack polling instead of the file system event listeners for hot reloading. This is useful if you are inside a virtual machine or have a remote file system. Pass a value in milliseconds."
  }),
  ssrName: null,
  docLink: "https://www.remotion.dev/docs/config#setwebpackpollinginmilliseconds",
  getValue: ({ commandLine }) => {
    if (commandLine[cliFlag86] !== undefined) {
      const val = commandLine[cliFlag86];
      if (typeof val !== "number") {
        throw new TypeError(`Webpack polling must be a number, got ${JSON.stringify(val)}`);
      }
      return {
        source: "cli",
        value: val
      };
    }
    if (webpackPolling !== null) {
      return {
        source: "config",
        value: webpackPolling
      };
    }
    return {
      source: "default",
      value: null
    };
  },
  setConfig: (value3) => {
    if (typeof value3 !== "number" && value3 !== null) {
      throw new TypeError(`Polling must be a number or null, got ${JSON.stringify(value3)} instead.`);
    }
    webpackPolling = value3;
  },
  type: 0,
  id: cliFlag86
};

// src/options/x264-preset.tsx
import { jsx as jsx81, jsxs as jsxs54, Fragment as Fragment82 } from "react/jsx-runtime";
var x264PresetOptions = [
  "ultrafast",
  "superfast",
  "veryfast",
  "faster",
  "fast",
  "medium",
  "slow",
  "slower",
  "veryslow",
  "placebo"
];
var preset = null;
var cliFlag87 = "x264-preset";
var DEFAULT_PRESET = "medium";
var x264Option = {
  name: "x264 Preset",
  cliFlag: cliFlag87,
  description: () => /* @__PURE__ */ jsxs54(Fragment82, {
    children: [
      "Sets a x264 preset profile. Only applies to videos rendered with",
      " ",
      /* @__PURE__ */ jsx81("code", {
        children: "h264"
      }),
      " codec.",
      /* @__PURE__ */ jsx81("br", {}),
      "Possible values: ",
      /* @__PURE__ */ jsx81("code", {
        children: "superfast"
      }),
      ", ",
      /* @__PURE__ */ jsx81("code", {
        children: "veryfast"
      }),
      ",",
      " ",
      /* @__PURE__ */ jsx81("code", {
        children: "faster"
      }),
      ", ",
      /* @__PURE__ */ jsx81("code", {
        children: "fast"
      }),
      ", ",
      /* @__PURE__ */ jsx81("code", {
        children: "medium"
      }),
      ",",
      " ",
      /* @__PURE__ */ jsx81("code", {
        children: "slow"
      }),
      ", ",
      /* @__PURE__ */ jsx81("code", {
        children: "slower"
      }),
      ", ",
      /* @__PURE__ */ jsx81("code", {
        children: "veryslow"
      }),
      ",",
      " ",
      /* @__PURE__ */ jsx81("code", {
        children: "placebo"
      }),
      ".",
      /* @__PURE__ */ jsx81("br", {}),
      "Default: ",
      /* @__PURE__ */ jsx81("code", {
        children: DEFAULT_PRESET
      })
    ]
  }),
  ssrName: "x264Preset",
  docLink: "https://www.remotion.dev/docs/renderer/render-media",
  type: "fast",
  getValue: ({ commandLine }) => {
    const value3 = commandLine[cliFlag87];
    if (typeof value3 !== "undefined") {
      return { value: value3, source: "cli" };
    }
    if (preset !== null) {
      return { value: preset, source: "config" };
    }
    return { value: null, source: "default" };
  },
  setConfig: (profile) => {
    preset = profile;
  },
  id: cliFlag87
};

// src/options/index.tsx
var allOptions = {
  audioCodecOption,
  browserExecutableOption,
  concurrencyOption,
  scaleOption,
  crfOption,
  jpegQualityOption,
  videoBitrateOption,
  audioBitrateOption,
  enforceAudioOption,
  everyNthFrameOption,
  mutedOption,
  videoCodecOption,
  offthreadVideoCacheSizeInBytesOption,
  offthreadVideoThreadsOption,
  webhookCustomDataOption,
  colorSpaceOption,
  deleteAfterOption,
  disableWebSecurityOption,
  disallowParallelEncodingOption,
  folderExpiryOption,
  enableMultiprocessOnLinuxOption,
  glOption,
  enableLambdaInsights,
  encodingMaxRateOption,
  encodingBufferSizeOption,
  beepOnFinishOption,
  numberOfGifLoopsOption,
  reproOption,
  runsOption,
  noOpenOption,
  pixelFormatOption,
  preferLosslessOption: preferLosslessAudioOption,
  proResProfileOption,
  x264Option,
  logLevelOption,
  delayRenderTimeoutInMillisecondsOption,
  headlessOption,
  overwriteOption,
  binariesDirectoryOption,
  forSeamlessAacConcatenationOption,
  separateAudioOption,
  publicPathOption,
  publicDirOption,
  onBrowserDownloadOption,
  throwIfSiteExistsOption,
  disableGitSourceOption,
  metadataOption,
  hardwareAccelerationOption,
  chromeModeOption,
  apiKeyOption,
  licenseKeyOption,
  audioLatencyHintOption,
  enableCrossSiteIsolationOption,
  ignoreCertificateErrorsOption,
  imageSequencePatternOption,
  mediaCacheSizeInBytesOption,
  darkModeOption,
  publicLicenseKeyOption,
  isProductionOption,
  askAIOption,
  experimentalClientSideRenderingOption,
  experimentalVisualModeOption,
  keyboardShortcutsOption,
  framesOption,
  forceNewStudioOption,
  numberOfSharedAudioTagsOption,
  ipv4Option,
  stillImageFormatOption,
  userAgentOption,
  videoImageFormatOption,
  overrideHeightOption,
  overrideWidthOption,
  overrideFpsOption,
  overrideDurationOption,
  rspackOption,
  outDirOption,
  packageManagerOption,
  webpackPollOption,
  stillFrameOption,
  imageSequenceOption,
  versionFlagOption,
  bundleCacheOption,
  envFileOption,
  portOption,
  propsOption,
  configOption,
  browserOption
};

// src/options/options-map.ts
var optionsMap = {
  renderMedia: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    videoBitrate: videoBitrateOption,
    numberOfGifLoops: numberOfGifLoopsOption,
    repro: reproOption,
    x264Preset: x264Option,
    audioBitrate: audioBitrateOption,
    colorSpace: colorSpaceOption,
    codec: videoCodecOption,
    disallowParallelEncoding: disallowParallelEncodingOption,
    jpegQuality: jpegQualityOption,
    encodingMaxRate: encodingMaxRateOption,
    encodingBufferSize: encodingBufferSizeOption,
    muted: mutedOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    binariesDirectory: binariesDirectoryOption,
    forSeamlessAacConcatenation: forSeamlessAacConcatenationOption,
    separateAudioTo: separateAudioOption,
    audioCodec: audioCodecOption,
    onBrowserDownload: onBrowserDownloadOption,
    hardwareAcceleration: hardwareAccelerationOption,
    chromeMode: chromeModeOption,
    licenseKey: licenseKeyOption
  },
  stitchFramesToVideo: {
    separateAudioTo: separateAudioOption,
    hardwareAcceleration: hardwareAccelerationOption
  },
  renderStill: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    jpegQuality: jpegQualityOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    binariesDirectory: binariesDirectoryOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption,
    apiKey: apiKeyOption,
    licenseKey: licenseKeyOption
  },
  getCompositions: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    binariesDirectory: binariesDirectoryOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption
  },
  selectComposition: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    binariesDirectory: binariesDirectoryOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption
  },
  renderFrames: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    forSeamlessAacConcatenation: forSeamlessAacConcatenationOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    jpegQuality: jpegQualityOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    binariesDirectory: binariesDirectoryOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption,
    imageSequencePattern: imageSequencePatternOption
  },
  renderMediaOnLambda: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    videoBitrate: videoBitrateOption,
    numberOfGifLoops: numberOfGifLoopsOption,
    preferLossless: preferLosslessAudioOption,
    audioBitrate: audioBitrateOption,
    deleteAfter: deleteAfterOption,
    x264Preset: x264Option,
    encodingMaxRate: encodingMaxRateOption,
    encodingBufferSize: encodingBufferSizeOption,
    colorSpace: colorSpaceOption,
    muted: mutedOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    apiKey: apiKeyOption,
    licenseKey: licenseKeyOption
  },
  renderStillOnLambda: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    jpegQuality: jpegQualityOption,
    logLevel: logLevelOption,
    deleteAfter: deleteAfterOption,
    scale: scaleOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    apiKey: apiKeyOption,
    licenseKey: licenseKeyOption
  },
  getCompositionsOnLambda: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    logLevel: logLevelOption,
    timeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption
  },
  renderMediaOnCloudRun: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    numberOfGifLoops: numberOfGifLoopsOption,
    preferLossless: preferLosslessAudioOption,
    colorSpace: colorSpaceOption,
    audioBitrate: audioBitrateOption,
    videoBitrate: videoBitrateOption,
    x264Preset: x264Option,
    encodingMaxRate: encodingMaxRateOption,
    encodingBufferSize: encodingBufferSizeOption,
    muted: mutedOption,
    logLevel: logLevelOption,
    delayRenderTimeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption,
    enforceAudioTrack: enforceAudioOption,
    scale: scaleOption,
    crf: crfOption,
    jpegQuality: jpegQualityOption
  },
  renderStillOnCloudRun: {
    mediaCacheSizeInBytes: mediaCacheSizeInBytesOption,
    offthreadVideoCacheSizeInBytes: offthreadVideoCacheSizeInBytesOption,
    offthreadVideoThreads: offthreadVideoThreadsOption,
    logLevel: logLevelOption,
    scale: scaleOption,
    jpegQuality: jpegQualityOption,
    delayRenderTimeoutInMilliseconds: delayRenderTimeoutInMillisecondsOption
  },
  ensureBrowser: {
    logLevel: logLevelOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption
  },
  openBrowser: {
    logLevel: logLevelOption,
    onBrowserDownload: onBrowserDownloadOption,
    chromeMode: chromeModeOption
  },
  deploySiteLambda: {
    logLevel: logLevelOption,
    throwIfSiteExists: throwIfSiteExistsOption
  },
  deploySiteCloudRun: {
    logLevel: logLevelOption
  }
};

// src/validate-output-filename.ts
var validateOutputFilename = ({
  codec: codec2,
  audioCodecSetting,
  extension,
  preferLossless,
  separateAudioTo
}) => {
  if (!defaultFileExtensionMap[codec2]) {
    throw new TypeError(`The codec "${codec2}" is not supported. Supported codecs are: ${Object.keys(defaultFileExtensionMap).join(", ")}`);
  }
  const map = defaultFileExtensionMap[codec2];
  const resolvedAudioCodec = resolveAudioCodec({
    codec: codec2,
    preferLossless,
    setting: audioCodecSetting,
    separateAudioTo
  });
  if (resolvedAudioCodec === null) {
    if (extension !== map.default) {
      throw new TypeError(`When using the ${codec2} codec, the output filename must end in .${map.default}.`);
    }
    return;
  }
  if (!(resolvedAudioCodec in map.forAudioCodec)) {
    throw new Error(`Audio codec ${resolvedAudioCodec} is not supported for codec ${codec2}`);
  }
  const acceptableExtensions = map.forAudioCodec[resolvedAudioCodec].possible;
  if (!acceptableExtensions.includes(extension) && !separateAudioTo) {
    throw new TypeError(`When using the ${codec2} codec with the ${resolvedAudioCodec} audio codec, the output filename must end in one of the following: ${acceptableExtensions.join(", ")}.`);
  }
};

// src/client.ts
var BrowserSafeApis = {
  getFileExtensionFromCodec,
  validCodecs,
  validAudioCodecs,
  getDefaultCrfForCodec,
  getValidCrfRanges,
  proResProfileOptions: NoReactInternals4.proResProfileOptions,
  x264PresetOptions,
  hardwareAccelerationOptions,
  validPixelFormats,
  validOpenGlRenderers,
  validPixelFormatsForCodec,
  validVideoImageFormats,
  validStillImageFormats,
  DEFAULT_PIXEL_FORMAT,
  DEFAULT_TIMEOUT,
  DEFAULT_JPEG_QUALITY,
  DEFAULT_COLOR_SPACE,
  supportedAudioCodecs,
  defaultFileExtensionMap,
  defaultAudioCodecs,
  defaultCodecsForFileExtension,
  validateOutputFilename,
  options: allOptions,
  validColorSpaces,
  optionsMap,
  codecSupportsCrf,
  codecSupportsVideoBitrate,
  logLevels,
  getOutputCodecOrUndefined,
  getExtensionFromAudioCodec,
  validChromeModeOptions
};
export {
  BrowserSafeApis
};
