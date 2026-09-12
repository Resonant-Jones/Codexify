// Rebuild the derived offline snapshot; repository Markdown remains authoritative.
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const root = path.join(__dirname, '..');
const directory = 'docs/architecture/';
const names = ['00-current-state.md', 'README.md', 'kb-validity-matrix.md', 'architecture-atlas.md', 'modules-and-ownership.md', 'system-overview.md', 'flows.md', 'data-and-storage.md', ...fs.readdirSync(path.join(root, directory, 'adr')).filter(name => name.endsWith('.md')).sort().map(name => 'adr/' + name)];
const bundle = Object.fromEntries(names.map(name => [(directory + name).toLowerCase(), fs.readFileSync(path.join(root, directory, name), 'utf8')]));
const file = path.join(__dirname, 'rc-atlas-prototype.html');
const html = fs.readFileSync(file, 'utf8');
const pattern = /(<script data-atlas-offline-documents>[\s\S]*?atob\(")[A-Za-z0-9+/=]+("\))/;
if (!pattern.test(html)) throw new Error('Offline document marker missing');
const result = html.replace(pattern, (_, before, after) => before + zlib.gzipSync(JSON.stringify(bundle)).toString('base64') + after);
if (process.argv.includes('--check')) {
  if (result !== html) throw new Error('Offline documents are stale; run node projection-ui-map/refresh-atlas-documents.cjs');
} else fs.writeFileSync(file, result);
console.log('Offline document snapshot verified: ' + names.length + ' documents');
