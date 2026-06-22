import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "CidConcatenateStringsExtension",
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CidConcatenateStrings") {
            // Store the original addInput method
            const origAddInput = nodeType.prototype.addInput;
            
            // Override addInput to handle node slot positions properly
            nodeType.prototype.addInput = function(name, type, options) {
                // Call the original method
                const result = origAddInput.call(this, name, type, options);
                
                // Sort inputs - make sure string_X are sorted numerically and placed before other inputs
                if (this.inputs.length > 1) {
                    this.inputs.sort((a, b) => {
                        const aIsString = a.name.startsWith("string_");
                        const bIsString = b.name.startsWith("string_");
                        
                        if (aIsString && bIsString) {
                            if (a.name === "string_1") return -1;
                            if (b.name === "string_1") return 1;
                            const aIndex = parseInt(a.name.split("_")[1]);
                            const bIndex = parseInt(b.name.split("_")[1]);
                            return aIndex - bIndex;
                        } else if (aIsString && !bIsString) {
                            return -1;
                        } else if (!aIsString && bIsString) {
                            return 1;
                        }
                        return 0; // Both are not string_, leave order as is
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
                
                // Remove all string_ inputs (in case ComfyUI adds them differently)
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    if (this.inputs[i].name.startsWith("string_")) {
                        this.removeInput(i);
                    }
                }
                
                // Add string_1 (this will be at the top position because of our sorter)
                this.addInput("string_1", "STRING");
                
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
                return nodeInfo;
            };

            // Override configure to restore the saved state
            const origConfigure = LGraphNode.prototype.configure;
            nodeType.prototype.configure = function (info) {
                // Remove string_1 from properties to prevent it from becoming a widget
                if (info.properties && info.properties.string_1 !== undefined) {
                    delete info.properties.string_1;
                }
                
                // Call original configure
                const result = origConfigure.call(this, info);
                this._was_configured = true;
                
                // Restore input slots if we have saved them
                if (info.input_slots && Array.isArray(info.input_slots)) {
                    // Remember non-string inputs that were already restored by origConfigure
                    const nonStringInputs = this.inputs.filter(inp => !inp.name.startsWith("string_"));
                    
                    // Clear current inputs
                    while (this.inputs.length > 0) {
                        this.removeInput(0);
                    }
                    
                    // Find highest connected input in the saved configuration
                    let highestConnectedIndex = -1;
                    if (info.inputs) {
                        for (const inputName in info.inputs) {
                            if (inputName.startsWith("string_")) {
                                const index = parseInt(inputName.split("_")[1]);
                                if (index > highestConnectedIndex) {
                                    highestConnectedIndex = index;
                                }
                            }
                        }
                    }
                    
                    // Determine which string_ slots to restore
                    const stringSlotsToRestore = info.input_slots.filter(name => {
                        if (!name.startsWith("string_")) return false;
                        if (name === "string_1") return true; // Always keep string_1
                        
                        const index = parseInt(name.split("_")[1]);
                        // Keep inputs that are connected or one slot after the highest connected
                        return index <= highestConnectedIndex + 1;
                    });
                    
                    // Restore string inputs
                    for (const inputName of stringSlotsToRestore) {
                        this.addInput(inputName, "STRING");
                    }
                    
                    // Restore non-string inputs from either saved slots or originally configured
                    const savedNonStringSlots = info.input_slots.filter(name => !name.startsWith("string_"));
                    for (const inputName of savedNonStringSlots) {
                        // Find if this non-string input already existed (e.g., separator converted to input)
                        const existing = nonStringInputs.find(inp => inp.name === inputName);
                        if (existing) {
                            this.addInput(existing.name, existing.type, existing);
                        } else {
                            // Guess STRING type, or leave it to standard ComfyUI restoration
                            this.addInput(inputName, "*"); 
                        }
                    }
                    
                    // Re-add any non-string inputs that weren't in the saved slots but exist in the node
                    for (const existing of nonStringInputs) {
                        if (!this.inputs.find(inp => inp.name === existing.name)) {
                            this.addInput(existing.name, existing.type, existing);
                        }
                    }
                    
                    // Make sure we have at least string_1 and string_2
                    if (!this.inputs.find(inp => inp.name === "string_1")) {
                        this.addInput("string_1", "STRING");
                    }
                    if (!this.inputs.find(inp => inp.name === "string_2")) {
                        this.addInput("string_2", "STRING");
                    }
                    
                    if (this.computeSize) {
                        const newSize = this.computeSize();
                        this.size = newSize;
                        this.setDirtyCanvas(true, true);
                    }
                }
                
                // Also make sure no string_X widgets exist
                if (this.widgets) {
                    for (let i = this.widgets.length - 1; i >= 0; i--) {
                        if (this.widgets[i].name.startsWith("string_")) {
                            this.widgets.splice(i, 1);
                        }
                    }
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
                    if (this.inputs[i].name.startsWith("string_") && this.getInputLink(i) != null) {
                        const index = parseInt(this.inputs[i].name.split("_")[1]);
                        if (index > highestConnectedIndex) {
                            highestConnectedIndex = index;
                        }
                    }
                }
                
                // Keep only connected inputs plus one extra slot
                const keepCount = Math.max(highestConnectedIndex + 1, 2); // 1-based indexing, min 2 slots
                
                // Remove excess inputs
                for (let i = this.inputs.length - 1; i >= 0; i--) {
                    if (this.inputs[i].name.startsWith("string_")) {
                        const index = parseInt(this.inputs[i].name.split("_")[1]);
                        if (index > keepCount) {
                            this.removeInput(i);
                        }
                    }
                }
                
                // Make sure we have at least string_1 and string_2
                if (!this.inputs.find(inp => inp.name === "string_1")) {
                    this.addInput("string_1", "STRING");
                }
                if (!this.inputs.find(inp => inp.name === "string_2")) {
                    this.addInput("string_2", "STRING");
                }

                // Remove any string_X widgets
                if (this.widgets) {
                    for (let i = this.widgets.length - 1; i >= 0; i--) {
                        if (this.widgets[i].name.startsWith("string_")) {
                            this.widgets.splice(i, 1);
                        }
                    }
                }

                if (this.computeSize) {
                    const newSize = this.computeSize();
                    this.size = newSize;
                    this.setDirtyCanvas(true, true);
                }
            };

            // Dynamically manage inputs when connections change
            const origOnConnChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (type === 1) { // Input connection change
                    const changedInput = this.inputs[index];
                    
                    // Only process dynamic logic for string_ inputs
                    if (changedInput && changedInput.name.startsWith("string_")) {
                        if (connected) {
                            // Check if this is the last string_ input
                            let isLastStringInput = true;
                            const currentIndex = parseInt(changedInput.name.split("_")[1]);
                            
                            for (let i = 0; i < this.inputs.length; i++) {
                                if (i !== index && this.inputs[i].name.startsWith("string_")) {
                                    const inputIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    if (inputIndex > currentIndex) {
                                        isLastStringInput = false;
                                        break;
                                    }
                                }
                            }
                            
                            if (isLastStringInput && this.inputs.length < 20) { // Limit to 20 total inputs (or string inputs)
                                this.addInput(`string_${currentIndex + 1}`, "STRING");
                            }
                        } else {
                            // Disconnected
                            const currentIndex = parseInt(changedInput.name.split("_")[1]);
                            
                            // Store all connections after the disconnected slot
                            const connectionsToMove = [];
                            
                            // Find all string inputs that come after the disconnected one and are connected
                            for (let i = 0; i < this.inputs.length; i++) {
                                if (this.inputs[i].name.startsWith("string_")) {
                                    const stringIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    if (stringIndex > currentIndex) {
                                        const link = this.getInputLink(i);
                                        if (link) {
                                            const originNode = app.graph.getNodeById(link.origin_id);
                                            const originSlot = link.origin_slot;
                                            connectionsToMove.push({
                                                originNode: originNode,
                                                originSlot: originSlot,
                                                oldStringIndex: stringIndex
                                            });
                                        }
                                    }
                                }
                            }
                            
                            // Disconnect all string inputs after the disconnected one
                            for (let i = this.inputs.length - 1; i >= 0; i--) {
                                if (this.inputs[i].name.startsWith("string_")) {
                                    const stringIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    if (stringIndex > currentIndex && this.getInputLink(i)) {
                                        this.disconnectInput(i);
                                    }
                                }
                            }
                            
                            // Reconnect all stored connections one slot up
                            for (const conn of connectionsToMove) {
                                const newStringIndex = conn.oldStringIndex - 1;
                                // Find the slot index for the new string index
                                let targetSlotIndex = -1;
                                for (let i = 0; i < this.inputs.length; i++) {
                                    if (this.inputs[i].name === `string_${newStringIndex}`) {
                                        targetSlotIndex = i;
                                        break;
                                    }
                                }
                                
                                // If the slot doesn't exist yet, create it
                                if (targetSlotIndex === -1) {
                                    this.addInput(`string_${newStringIndex}`, "STRING");
                                    targetSlotIndex = this.inputs.length - 1;
                                }
                                
                                conn.originNode.connect(conn.originSlot, this, targetSlotIndex);
                            }
                            
                            // Adjust the number of inputs
                            let highestConnectedStringIndex = 0;
                            for (let i = 0; i < this.inputs.length; i++) {
                                if (this.inputs[i].name.startsWith("string_") && this.getInputLink(i) != null) {
                                    const stringIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    if (stringIndex > highestConnectedStringIndex) {
                                        highestConnectedStringIndex = stringIndex;
                                    }
                                }
                            }
                            
                            const keepCount = Math.max(highestConnectedStringIndex + 1, 1);
                            
                            // Remove excess string inputs
                            for (let i = this.inputs.length - 1; i >= 0; i--) {
                                if (this.inputs[i].name.startsWith("string_")) {
                                    const stringIndex = parseInt(this.inputs[i].name.split("_")[1]);
                                    if (stringIndex > keepCount) {
                                        this.removeInput(i);
                                    }
                                }
                            }
                            
                            // Ensure we always have at least string_1
                            if (!this.inputs.find(inp => inp.name === "string_1")) {
                                this.addInput("string_1", "STRING");
                            }
                        }
                    }

                    if (this.computeSize) {
                        const newSize = this.computeSize();
                        this.size = newSize;
                        this.setDirtyCanvas(true, true);
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