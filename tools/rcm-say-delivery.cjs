"use strict";
// Stable Say-only CLI exports. Keeps the original private Say journal and
// physically proven delivery behavior while sharing coordinator code.
const coordinator=require("./rcm-delivery-coordinator-core.cjs").createCoordinator("say");
if(require.main===module)coordinator.main();
module.exports=coordinator;
