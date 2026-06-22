import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidAnySyncExtension",
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CidAnySync") {
            const origOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (origOnNodeCreated) {
                    origOnNodeCreated.call(this);
                }

                while (this.outputs.length > 1) {
                    this.removeOutput(this.outputs.length - 1);
                }

                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
            };

            nodeType.prototype.configure = function (info) {
                LGraphNode.prototype.configure.call(this, info);

                this._was_configured = true;

                return true;
            };

            // Adjust inputs/outputs after graph is loaded based on existing connections
            const origAfterConfigure = nodeType.prototype.onAfterGraphConfigured;
            nodeType.prototype.onAfterGraphConfigured = function () {
                if (origAfterConfigure) {
                    origAfterConfigure.call(this);
                }

                if (!this._was_configured) {
                    return;
                }

                let highestConnectedInputSlot = -1;

                for (let i = 0; i < this.inputs.length; i++) {
                    if (this.inputs[i] && this.getInputLink(i) != null) {
                        highestConnectedInputSlot = i;
                    }
                }

                const keepCount = highestConnectedInputSlot + 2;

                while (this.outputs.length > keepCount) {
                    this.removeOutput(this.outputs.length - 1);
                }

                while (this.inputs.length > keepCount) {
                    this.removeInput(this.inputs.length - 1);
                }

                if (this.inputs.length === 0) {
                    this.addInput("input_1", "*");
                }

                if (this.outputs.length === 0) {
                    this.addOutput("*", "*");
                }

                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
            };

            // Dynamically manage inputs/outputs when connections change
            const origOnConnChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (type === 1) { // Input connection change
                    if (connected) {
                        // When an input is connected, copy the type from the source
                        let newType = "*";
                        if (link_info) {
                            const originNode = app.graph.getNodeById(link_info.origin_id);
                            newType = originNode.outputs[link_info.origin_slot].type;
                        }
                        if (newType && newType !== "*") {
                            this.inputs[index].type = newType;
                            this.outputs[index].type = newType;
                            this.outputs[index].label = newType;
                            this.outputs[index].name = newType;
                        }
                        // When the last slot is connected, add a new slot
                        if (index === this.inputs.length - 1 && this.inputs.length < 10) {
                            const newIndex = this.inputs.length + 1;
                            this.addInput(`input_${newIndex}`, "*");
                            this.addOutput("*", "*");
                        }
                    } else {
                        // Store all connections after the disconnected slot
                        const connectionsToMove = [];
                        for (let i = index + 1; i < this.inputs.length; i++) {
                            const link = this.getInputLink(i);
                            if (link) {
                                const originNode = app.graph.getNodeById(link.origin_id);
                                const originSlot = link.origin_slot;
                                connectionsToMove.push({
                                    originNode: originNode,
                                    originSlot: originSlot,
                                    targetSlot: i,
                                    type: this.inputs[i].type
                                });
                            }
                        }
                        
                        // Disconnect all inputs after the disconnected one
                        for (let i = this.inputs.length - 1; i > index; i--) {
                            if (this.getInputLink(i)) {
                                this.disconnectInput(i);
                            }
                        }
                        
                        // Reset the types of the disconnected slot
                        if (index < this.inputs.length) {
                            this.inputs[index].type = "*";
                            this.outputs[index].type = "*";
                            this.outputs[index].label = "*";
                            this.outputs[index].name = "*";
                        }
                        
                        // Reconnect all stored connections one slot up
                        for (const conn of connectionsToMove) {
                            const newSlot = conn.targetSlot - 1;
                            conn.originNode.connect(conn.originSlot, this, newSlot);
                            
                            // Set the type for the new connection if it wasn't "*"
                            if (conn.type && conn.type !== "*") {
                                this.inputs[newSlot].type = conn.type;
                                this.outputs[newSlot].type = conn.type;
                                this.outputs[newSlot].label = conn.type;
                                this.outputs[newSlot].name = conn.type;
                            }
                        }
                        
                        // Adjust the number of inputs/outputs
                        let highestConnectedInput = -1;
                        for (let i = 0; i < this.inputs.length; i++) {
                            if (this.inputs[i] && this.getInputLink(i) != null) {
                                highestConnectedInput = i;
                            }
                        }
                        
                        const keepCount = Math.max(highestConnectedInput + 2, 1);
                        
                        // Remove excess inputs/outputs
                        while (this.inputs.length > keepCount) {
                            this.removeInput(this.inputs.length - 1);
                            this.removeOutput(this.outputs.length - 1);
                        }
                        
                        // Ensure we always have at least one input
                        if (this.inputs.length === 0) {
                            this.addInput("input_1", "*");
                            this.addOutput("*", "*");
                        }

                        if (this.computeSize) {
                            const newSize = this.computeSize();
                            this.size = newSize;
                            this.setDirtyCanvas(true, true);
                        }
                    }
                } else if (type === 2) { // Output connection change
                    if (origOnConnChange) {
                        origOnConnChange.call(this, type, index, connected, link_info);
                    }
                }
            };
        }
    }
});