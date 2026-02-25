"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.quietOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'quiet';
let currentQuiet = false;
exports.quietOption = {
    name: 'Quiet',
    cliFlag,
    ssrName: 'quiet',
    description: () => (jsx_runtime_1.jsx(jsx_runtime_1.Fragment, { children: "Only prints the composition IDs, separated by a space." })),
    docLink: 'https://www.remotion.dev/docs/cli/compositions#--quiet---q',
    type: false,
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag] !== undefined) {
            return { value: true, source: 'cli' };
        }
        if (currentQuiet !== false)
            return { value: currentQuiet, source: 'config' };
        return { value: false, source: 'default' };
    },
    setConfig: (value) => {
        currentQuiet = value;
    },
    id: cliFlag,
};
