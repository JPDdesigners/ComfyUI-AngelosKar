import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

/**
 * 👔 AK Tag Controllers Suite (Frontend Extension)
 * Unified controller for:
 *   1. AK_GarmentModeController (1-5 Garments)
 *   2. AK_TagBypasser (Generic Tag Bypasser)
 *   3. AK_TagMuter (Generic Tag Muter)
 * 
 * Strict Priority Hierarchy across canvas:
 *   MUTE (mode 2) > BYPASS (mode 4) > ACTIVE (mode 0)
 * 
 * If ANY rule dictates MUTE (e.g. Garment 2 is off), the node is MUTED.
 * Bypass only applies if the node is NOT Muted.
 */

const CONTROLLER_TYPES = new Set([
    "AK_GarmentModeController",
    "AK_TagBypasser",
    "AK_TagMuter"
]);

function parseGarmentCount(val) {
    if (typeof val === "number") return val;
    if (typeof val === "string") {
        const match = val.match(/\d+/);
        if (match) return parseInt(match[0], 10);
    }
    return 1;
}

/**
 * Core Unified Evaluator
 * Evaluates all active controllers and sets the correct mode for all tagged nodes.
 */
export function evaluateAndApplyAllTags() {
    if (!app.graph || !app.graph._nodes) return { modified: 0, total: 0 };

    // 1. Gather all active controllers in the graph
    const garmentControllers = app.graph._nodes.filter(
        n => n.type === "AK_GarmentModeController" && n.mode === 0
    );
    const tagBypassers = app.graph._nodes.filter(
        n => n.type === "AK_TagBypasser" && n.mode === 0
    );
    const tagMuters = app.graph._nodes.filter(
        n => n.type === "AK_TagMuter" && n.mode === 0
    );

    // Active garment count (default 5 if no garment controller present)
    let garmentCount = 5;
    let hasGarmentController = false;
    if (garmentControllers.length > 0) {
        hasGarmentController = true;
        const ctrl = garmentControllers[0];
        const w = ctrl.widgets?.find(x => x.name === "active_garments");
        garmentCount = parseGarmentCount(w?.value || 1);
    }

    // Parse Bypasser rules: [{ tag: "[rmbg]", targetMode: 4 or 0 }]
    const bypassRules = [];
    for (const b of tagBypassers) {
        const tagW = b.widgets?.find(x => x.name === "tag");
        const modeW = b.widgets?.find(x => x.name === "mode");
        const rawTag = (tagW?.value || "").trim().toLowerCase();
        const isBypass = (modeW?.value === "Bypass");
        if (rawTag) {
            bypassRules.push({ tag: rawTag, isBypass });
        }
    }

    // Parse Muter rules: [{ tag: "[preview]", targetMode: 2 or 0 }]
    const muteRules = [];
    for (const m of tagMuters) {
        const tagW = m.widgets?.find(x => x.name === "tag");
        const modeW = m.widgets?.find(x => x.name === "mode");
        const rawTag = (tagW?.value || "").trim().toLowerCase();
        const isMute = (modeW?.value === "Mute");
        if (rawTag) {
            muteRules.push({ tag: rawTag, isMute });
        }
    }

    let modified = 0;
    let taggedCount = 0;

    // 2. Iterate through all nodes on canvas
    for (const node of app.graph._nodes) {
        if (CONTROLLER_TYPES.has(node.type)) continue;

        const title = (node.title || node.type || "").toLowerCase();

        let desiresMute = false;
        let desiresBypass = false;
        let desiresActive = false;
        let hasMatchingRule = false;

        // ── Check Garment Tags: [g2], [g3], [g4], [g5] ──
        if (hasGarmentController) {
            if (/\[g2\]/.test(title)) {
                hasMatchingRule = true;
                if (garmentCount < 2) desiresMute = true;
                else desiresActive = true;
            }
            if (/\[g3\]/.test(title)) {
                hasMatchingRule = true;
                if (garmentCount < 3) desiresMute = true;
                else desiresActive = true;
            }
            if (/\[g4\]/.test(title)) {
                hasMatchingRule = true;
                if (garmentCount < 4) desiresMute = true;
                else desiresActive = true;
            }
            if (/\[g5\]/.test(title)) {
                hasMatchingRule = true;
                if (garmentCount < 5) desiresMute = true;
                else desiresActive = true;
            }
        }

        // ── Check Generic Mute Rules ──
        for (const rule of muteRules) {
            if (title.includes(rule.tag)) {
                hasMatchingRule = true;
                if (rule.isMute) desiresMute = true;
                else desiresActive = true;
            }
        }

        // ── Check Generic Bypass Rules ──
        for (const rule of bypassRules) {
            if (title.includes(rule.tag)) {
                hasMatchingRule = true;
                if (rule.isBypass) desiresBypass = true;
                else desiresActive = true;
            }
        }

        // ── Apply Unified Priority: MUTE (2) > BYPASS (4) > ACTIVE (0) ──
        if (hasMatchingRule) {
            taggedCount++;
            let finalMode = 0; // Default Active
            if (desiresMute) {
                finalMode = 2; // LiteGraph.NEVER (Mute)
            } else if (desiresBypass) {
                finalMode = 4; // LiteGraph.BYPASS (Bypass)
            } else if (desiresActive) {
                finalMode = 0; // LiteGraph.ALWAYS (Active)
            }

            if (node.mode !== finalMode) {
                node.mode = finalMode;
                modified++;
            }
        }
    }

    if (modified > 0) {
        app.graph.setDirtyCanvas(true, true);
    }

    return { modified, total: taggedCount };
}

// ─── Register Extension ──────────────────────────────────────────────────────

app.registerExtension({
    name: "AngelosKar.TagControllers",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        // ── 1. AK_GarmentModeController ──
        if (nodeData.name === "AK_GarmentModeController") {
            const origCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = origCreated?.apply(this, arguments);
                const modeWidget = this.widgets?.find(w => w.name === "active_garments");

                if (modeWidget) {
                    const origCallback = modeWidget.callback;
                    modeWidget.callback = function (val) {
                        const res = origCallback?.apply(this, arguments);
                        evaluateAndApplyAllTags();
                        return res;
                    };
                }

                // Quick buttons for 1..5
                this.addWidget("button", "👉 1 Garment  [G2..G5 Mute]", "btn_1", () => {
                    if (modeWidget) modeWidget.value = "1 Garment";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "👉 2 Garments [G2 Active, G3..G5 Mute]", "btn_2", () => {
                    if (modeWidget) modeWidget.value = "2 Garments";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "👉 3 Garments [G2, G3 Active, G4..G5 Mute]", "btn_3", () => {
                    if (modeWidget) modeWidget.value = "3 Garments";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "👉 4 Garments [G2..G4 Active, G5 Mute]", "btn_4", () => {
                    if (modeWidget) modeWidget.value = "4 Garments";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "👉 5 Garments [All Active]", "btn_5", () => {
                    if (modeWidget) modeWidget.value = "5 Garments";
                    evaluateAndApplyAllTags();
                });

                const currentSize = this.size || [320, 260];
                this.size = [Math.max(currentSize[0], 340), Math.max(currentSize[1], 330)];

                setTimeout(() => evaluateAndApplyAllTags(), 300);
                return r;
            };

            const origConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                const r = origConfigure?.apply(this, arguments);
                setTimeout(() => evaluateAndApplyAllTags(), 400);
                return r;
            };

            const origDraw = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function (ctx) {
                origDraw?.apply(this, arguments);
                if (this.flags.collapsed) return;

                ctx.save();
                const margin = 12;
                const yStart = this.size[1] - 85;
                const width = this.size[0] - margin * 2;
                const height = 75;

                ctx.fillStyle = "rgba(0, 0, 0, 0.35)";
                ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(margin, yStart, width, height, 6);
                ctx.fill();
                ctx.stroke();

                ctx.font = "bold 11px sans-serif";
                ctx.fillStyle = "#ffcc00";
                ctx.fillText("🏷️ TAG REMINDER (in node title):", margin + 10, yStart + 18);

                ctx.font = "10px monospace";
                ctx.fillStyle = "#e0e0e0";
                ctx.fillText("• [G2] Active for 2+  |  • [G3] Active for 3+", margin + 10, yStart + 36);
                ctx.fillText("• [G4] Active for 4+  |  • [G5] Active for 5+", margin + 10, yStart + 52);

                ctx.font = "italic 9px sans-serif";
                ctx.fillStyle = "#999999";
                ctx.fillText("Priority: MUTE > BYPASS > ACTIVE. Case-insensitive.", margin + 10, yStart + 67);
                ctx.restore();
            };
        }

        // ── 2. AK_TagBypasser ──
        if (nodeData.name === "AK_TagBypasser") {
            const origCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = origCreated?.apply(this, arguments);
                const tagWidget = this.widgets?.find(w => w.name === "tag");
                const modeWidget = this.widgets?.find(w => w.name === "mode");

                if (tagWidget) {
                    const origCb = tagWidget.callback;
                    tagWidget.callback = function () {
                        const res = origCb?.apply(this, arguments);
                        evaluateAndApplyAllTags();
                        return res;
                    };
                }

                if (modeWidget) {
                    const origCb = modeWidget.callback;
                    modeWidget.callback = function () {
                        const res = origCb?.apply(this, arguments);
                        evaluateAndApplyAllTags();
                        return res;
                    };
                }

                this.addWidget("button", "🟢 Set ACTIVE (Process)", "btn_active", () => {
                    if (modeWidget) modeWidget.value = "Active";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "🟠 Set BYPASS (Skip)", "btn_bypass", () => {
                    if (modeWidget) modeWidget.value = "Bypass";
                    evaluateAndApplyAllTags();
                });

                const currentSize = this.size || [280, 150];
                this.size = [Math.max(currentSize[0], 300), Math.max(currentSize[1], 180)];

                setTimeout(() => evaluateAndApplyAllTags(), 300);
                return r;
            };

            const origConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                const r = origConfigure?.apply(this, arguments);
                setTimeout(() => evaluateAndApplyAllTags(), 400);
                return r;
            };

            const origDraw = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function (ctx) {
                origDraw?.apply(this, arguments);
                if (this.flags.collapsed) return;

                const modeWidget = this.widgets?.find(w => w.name === "mode");
                const isBypass = modeWidget?.value === "Bypass";

                ctx.save();
                const margin = 10;
                const yStart = this.size[1] - 40;
                const width = this.size[0] - margin * 2;
                const height = 30;

                ctx.fillStyle = isBypass ? "rgba(230, 126, 34, 0.25)" : "rgba(39, 174, 96, 0.25)";
                ctx.strokeStyle = isBypass ? "#e67e22" : "#27ae60";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(margin, yStart, width, height, 5);
                ctx.fill();
                ctx.stroke();

                ctx.font = "bold 11px sans-serif";
                ctx.fillStyle = isBypass ? "#f39c12" : "#2ecc71";
                const label = isBypass ? "🟠 State: BYPASSED (Passthrough)" : "🟢 State: ACTIVE (Normal)";
                ctx.fillText(label, margin + 10, yStart + 19);
                ctx.restore();
            };
        }

        // ── 3. AK_TagMuter ──
        if (nodeData.name === "AK_TagMuter") {
            const origCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = origCreated?.apply(this, arguments);
                const tagWidget = this.widgets?.find(w => w.name === "tag");
                const modeWidget = this.widgets?.find(w => w.name === "mode");

                if (tagWidget) {
                    const origCb = tagWidget.callback;
                    tagWidget.callback = function () {
                        const res = origCb?.apply(this, arguments);
                        evaluateAndApplyAllTags();
                        return res;
                    };
                }

                if (modeWidget) {
                    const origCb = modeWidget.callback;
                    modeWidget.callback = function () {
                        const res = origCb?.apply(this, arguments);
                        evaluateAndApplyAllTags();
                        return res;
                    };
                }

                this.addWidget("button", "🟢 Set ACTIVE", "btn_active", () => {
                    if (modeWidget) modeWidget.value = "Active";
                    evaluateAndApplyAllTags();
                });
                this.addWidget("button", "🔴 Set MUTE (Disabled)", "btn_mute", () => {
                    if (modeWidget) modeWidget.value = "Mute";
                    evaluateAndApplyAllTags();
                });

                const currentSize = this.size || [280, 150];
                this.size = [Math.max(currentSize[0], 300), Math.max(currentSize[1], 180)];

                setTimeout(() => evaluateAndApplyAllTags(), 300);
                return r;
            };

            const origConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                const r = origConfigure?.apply(this, arguments);
                setTimeout(() => evaluateAndApplyAllTags(), 400);
                return r;
            };

            const origDraw = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function (ctx) {
                origDraw?.apply(this, arguments);
                if (this.flags.collapsed) return;

                const modeWidget = this.widgets?.find(w => w.name === "mode");
                const isMute = modeWidget?.value === "Mute";

                ctx.save();
                const margin = 10;
                const yStart = this.size[1] - 40;
                const width = this.size[0] - margin * 2;
                const height = 30;

                ctx.fillStyle = isMute ? "rgba(231, 76, 60, 0.25)" : "rgba(39, 174, 96, 0.25)";
                ctx.strokeStyle = isMute ? "#e74c3c" : "#27ae60";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(margin, yStart, width, height, 5);
                ctx.fill();
                ctx.stroke();

                ctx.font = "bold 11px sans-serif";
                ctx.fillStyle = isMute ? "#e74c3c" : "#2ecc71";
                const label = isMute ? "🔴 State: MUTED (Disabled)" : "🟢 State: ACTIVE (Normal)";
                ctx.fillText(label, margin + 10, yStart + 19);
                ctx.restore();
            };
        }
    },

    // Enforce tags right before queue execution
    setup() {
        api.addEventListener("execution_start", () => {
            evaluateAndApplyAllTags();
        });
    }
});
