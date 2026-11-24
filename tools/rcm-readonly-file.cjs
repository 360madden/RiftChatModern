"use strict";

// Shared bounded read primitive for journals and dependency evidence.
// No writes, no symlink traversal at the inspected leaf, and no assumption
// that a missing path is equivalent to a corrupt or inaccessible file.
const fs=require("node:fs");

function stamp(s) {
    return [s.dev,s.ino,s.size,s.mtimeNs,s.ctimeNs].join(":");
}
function inspectPath(file,expected="file") {
    try {
        const s=fs.lstatSync(file,{bigint:true});
        const valid=!s.isSymbolicLink()&&
            (expected==="directory"?s.isDirectory():s.isFile());
        return {state:valid?"present":"unsafe",stat:s,stamp:stamp(s)};
    } catch(e) {
        return {state:e.code==="ENOENT"?"absent":"unreadable",stamp:null};
    }
}
function comparable(a,b) {
    return a.state===b.state&&a.stamp===b.stamp;
}
function readBounded(file,maxBytes,before=inspectPath(file)) {
    if(before.state!=="present")throw Error("file_not_regular");
    if(!Number.isSafeInteger(maxBytes)||maxBytes<1||before.stat.size>BigInt(maxBytes))
        throw Error("file_over_budget");
    let fd;
    try {
        // The descriptor identity check prevents reading a replacement file
        // after the lstat check. On hosts supporting O_NOFOLLOW, reject a
        // symlink substituted between lstat and open as well.
        fd=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
        const opened=fs.fstatSync(fd,{bigint:true});
        if(!opened.isFile()||stamp(opened)!==before.stamp)
            throw Error("file_changed_during_read");
        const size=Number(opened.size);
        const buffer=Buffer.alloc(size+1);
        let read=0;
        while(read<buffer.length) {
            const n=fs.readSync(fd,buffer,read,buffer.length-read,null);
            if(n===0)break;
            read+=n;
        }
        if(read!==size||stamp(fs.fstatSync(fd,{bigint:true}))!==before.stamp||
            !comparable(before,inspectPath(file)))
            throw Error("file_changed_during_read");
        return buffer.subarray(0,read);
    } finally {
        if(fd!==undefined)fs.closeSync(fd);
    }
}

module.exports={inspectPath,comparable,readBounded};
