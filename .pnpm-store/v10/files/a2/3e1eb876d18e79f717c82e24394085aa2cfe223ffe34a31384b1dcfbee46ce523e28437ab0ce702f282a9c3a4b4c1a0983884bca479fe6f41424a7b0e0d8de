"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.outputOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'output';
let currentOutput;
// Option for --output
exports.outputOption = {
    name: 'Output',
    cliFlag,
    ssrName: 'output',
    description: () => (jsx_runtime_1.jsxs(jsx_runtime_1.Fragment, { children: ["Sets the output file path, as an alternative to the", ' ', jsx_runtime_1.jsx("code", { children: "output-location" }),
            " positional argument."] })),
    docLink: 'https://www.remotion.dev/docs/cli/render#--output-',
    type: '',
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag] !== undefined) {
            return {
                value: commandLine[cliFlag],
                source: 'cli',
            };
        }
        if (currentOutput !== undefined) {
            return {
                value: currentOutput,
                source: 'config',
            };
        }
        return {
            source: 'default',
            value: undefined,
        };
    },
    setConfig: (value) => {
        currentOutput = value;
    },
    id: cliFlag,
};
