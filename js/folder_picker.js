import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
    name: "AngelosKar.FolderPicker",

    async beforeRegisterNodeDef(nodeType, nodeData, appInstance) {
        if (nodeData.name !== "AK_FolderPicker") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            const folderWidget = this.widgets.find((w) => w.name === "folder_path");

            // ── Browse Button ──
            this.addWidget("button", "📂 Browse Folder", "browse", () => {
                api.fetchApi('/angeloskar/choose_folder', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if (data.path) {
                            folderWidget.value = data.path;
                            appInstance.graph.setDirtyCanvas(true);
                        }
                    })
                    .catch(err => console.error("[AK] Folder picker error:", err));
            });

            // Move button above the path field
            this.widgets.unshift(this.widgets.pop());

            return r;
        };
    }
});