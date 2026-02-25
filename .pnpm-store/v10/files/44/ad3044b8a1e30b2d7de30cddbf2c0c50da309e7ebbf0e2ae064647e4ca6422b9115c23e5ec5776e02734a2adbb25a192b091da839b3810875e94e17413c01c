"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimelineListItem = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const remotion_1 = require("remotion");
const colors_1 = require("../../helpers/colors");
const timeline_layout_1 = require("../../helpers/timeline-layout");
const ExpandedTracksProvider_1 = require("../ExpandedTracksProvider");
const TimelineLayerEye_1 = require("./TimelineLayerEye");
const TimelineStack_1 = require("./TimelineStack");
const SPACING = 5;
const space = {
    width: SPACING,
    flexShrink: 0,
};
const arrowButton = {
    background: 'none',
    border: 'none',
    color: 'white',
    cursor: 'pointer',
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 12,
    height: 12,
    flexShrink: 0,
    fontSize: 8,
    marginRight: 4,
    userSelect: 'none',
    outline: 'none',
    lineHeight: 1,
};
const expandedSection = {
    height: timeline_layout_1.TIMELINE_TRACK_EXPANDED_HEIGHT,
    color: 'white',
    fontFamily: 'Arial, Helvetica, sans-serif',
    fontSize: 12,
    display: 'flex',
    alignItems: 'center',
    paddingLeft: 28,
    borderBottom: `1px solid ${colors_1.TIMELINE_TRACK_SEPARATOR}`,
};
const TimelineListItem = ({ nestedDepth, sequence, isCompact }) => {
    var _a;
    const visualModeEnabled = Boolean(process.env.EXPERIMENTAL_VISUAL_MODE_ENABLED);
    const { hidden, setHidden } = (0, react_1.useContext)(remotion_1.Internals.SequenceVisibilityToggleContext);
    const { expandedTracks, toggleTrack } = (0, react_1.useContext)(ExpandedTracksProvider_1.ExpandedTracksContext);
    const isExpanded = (_a = expandedTracks[sequence.id]) !== null && _a !== void 0 ? _a : false;
    const onToggleExpand = (0, react_1.useCallback)(() => {
        toggleTrack(sequence.id);
    }, [sequence.id, toggleTrack]);
    const padder = (0, react_1.useMemo)(() => {
        return {
            width: Number(SPACING * 1.5) * nestedDepth,
            flexShrink: 0,
        };
    }, [nestedDepth]);
    const isItemHidden = (0, react_1.useMemo)(() => {
        var _a;
        return (_a = hidden[sequence.id]) !== null && _a !== void 0 ? _a : false;
    }, [hidden, sequence.id]);
    const onToggleVisibility = (0, react_1.useCallback)((type) => {
        setHidden((prev) => {
            return {
                ...prev,
                [sequence.id]: type !== 'enable',
            };
        });
    }, [sequence.id, setHidden]);
    const outer = (0, react_1.useMemo)(() => {
        return {
            height: (0, timeline_layout_1.getTimelineLayerHeight)(sequence.type === 'video' ? 'video' : 'other') +
                timeline_layout_1.TIMELINE_ITEM_BORDER_BOTTOM,
            color: 'white',
            fontFamily: 'Arial, Helvetica, sans-serif',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            wordBreak: 'break-all',
            textAlign: 'left',
            paddingLeft: SPACING,
            borderBottom: `1px solid ${colors_1.TIMELINE_TRACK_SEPARATOR}`,
        };
    }, [sequence.type]);
    const arrowStyle = (0, react_1.useMemo)(() => {
        return {
            ...arrowButton,
            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
        };
    }, [isExpanded]);
    return (jsx_runtime_1.jsxs(jsx_runtime_1.Fragment, { children: [
            jsx_runtime_1.jsxs("div", { style: outer, children: [
                    jsx_runtime_1.jsx(TimelineLayerEye_1.TimelineLayerEye, { type: sequence.type === 'audio' ? 'speaker' : 'eye', hidden: isItemHidden, onInvoked: onToggleVisibility }), jsx_runtime_1.jsx("div", { style: padder }), sequence.parent && nestedDepth > 0 ? jsx_runtime_1.jsx("div", { style: space }) : null, visualModeEnabled ? (jsx_runtime_1.jsx("button", { type: "button", style: arrowStyle, onClick: onToggleExpand, "aria-expanded": isExpanded, "aria-label": `${isExpanded ? 'Collapse' : 'Expand'} track`, children: jsx_runtime_1.jsx("svg", { width: "12", height: "12", viewBox: "0 0 8 8", style: { display: 'block' }, children: jsx_runtime_1.jsx("path", { d: "M2 1L6 4L2 7Z", fill: "white" }) }) })) : null, jsx_runtime_1.jsx(TimelineStack_1.TimelineStack, { sequence: sequence, isCompact: isCompact })
                ] }), visualModeEnabled && isExpanded ? (jsx_runtime_1.jsx("div", { style: expandedSection, children: "Expanded track details" })) : null] }));
};
exports.TimelineListItem = TimelineListItem;
