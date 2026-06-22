import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidStoreAnyExtension",
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CidStoreAny") {
            const origOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (origOnNodeCreated) {
                    origOnNodeCreated.call(this);
                }
            };

            // Adjust inputs/outputs after graph is loaded
            const origAfterConfigure = nodeType.prototype.onAfterGraphConfigured;
            nodeType.prototype.onAfterGraphConfigured = function () {
                if (origAfterConfigure) {
                    origAfterConfigure.call(this);
                }
            };

            // Dynamically manage input/output type when connections change
            const origOnConnChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (origOnConnChange) {
                    origOnConnChange.call(this, type, index, connected, link_info);
                }

                if (type === 1) { // Input connection change
                    if (connected) {
                        // When an input is connected, copy the type from the source
                        let newType = "*";
                        if (link_info) {
                            const originNode = app.graph.getNodeById(link_info.origin_id);
                            if (originNode && originNode.outputs && originNode.outputs[link_info.origin_slot]) {
                                newType = originNode.outputs[link_info.origin_slot].type;
                            }
                        }
                        if (newType && newType !== "*") {
                            this.inputs[index].type = newType;
                            this.outputs[0].type = newType;
                            this.outputs[0].label = newType;
                            this.outputs[0].name = newType;
                        }
                    } else {
                        // Reset the types when disconnected
                        this.inputs[index].type = "*";
                        this.outputs[0].type = "*";
                        this.outputs[0].label = "*";
                        this.outputs[0].name = "*";
                    }
                }
            };
        }
    }
});
