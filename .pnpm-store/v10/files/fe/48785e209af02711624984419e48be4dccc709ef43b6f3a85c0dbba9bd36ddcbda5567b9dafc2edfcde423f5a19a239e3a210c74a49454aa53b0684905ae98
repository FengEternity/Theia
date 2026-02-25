"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.helpOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'help';
let currentHelp = null;
exports.helpOption = {
    name: 'Help',
    cliFlag,
    ssrName: 'help',
    description: () => (jsx_runtime_1.jsx(jsx_runtime_1.Fragment, { children: "Prints available commands and flags for the Remotion CLI." })),
    docLink: 'https://www.remotion.dev/docs/cli/help',
    type: false,
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag] !== undefined) {
            return { value: Boolean(commandLine[cliFlag]), source: 'cli' };
        }
        if (currentHelp !== null)
            return { value: currentHelp, source: 'config' };
        return { value: false, source: 'default' };
    },
    setConfig: (value) => {
        currentHelp = value;
    },
    id: cliFlag,
};
