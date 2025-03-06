
var shell = require('shelljs');

shell.rm('-rf', 'src/ipywwt/web_static/research');
shell.mkdir('-p', 'src/ipywwt/web_static/research');
shell.cp('-r', 'node_modules/@wwtelescope/research-app/dist/*', 'src/ipywwt/web_static/research');