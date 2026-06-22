import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidGetGlobalVariableExtension",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "CidGetGlobalVariable") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.call(this);
                }

                const widget = this.widgets.find(w => w.name === "output_type");

                const updateSlotTypes = () => {
                    const selectedType = widget.value === "*" ? "*" : widget.value;
                    const outputName = selectedType === "*" ? "value" : selectedType;

                    if (this.inputs && this.inputs.length > 0) {
                        this.inputs[0].type = selectedType;
                    }

                    if (this.outputs && this.outputs.length > 0) {
                        this.outputs[0].type = selectedType;
                        this.outputs[0].name = outputName;
                        this.outputs[0].label = outputName;
                    }
                };

                if (widget) {
                    const originalCallback = widget.callback;
                    widget.callback = (value) => {
                        if (originalCallback) originalCallback.call(widget, value);
                        updateSlotTypes();
                    };
                }

                this._cidUpdateSlotTypes = updateSlotTypes;
            };

            const originalOnConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function (info) {
                if (originalOnConfigure) {
                    originalOnConfigure.call(this, info);
                }

                if (this._cidUpdateSlotTypes) {
                    this._cidUpdateSlotTypes();
                }
            };
        }
    }
});
