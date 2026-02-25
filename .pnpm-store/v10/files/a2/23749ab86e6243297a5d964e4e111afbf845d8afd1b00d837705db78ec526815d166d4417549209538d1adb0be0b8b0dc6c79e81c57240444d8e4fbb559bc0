"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.forceOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'force';
exports.forceOption = {
    name: 'Force',
    cliFlag,
    ssrName: 'force',
    description: () => jsx_runtime_1.jsx(jsx_runtime_1.Fragment, {}),
    docLink: null,
    type: false,
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag] !== undefined) {
            return { value: Boolean(commandLine[cliFlag]), source: 'cli' };
        }
        return {
            source: 'default',
            value: false,
        };
    },
    setConfig: () => { },
    id: cliFlag,
};
