/**
 * CidTimerStart frontend extension.
 *
 * The node itself is a plain pass-through; this only reflects the connected
 * input type onto the pass-through output so the widget shows e.g. LATENT
 * instead of * while spliced into a data path.
 */

import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "CidTimerStartExtension",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "CidTimerStart") return;

    const origOnConnChange = nodeType.prototype.onConnectionsChange;
    nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
      origOnConnChange?.call(this, type, index, connected, link_info);
      if (type !== 1) return;
      const input = this.inputs?.[index];
      if (!input || input.name !== "passthrough") return;
      let newType = "*";
      if (connected && link_info) {
        const originNode = app.graph.getNodeById(link_info.origin_id);
        const out = originNode?.outputs?.[link_info.origin_slot];
        if (out?.type && out.type !== "*") newType = out.type;
      }
      const output = this.outputs?.[0];
      if (output) {
        output.type = newType;
        output.label = newType;
        output.name = newType;
      }
    };
  },
});
