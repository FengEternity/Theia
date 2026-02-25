import React from 'react';
import type { UpdaterFunction } from './ZodSwitch';
import type { AnyZodSchema, ZodSafeParseResult } from './zod-schema-type';
export type LocalState<T> = {
    value: T;
    zodValidation: ZodSafeParseResult;
    keyStabilityRevision: number;
};
export type RevisionContextType = {
    childResetRevision: number;
};
export declare const RevisionContext: React.Context<RevisionContextType>;
export declare const useLocalState: <T>({ unsavedValue, schema, setValue, savedValue, }: {
    unsavedValue: T;
    schema: AnyZodSchema;
    setValue: UpdaterFunction<T>;
    savedValue: T;
}) => {
    localValue: LocalState<T>;
    onChange: (updater: (oldV: T) => T, forceApply: boolean, increment: boolean) => void;
    reset: () => void;
    RevisionContextProvider: ({ children }: {
        children: React.ReactNode;
    }) => import("react/jsx-runtime").JSX.Element;
};
