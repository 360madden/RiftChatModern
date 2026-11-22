"use strict";
// Separate public-channel CLI. Never admits Say or unverified social formats.
// Current accepted profile: RIFT numbered public slot 4, Level 1-29.
const coordinator=require("./rcm-delivery-coordinator-core.cjs").createCoordinator("public");
if(require.main===module)coordinator.main();
module.exports=coordinator;
