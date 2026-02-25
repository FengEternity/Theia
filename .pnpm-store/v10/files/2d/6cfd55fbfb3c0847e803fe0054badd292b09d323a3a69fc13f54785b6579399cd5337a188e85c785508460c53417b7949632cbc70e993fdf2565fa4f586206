"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.qualityOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'quality';
exports.qualityOption = {
    name: 'Quality (deprecated)',
    cliFlag,
    ssrName: 'quality',
    description: () => (jsx_runtime_1.jsxs(jsx_runtime_1.Fragment, { children: ["Renamed to ",
            jsx_runtime_1.jsx("code", { children: "--jpeg-quality" }),
            " in v4.0.0"] })),
    docLink: 'https://www.remotion.dev/docs/cli/still#--quality-',
    type: null,
    getValue: () => {
        throw new Error('The "--quality" flag was deprecated in v4.0.0. Please use "--jpeg-quality" instead.');
    },
    setConfig: () => { },
    id: cliFlag,
};
