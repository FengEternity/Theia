"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.applyVisualControlHandler = void 0;
const node_fs_1 = require("node:fs");
const node_path_1 = __importDefault(require("node:path"));
const parse_ast_1 = require("../../codemods/parse-ast");
const recast_mods_1 = require("../../codemods/recast-mods");
const applyVisualControlHandler = ({ input: { fileName, changes }, remotionRoot }) => {
    const absolutePath = node_path_1.default.resolve(remotionRoot, fileName);
    const fileRelativeToRoot = node_path_1.default.relative(remotionRoot, absolutePath);
    if (fileRelativeToRoot.startsWith('..')) {
        throw new Error('Cannot apply visual control change to a file outside the project');
    }
    const fileContents = (0, node_fs_1.readFileSync)(absolutePath, 'utf-8');
    const ast = (0, parse_ast_1.parseAst)(fileContents);
    const { newAst, changesMade } = (0, recast_mods_1.applyCodemod)({
        file: ast,
        codeMod: {
            type: 'apply-visual-control',
            changes,
        },
    });
    if (changesMade.length === 0) {
        throw new Error('No changes were made to the file');
    }
    const output = (0, parse_ast_1.serializeAst)(newAst);
    (0, node_fs_1.writeFileSync)(absolutePath, output);
    return Promise.resolve({
        success: true,
    });
};
exports.applyVisualControlHandler = applyVisualControlHandler;
