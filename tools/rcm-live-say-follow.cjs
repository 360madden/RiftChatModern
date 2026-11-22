"use strict";
// Stable Say-specific CLI/API backed by the shared, source-integrity-checked
// read-only Log.txt follower. Only the proven RIFT Live Say syntax is accepted.
const core=require("./rcm-live-social-follow-core.cjs");
function follow(cfg,emit){return core.follow(cfg,emit,"say");}
function start(argv){return core.start(argv,"say");}
function isObservedSay(event){return core.isObserved("say",event);}
if(require.main===module)start();
module.exports={parseArgs:core.parseArgs,sourceInfo:core.sourceInfo,
  anchorFor:core.anchorFor,isObservedSay,follow,run:start};
