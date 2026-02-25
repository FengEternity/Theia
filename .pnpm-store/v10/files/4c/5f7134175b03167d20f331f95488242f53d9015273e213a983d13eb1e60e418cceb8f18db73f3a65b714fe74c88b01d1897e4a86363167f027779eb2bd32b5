"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.concurrenciesOption = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const cliFlag = 'concurrencies';
let currentConcurrencies = '';
exports.concurrenciesOption = {
    name: 'Concurrencies',
    cliFlag,
    ssrName: 'concurrencies',
    description: () => (jsx_runtime_1.jsxs(jsx_runtime_1.Fragment, { children: ["You can specify which concurrency value should be used while rendering the video. Multiple concurrency values can be passed separated by comma. Learn more about", ' ', jsx_runtime_1.jsx("a", { href: "/docs/terminology/concurrency", children: jsx_runtime_1.jsx("code", { children: "concurrency" }) })
        ] })),
    docLink: 'https://www.remotion.dev/docs/cli/benchmark#--concurrencies',
    type: '',
    getValue: ({ commandLine }) => {
        if (commandLine[cliFlag]) {
            return {
                value: String(commandLine[cliFlag]),
                source: 'cli',
            };
        }
        if (currentConcurrencies) {
            return {
                value: currentConcurrencies,
                source: 'config',
            };
        }
        return {
            source: 'default',
            value: '',
        };
    },
    setConfig: (value) => {
        currentConcurrencies = value;
    },
    id: cliFlag,
};
