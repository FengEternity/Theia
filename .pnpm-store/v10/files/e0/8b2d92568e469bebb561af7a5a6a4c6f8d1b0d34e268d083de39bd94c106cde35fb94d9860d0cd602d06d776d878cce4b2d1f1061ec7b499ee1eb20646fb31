import type { EventSourceEvent } from '@remotion/studio-shared';
import type { IncomingMessage, ServerResponse } from 'node:http';
export type LiveEventsServer = {
    sendEventToClient: (event: EventSourceEvent) => void;
    router: (request: IncomingMessage, response: ServerResponse) => Promise<void>;
    closeConnections: () => Promise<void>;
};
export declare const makeLiveEventsRouter: (logLevel: "error" | "info" | "trace" | "verbose" | "warn") => LiveEventsServer;
export declare const waitForLiveEventsListener: () => Promise<LiveEventsServer>;
export declare const setLiveEventsListener: (listener: LiveEventsServer) => () => void;
