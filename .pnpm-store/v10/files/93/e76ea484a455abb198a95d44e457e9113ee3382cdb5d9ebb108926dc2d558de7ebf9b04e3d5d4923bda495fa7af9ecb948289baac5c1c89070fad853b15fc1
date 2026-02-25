"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ZodNumberEditor = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const InputDragger_1 = require("../../NewComposition/InputDragger");
const Fieldset_1 = require("./Fieldset");
const SchemaLabel_1 = require("./SchemaLabel");
const ZodFieldValidation_1 = require("./ZodFieldValidation");
const local_state_1 = require("./local-state");
const zod_schema_type_1 = require("./zod-schema-type");
const fullWidth = {
    width: '100%',
};
const getMinValue = (schema) => {
    var _a;
    const { checks } = (0, zod_schema_type_1.getZodDef)(schema);
    if (!checks)
        return -Infinity;
    if ((0, zod_schema_type_1.isZodV3Schema)(schema)) {
        // v3: {kind: "min", value: 0, inclusive: true}
        const minCheck = checks.find((c) => c.kind === 'min');
        if (!minCheck || !minCheck.inclusive)
            return -Infinity;
        return minCheck.value;
    }
    // v4: check objects with _zod.def = {check: "greater_than", value: 0, inclusive: true}
    for (const c of checks) {
        const def = (_a = c._zod) === null || _a === void 0 ? void 0 : _a.def;
        if ((def === null || def === void 0 ? void 0 : def.check) === 'greater_than' && def.inclusive) {
            return def.value;
        }
    }
    return -Infinity;
};
const getMaxValue = (schema) => {
    var _a;
    const { checks } = (0, zod_schema_type_1.getZodDef)(schema);
    if (!checks)
        return Infinity;
    if ((0, zod_schema_type_1.isZodV3Schema)(schema)) {
        // v3: {kind: "max", value: 100, inclusive: true}
        const maxCheck = checks.find((c) => c.kind === 'max');
        if (!maxCheck || !maxCheck.inclusive)
            return Infinity;
        return maxCheck.value;
    }
    // v4: check objects with _zod.def = {check: "less_than", value: 100, inclusive: true}
    for (const c of checks) {
        const def = (_a = c._zod) === null || _a === void 0 ? void 0 : _a.def;
        if ((def === null || def === void 0 ? void 0 : def.check) === 'less_than' && def.inclusive) {
            return def.value;
        }
    }
    return Infinity;
};
const getStep = (schema) => {
    var _a;
    const { checks } = (0, zod_schema_type_1.getZodDef)(schema);
    if (!checks)
        return undefined;
    if ((0, zod_schema_type_1.isZodV3Schema)(schema)) {
        // v3: {kind: "multipleOf", value: 5}
        const multipleStep = checks.find((c) => c.kind === 'multipleOf');
        if (!multipleStep)
            return undefined;
        return multipleStep.value;
    }
    // v4: check objects with _zod.def = {check: "multiple_of", value: 5}
    for (const c of checks) {
        const def = (_a = c._zod) === null || _a === void 0 ? void 0 : _a.def;
        if ((def === null || def === void 0 ? void 0 : def.check) === 'multiple_of') {
            return def.value;
        }
    }
    return undefined;
};
const ZodNumberEditor = ({ jsonPath, value, schema, setValue, onSave, defaultValue, onRemove, showSaveButton, saving, saveDisabledByParent, mayPad, }) => {
    const { localValue, onChange: setLocalValue, reset, } = (0, local_state_1.useLocalState)({
        unsavedValue: value,
        schema,
        setValue,
        savedValue: defaultValue,
    });
    const onNumberChange = (0, react_1.useCallback)((newValue) => {
        setLocalValue(() => newValue, false, false);
    }, [setLocalValue]);
    const isDefault = localValue.value === defaultValue;
    const onTextChange = (0, react_1.useCallback)((newValue) => {
        setLocalValue(() => Number(newValue), false, false);
    }, [setLocalValue]);
    const save = (0, react_1.useCallback)(() => {
        onSave(() => value, false, false);
    }, [onSave, value]);
    return (jsx_runtime_1.jsxs(Fieldset_1.Fieldset, { shouldPad: mayPad, success: localValue.zodValidation.success, children: [
            jsx_runtime_1.jsx(SchemaLabel_1.SchemaLabel, { handleClick: null, isDefaultValue: isDefault, jsonPath: jsonPath, onReset: reset, onSave: save, showSaveButton: showSaveButton, onRemove: onRemove, saving: saving, valid: localValue.zodValidation.success, saveDisabledByParent: saveDisabledByParent, suffix: null }), jsx_runtime_1.jsxs("div", { style: fullWidth, children: [
                    jsx_runtime_1.jsx(InputDragger_1.InputDragger, { type: 'number', value: localValue.value, style: fullWidth, status: localValue.zodValidation.success ? 'ok' : 'error', placeholder: jsonPath.join('.'), onTextChange: onTextChange, onValueChange: onNumberChange, min: getMinValue(schema), max: getMaxValue(schema), step: getStep(schema), rightAlign: false }), jsx_runtime_1.jsx(ZodFieldValidation_1.ZodFieldValidation, { path: jsonPath, localValue: localValue })
                ] })
        ] }));
};
exports.ZodNumberEditor = ZodNumberEditor;
