"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.browserArgsOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'browser-args';
let currentBrowserArgs = '';
exports.browserArgsOption = {
    name: 'Browser Args',
    cliFlag,
    ssrName: 'browserArgs',
    description: () => (jsx_runtime_1.jsx(jsx_runtime_1.Fragment, { children: "A set of command line flags that should be passed to the browser." })),
    docLink: 'https://www.remotion.dev/docs/cli/studio#--browser-args',
    type: '',
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag] !== undefined)
            return { value: String(commandLine[cliFlag]), source: 'cli' };
        if (currentBrowserArgs !== '')
            return { value: currentBrowserArgs, source: 'config' };
        return { value: '', source: 'default' };
    },
    setConfig: (value) => {
        currentBrowserArgs = value;
    },
    id: cliFlag,
};
