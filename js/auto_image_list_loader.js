import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
    name: "AngelosKar.AutoImageListLoader",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        if (nodeData.name !== "AK_AutoImageListLoader") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = origCreated?.apply(this, arguments);
            const node = this;

            const fpWidget = this.widgets.find(w => w.name === "folder_path");

            // ── Browse Folder Button ──
            const browseBtn = this.addWidget("button", "📂 Browse Folder", "browse", () => {
                api.fetchApi("/angeloskar/choose_folder", { method: "POST" })
                    .then(res => res.json())
                    .then(data => {
                        if (data.path) {
                            fpWidget.value = data.path;
                            appInstance.graph.setDirtyCanvas(true);
                        }
                    })
                    .catch(err => console.error("[AK] Folder picker error:", err));
            });

            // ── Reset Counter Button ──
            const resetBtn = this.addWidget("button", "🔄 Reset Counter", "reset", () => {
                if (resetBtn._akBusy) return;
                resetBtn._akBusy = true;

                const originalName = resetBtn.name;
                resetBtn.name = "⏳ Resetting...";
                appInstance.graph.setDirtyCanvas(true);

                api.fetchApi("/angeloskar/reset_auto_list_counter", {
                    method: "POST",
                    body: JSON.stringify({ unique_id: String(node.id) }),
                    headers: { "Content-Type": "application/json" }
                })
                    .then(res => res.json())
                    .then(data => {
                        resetBtn.name = "✅ Counter Reset!";
                        appInstance.graph.setDirtyCanvas(true);
                        console.log("[AK] Auto list counter reset:", data.message);

                        setTimeout(() => {
                            resetBtn.name = originalName;
                            resetBtn._akBusy = false;
                            appInstance.graph.setDirtyCanvas(true);
                        }, 2000);
                    })
                    .catch(err => {
                        resetBtn.name = "❌ Reset Failed!";
                        appInstance.graph.setDirtyCanvas(true);
                        console.error("[AK] Reset error:", err);

                        setTimeout(() => {
                            resetBtn.name = originalName;
                            resetBtn._akBusy = false;
                            appInstance.graph.setDirtyCanvas(true);
                        }, 2000);
                    });
            });

            // Move browse button right after folder_path
            const ws = this.widgets;
            const btnIdx = ws.indexOf(browseBtn);
            const fpIdx = ws.indexOf(fpWidget);
            if (btnIdx > fpIdx + 1) {
                ws.splice(btnIdx, 1);
                ws.splice(fpIdx + 1, 0, browseBtn);
            }

            return r;
        };
    }
});
