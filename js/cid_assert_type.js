import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidAssertTypeExtension",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "CidAssertType") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.call(this);
                }

                const widget = this.widgets.find(w => w.name === "assert_type");

                const updateOutputType = () => {
                    const selectedType = widget?.value || "STRING";

                    if (this.outputs && this.outputs.length > 0) {
                        this.outputs[0].type = selectedType;
                        this.outputs[0].name = selectedType;
                        this.outputs[0].label = selectedType;
                    }

                    if (this.computeSize) {
                        this.size = this.computeSize();
                        this.setDirtyCanvas(true, true);
                    }
                };

                if (widget) {
                    const originalCallback = widget.callback;
                    widget.callback = (value) => {
                        if (originalCallback) originalCallback.call(widget, value);
                        updateOutputType();
                    };
                }

                this._cidUpdateAssertTypeOutput = updateOutputType;
                updateOutputType();
            };

            const originalOnConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (originalOnConfigure) {
                    originalOnConfigure.call(this, info);
                }

                if (this._cidUpdateAssertTypeOutput) {
                    this._cidUpdateAssertTypeOutput();
                }
            };
        }
    }
});
