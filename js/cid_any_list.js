import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidAnyListExtension",
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CidAnyList") {
            // Store the original addInput method
            const origAddInput = nodeType.prototype.addInput;
            
            // Override addInput to handle node slot positions properly
            nodeType.prototype.addInput = function(name, type, options) {
                // Call the original method
                const result = origAddInput.call(this, name, type, options);
                
                // Sort inputs numerically
                if (this.inputs.length > 1) {
                    this.inputs.sort((a, b) => {
                        if (a.name === "item_1") return -1; // item_1 always first
                        if (b.name === "item_1") return 1;
                        
                        const aIndex = parseInt(a.name.split("_")[1]);
                        const bIndex = parseInt(b.name.split("_")[1]);
                        return aIndex - bIndex;
                    });
                }
                
                return result;
            };
            
            // Storing the original onNodeCreated
            const origOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                if (origOnNodeCreated) {
                    origOnNodeCreated.call(this);
                }
                
                // Flag to prevent infinite loop in connection handling
                this._handlingFirstConnection = false;
                
                // Ensure we only have item_1
                while (this.inputs.length > 0) {
                    this.removeInput(0);
                }
                
                // Add item_1 (this will be at the top position)
                this.addInput("item_1", "*");
                this.inputs[0].label = "any_1";
                
                // Set the output type to * (any)
                this.outputs[0].type = "*";
                this.outputs[0].name = "*";
                this.outputs[0].label = "list_any";
                
                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
            };

            // Save the node's config with input slot info
            const origGetSerializedInfo = nodeType.prototype.getSerializedInfo;
            nodeType.prototype.getSerializedInfo = function() {
                const nodeInfo = origGetSerializedInfo ? origGetSerializedInfo.call(this) : this.serialize();
                nodeInfo.input_slots = this.inputs.map(input => input.name);
                nodeInfo.input_type = this.inputs[0].type;
                return nodeInfo;
            };

            // Override configure to restore the saved state
            const origConfigure = LGraphNode.prototype.configure;
            nodeType.prototype.configure = function (info) {
                // Remove item_1 from properties to prevent it from becoming a widget
                if (info.properties && info.properties.item_1 !== undefined) {
                    delete info.properties.item_1;
                }
                
                // Call original configure
                const result = origConfigure.call(this, info);
                this._was_configured = true;
                this._initial_config_info = info; // Store for use in onAfterGraphConfigured
                
                // Restore input slots if we have saved them
                if (info.input_slots && Array.isArray(info.input_slots)) {
                    // Clear current inputs
                    while (this.inputs.length > 0) {
                        this.removeInput(0);
                    }
                    
                    // Find highest connected input in the saved configuration
                    let highestConnectedIndex = -1;
                    if (info.inputs) {
                        for (const inputName in info.inputs) {
                            if (inputName.startsWith("item_")) {
                                const index = parseInt(inputName.split("_")[1]);
                                if (index > highestConnectedIndex) {
                                    highestConnectedIndex = index;
                                }
                            }
                        }
                    }
                    
                    // Restore the saved input type
                    const inputType = info.input_type || "*";
                    
                    // Restore all input slots
                    for (let i = 0; i < info.input_slots.length; i++) {
                        const slotName = info.input_slots[i];
                        this.addInput(slotName, inputType);
                    }
                    
                    // Add one more empty slot if the highest connected input is the last one
                    if (highestConnectedIndex === info.input_slots.length && info.input_slots.length < 20) {
                        this.addInput(`item_${info.input_slots.length + 1}`, inputType);
                    }
                    
                    // Set the output type to match the input type
                    if (this.outputs && this.outputs.length > 0) {
                        this.outputs[0].type = inputType;
                        this.outputs[0].name = inputType;
                        this.outputs[0].label = `list_${inputType.toLowerCase()}`;
                    }
                    
                    // Update input labels based on type
                    for (let i = 0; i < this.inputs.length; i++) {
                        const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                        this.inputs[i].label = `${inputType.toLowerCase()}_${inputIndex}`;
                    }
                } else {
                    // Default setup with just item_1
                    this.addInput("item_1", "*");
                    this.inputs[0].label = "any_1";
                }
                
                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
                
                return result;
            };

            // Adjust inputs after graph is loaded
            const origAfterConfigure = nodeType.prototype.onAfterGraphConfigured;
            nodeType.prototype.onAfterGraphConfigured = function () {
                if (origAfterConfigure) {
                    origAfterConfigure.call(this);
                }

                if (!this._was_configured) {
                    return;
                }

                // Find highest connected input
                let highestConnectedIndex = -1;
                for (let i = 0; i < this.inputs.length; i++) {
                    if (this.getInputLink(i) != null) {
                        highestConnectedIndex = i;
                    }
                }
                
                // Keep only connected inputs plus one extra slot
                const keepCount = Math.max(highestConnectedIndex + 2, 1);
                
                // Remove excess inputs, but make sure we keep at least 1 input
                while (this.inputs.length > keepCount) {
                    this.removeInput(this.inputs.length - 1);
                }
                
                // Make sure we have at least item_1
                if (this.inputs.length === 0) {
                    this.addInput("item_1", "*");
                    this.inputs[0].label = "any_1";
                }

                // Get input type from connections or restore from saved config
                let inputType = "*";
                for (let i = 0; i < this.inputs.length; i++) {
                    const link = this.getInputLink(i);
                    if (link) {
                        const originNode = app.graph.getNodeById(link.origin_id);
                        if (originNode && originNode.outputs && originNode.outputs[link.origin_slot]) {
                            inputType = originNode.outputs[link.origin_slot].type;
                            break;
                        }
                    }
                }

                // If no connections but we have stored input type, use that
                if (inputType === "*" && this._initial_config_info && this._initial_config_info.input_type) {
                    inputType = this._initial_config_info.input_type;
                }

                // Update input and output labels based on type
                if (inputType !== "*") {
                    for (let i = 0; i < this.inputs.length; i++) {
                        this.inputs[i].type = inputType;
                        const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                        this.inputs[i].label = `${inputType.toLowerCase()}_${inputIndex}`;
                    }
                    
                    if (this.outputs && this.outputs.length > 0) {
                        this.outputs[0].type = inputType;
                        this.outputs[0].name = inputType;
                        this.outputs[0].label = `list_${inputType.toLowerCase()}`;
                    }
                } else {
                    // Reset to any type labels if no connections
                    for (let i = 0; i < this.inputs.length; i++) {
                        const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                        this.inputs[i].label = `any_${inputIndex}`;
                    }
                    
                    if (this.outputs && this.outputs.length > 0) {
                        this.outputs[0].label = "list_any";
                    }
                }

                // Remove any item_1 widget (it should only be an input)
                if (this.widgets) {
                    const itemWidgetIndex = this.widgets.findIndex(w => w.name === "item_1");
                    if (itemWidgetIndex !== -1) {
                        this.widgets.splice(itemWidgetIndex, 1);
                    }
                }

                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
            };

            // Store original onConnectionsChange
            const origOnConnChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (origOnConnChange) {
                    origOnConnChange.call(this, type, index, connected, link_info);
                }
                
                // Handle input connections
                if (type === 1) { // Input connection change
                    if (connected) {
                        // A new connection has been made
                        if (link_info && index === 0 && !this._handlingFirstConnection) {
                            // First input determines the type for all inputs
                            const originNode = app.graph.getNodeById(link_info.origin_id);
                            if (originNode && originNode.outputs && originNode.outputs[link_info.origin_slot]) {
                                const inputType = originNode.outputs[link_info.origin_slot].type;
                                
                                // Set flag to prevent infinite loop
                                this._handlingFirstConnection = true;
                                
                                // Update all input types and labels first
                                for (let i = 0; i < this.inputs.length; i++) {
                                    this.inputs[i].type = inputType;
                                    const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    this.inputs[i].name = `item_${inputIndex}`;
                                    this.inputs[i].label = `${inputType.toLowerCase()}_${inputIndex}`;
                                }
                                
                                // Update output type and label
                                if (this.outputs && this.outputs.length > 0) {
                                    this.outputs[0].type = inputType;
                                    this.outputs[0].name = inputType;
                                    this.outputs[0].label = `list_${inputType.toLowerCase()}`;
                                }
                                
                                // Force the link to use the correct color
                                if (this.inputs[0].link !== null && this.inputs[0].link !== undefined) {
                                    const link = app.graph.links[this.inputs[0].link];
                                    if (link) {
                                        // Creating a new temporary style for this link
                                        link._color_cache = null; // Reset color cache
                                        app.graph.setDirtyCanvas(true, true);
                                    }
                                }
                                
                                // Clear the flag
                                setTimeout(() => {
                                    this._handlingFirstConnection = false;
                                }, 50);
                            }
                        }
                        
                        // If the last input is connected, add a new one if we're under 20
                        let isLastInput = true;
                        const currentName = this.inputs[index].name;
                        const currentIndex = parseInt(currentName.split("_")[1]);
                        
                        for (let i = 0; i < this.inputs.length; i++) {
                            if (i !== index) {
                                const inputName = this.inputs[i].name;
                                const inputIndex = parseInt(inputName.split("_")[1]);
                                if (inputIndex > currentIndex) {
                                    isLastInput = false;
                                    break;
                                }
                            }
                        }
                        
                        if (isLastInput && this.inputs.length < 20) {
                            const inputType = this.inputs[0].type;
                            const newIndex = currentIndex + 1;
                            this.addInput(`item_${newIndex}`, inputType);
                            this.inputs[this.inputs.length - 1].label = `${inputType.toLowerCase()}_${newIndex}`;
                        }
                    } else {
                        // Disconnection
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
                                    targetSlot: i
                                });
                            }
                        }
                        
                        // Disconnect all inputs after the disconnected one
                        for (let i = this.inputs.length - 1; i > index; i--) {
                            if (this.getInputLink(i)) {
                                this.disconnectInput(i);
                            }
                        }
                        
                        // Reconnect all stored connections one slot up
                        for (const conn of connectionsToMove) {
                            const newSlot = conn.targetSlot - 1;
                            conn.originNode.connect(conn.originSlot, this, newSlot);
                        }
                        
                        // Adjust the number of inputs
                        let highestConnectedInput = -1;
                        for (let i = 0; i < this.inputs.length; i++) {
                            if (this.inputs[i] && this.getInputLink(i) != null) {
                                highestConnectedInput = i;
                            }
                        }
                        
                        const keepCount = Math.max(highestConnectedInput + 2, 1);
                        
                        // Remove excess inputs
                        while (this.inputs.length > keepCount) {
                            this.removeInput(this.inputs.length - 1);
                        }
                        
                        // Ensure we always have at least one input
                        if (this.inputs.length === 0) {
                            this.addInput("item_1", "*");
                        }
                        
                        // If no connections remain, reset to any type
                        let hasConnections = false;
                        for (let i = 0; i < this.inputs.length; i++) {
                            if (this.getInputLink(i) != null) {
                                hasConnections = true;
                                break;
                            }
                        }
                        
                        if (!hasConnections) {
                            // Reset to any type
                            for (let i = 0; i < this.inputs.length; i++) {
                                this.inputs[i].type = "*";
                                const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                this.inputs[i].label = `any_${inputIndex}`;
                            }
                            
                            if (this.outputs && this.outputs.length > 0) {
                                this.outputs[0].type = "*";
                                this.outputs[0].name = "*";
                                this.outputs[0].label = "list_any";
                            }
                        }
                    }

                    if (this.computeSize) {
                        const newSize = this.computeSize();
                        this.size = newSize;
                        this.setDirtyCanvas(true, true);
                    }
                }
            };
        }
    }
});
