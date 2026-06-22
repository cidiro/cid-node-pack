import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidAnyBufferExtension",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "CidAnyBuffer") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.call(this);
                }

                const widget = this.widgets.find(w => w.name === "buffer_size");

                // Dynamically update the number and type of outputs
                const updateOutputs = () => {
                    const count = widget.value || 5;

                    let currentType = this.inputs[0].type.toLowerCase() || "*";

                    while (this.outputs.length > count) {
                        this.removeOutput(this.outputs.length - 1);
                    }

                    while (this.outputs.length < count && this.outputs.length < 20) {
                        const idx = this.outputs.length + 1;
                        this.addOutput(`${currentType}_${idx}`, currentType);
                    }

                    for (let i = 0; i < this.outputs.length; i++) {
                        this.outputs[i].type = currentType;
                        this.outputs[i].name = currentType;
                        this.outputs[i].label = currentType !== "*" ? `${currentType}_${i + 1}` : `value_${i + 1}`;
                    }

                    if (this.computeSize) {
                        const newSize = this.computeSize();
                        this.size = newSize;
                    }
                };

                // Override the buffer_size widget callback to update outputs when changed
                if (widget) {
                    const originalCallback = widget.callback;
                    widget.callback = (value) => {
                        if (originalCallback) originalCallback.call(widget, value);
                        updateOutputs();
                    };
                }

                updateOutputs();
            };

            const origOnConnChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (origOnConnChange) {
                    origOnConnChange.call(this, type, index, connected, link_info);
                }

                // When an input connection is made, adopt the input type
                if (type === 1 && index === 0 && connected) {
                    if (link_info) {
                        const originNode = app.graph.getNodeById(link_info.origin_id);
                        if (originNode && originNode.outputs && originNode.outputs[link_info.origin_slot]) {
                            const originType = originNode.outputs[link_info.origin_slot].type.toLowerCase();

                            // Propagate the input type to all outputs
                            this.inputs[0].type = originType;

                            for (let i = 0; i < this.outputs.length; i++) {
                                this.outputs[i].type = originType;
                                this.outputs[i].name = originType;
                                this.outputs[i].label = `${originType}_${i + 1}`;
                            }
                        }
                    }
                }
                // When input is disconnected, reset to any type
                else if (type === 1 && index === 0 && !connected) {
                    this.inputs[0].type = "*";

                    for (let i = 0; i < this.outputs.length; i++) {
                        this.outputs[i].type = "*";
                        this.outputs[i].name = "*";
                        this.outputs[i].label = `value_${i + 1}`;
                    }
                }
            };
        }
    }
});