import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
    name: "AngelosKar.ResetCounters",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        if (nodeData.name !== "AK_ResetCounters") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = origCreated?.apply(this, arguments);
            const node = this;

            // ── Reset All Counters Button ──
            const resetBtn = this.addWidget("button", "🔄 Reset All Counters", "reset_all", async () => {
                if (resetBtn._akBusy) return;
                resetBtn._akBusy = true;

                const originalName = resetBtn.name;
                resetBtn.name = "⏳ Resetting...";
                app.graph.setDirtyCanvas(true);

                // Find all AK scheduler / auto-loader nodes in the graph
                const targetTypes = ["AK_ImageListScheduler", "AK_AutoImageListLoader"];
                const endpoints = {
                    "AK_ImageListScheduler": "/angeloskar/reset_image_list_counter",
                    "AK_AutoImageListLoader": "/angeloskar/reset_auto_list_counter",
                };

                const targets = app.graph._nodes.filter(n => targetTypes.includes(n.type));

                if (targets.length === 0) {
                    resetBtn.name = "⚠ No schedulers found";
                    app.graph.setDirtyCanvas(true);
                    setTimeout(() => {
                        resetBtn.name = originalName;
                        resetBtn._akBusy = false;
                        app.graph.setDirtyCanvas(true);
                    }, 2000);
                    return;
                }

                let resetCount = 0;
                let errors = 0;

                for (const target of targets) {
                    const endpoint = endpoints[target.type];
                    try {
                        const res = await api.fetchApi(endpoint, {
                            method: "POST",
                            body: JSON.stringify({ unique_id: String(target.id) }),
                            headers: { "Content-Type": "application/json" },
                        });
                        const data = await res.json();
                        if (data.status === "ok") resetCount++;
                        console.log(`[AK] Reset node ${target.id} (${target.type}):`, data.message);
                    } catch (err) {
                        errors++;
                        console.error(`[AK] Failed to reset node ${target.id}:`, err);
                    }
                }

                if (errors === 0) {
                    resetBtn.name = `✅ Reset ${resetCount} counter${resetCount !== 1 ? "s" : ""}!`;
                } else {
                    resetBtn.name = `⚠ Reset ${resetCount}, failed ${errors}`;
                }
                app.graph.setDirtyCanvas(true);

                setTimeout(() => {
                    resetBtn.name = originalName;
                    resetBtn._akBusy = false;
                    app.graph.setDirtyCanvas(true);
                }, 2500);
            });

            return r;
        };
    }
});
