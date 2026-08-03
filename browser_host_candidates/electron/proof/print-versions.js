console.log(JSON.stringify({
  electron: process.versions.electron,
  chromium: process.versions.chrome,
  node: process.versions.node,
  v8: process.versions.v8,
  platform: process.platform,
  arch: process.arch
}, null, 2));
