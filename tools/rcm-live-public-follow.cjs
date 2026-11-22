"use strict";
// Separate bounded public channel follower. Current physically confirmed
// profile: numbered slot 4 / Level 1-29. No other formats are admitted.
const core=require("./rcm-live-social-follow-core.cjs");
function follow(cfg,emit){return core.follow(cfg,emit,"public");}
function start(argv){return core.start(argv,"public");}
function isObservedPublic(event){return core.isObserved("public",event);}
if(require.main===module)start();
module.exports={parseArgs:core.parseArgs,sourceInfo:core.sourceInfo,
  anchorFor:core.anchorFor,isObservedPublic,follow,run:start};
