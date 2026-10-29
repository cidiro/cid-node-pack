"""Standalone headless DOM/canvas smoke test, using ComfyUI API stubs.

Run: python3 tests/browser_ab_testing.py /path/to/chrome-headless-shell
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import io
import base64
import json
import subprocess
import sys
import tempfile
import threading
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HTML = '''<!doctype html><style>body {background:#333} #host{width:440px;height:600px}</style><div id="host"></div>
<script type="module">
import {mountTournament} from '/extensions/cid/cid_image_ab_testing.js';
const assert=(x,m)=>{if(!x) throw Error(m)};
const pause=()=>new Promise(r=>setTimeout(r,350));
let errors=[]; window.addEventListener('error',e=>errors.push(e.message));
const host=document.querySelector('#host');
const node={properties:{},inputs:[],widgets:[{name:'max_votes',value:30}],setDirtyCanvas(){},
  addDOMWidget(n,t,root){host.replaceChildren(root);return {}}};
const manifest={id:'browser',seed:123,budget:30,images:Array.from({length:5},(_,i)=>({id:String(i),preview:{filename:String(i),type:'temp',subfolder:'qa'}}))};
const btn=text=>[...host.querySelectorAll('button')].find(b=>b.textContent===text);
try {
  let ui=mountTournament(node);ui.load(manifest);await pause();
  assert(!btn('Choose A').disabled,'previews loaded');
  btn('Choose A').click();btn('Choose A').click();
  assert(node.properties.cid_ab_session.used===1,'double-click guard');await pause();
  const state=JSON.parse(JSON.stringify(node.properties.cid_ab_session));
  btn('Undo Last Vote').click();assert(node.properties.cid_ab_session.used===0,'undo refunded');
  ui.load(state,true);assert(node.properties.cid_ab_session.used===1,'restore vote');
  btn('Slide / Click').click();
  const canvas=host.querySelector('canvas');canvas.dispatchEvent(new PointerEvent('pointermove',{clientX:100}));
  host.style.width='360px';await pause();
  btn('End Session').click();assert(host.textContent.includes('Select image 5'),'all candidates in early selection');
  btn('Select image 5').click();assert(node.properties.cid_ab_session.result.winner===4,'human selection');
  assert(host.textContent.includes('incomplete round-robin'),'honest label');
  ui.dispose();ui=mountTournament(node);ui.load(manifest);await pause();
  let guard=0;
  while(!node.properties.cid_ab_session.result && guard++<30){
    const pair=node.properties.cid_ab_session.queue[0];
    btn(pair[0]<pair[1]?'Choose A':'Choose B').click();await pause();
  }
  assert(node.properties.cid_ab_session.result.method==='confirmed','confirmed winner shown');
  assert(host.textContent.includes('Selected image 1'),'winner preview');
  btn('Undo Last Vote').click();assert(!node.properties.cid_ab_session.result,'undo completed session');
  ui.load({...manifest,id:'new-run'});assert(node.properties.cid_ab_session.used===0,'new run resets');
  ui.load({...manifest,id:'missing',images:manifest.images.map(x=>({...x,preview:{filename:'missing'}}))});await pause();
  assert(host.textContent.includes('Preview unavailable'),'missing preview message');
  assert(btn('Choose A').disabled,'missing images cannot vote');
  assert(!errors.length,errors.join(';'));
  document.body.dataset.test='PASS'; document.body.append('PASS: canvas, votes, undo, restore, early selection, confirmation, missing previews');
} catch(e) {document.body.dataset.test='FAIL';document.body.append(e.stack)}
</script>'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_GET(self):
        path = self.path.split('?')[0]
        status, mime = 200, 'text/javascript'
        if path == '/':
            data, mime = HTML.encode(), 'text/html'
        elif path == '/scripts/app.js':
            data = b'export const app={registerExtension(){},graph:{links:{}}};'
        elif path == '/scripts/api.js':
            data = b'export const api={apiURL:x=>x};'
        elif path in ('/extensions/cid/cid_image_ab_testing.js', '/extensions/cid/cid_image_ab_testing_engine.mjs'):
            data = (ROOT / 'js' / path.rsplit('/', 1)[1]).read_bytes()
        elif path == '/view' and 'missing' not in self.path:
            image = io.BytesIO(); Image.new('RGB', (100, 70), '#568cab').save(image, format='PNG')
            data, mime = image.getvalue(), 'image/png'
        else:
            status, data = 404, b'missing'
        self.send_response(status);self.send_header('Content-Type', mime);self.end_headers();self.wfile.write(data)

if __name__ == '__main__':
    # A self-contained file mode needs no HTTP listener or network access.
    server = None
    if '--file' not in sys.argv:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='cid-ab-browser-') as profile:
            url = f'http://127.0.0.1:{server.server_port}' if server else None
            if not server:
                def module_url(text):
                    return 'data:text/javascript;base64,' + base64.b64encode(text.encode()).decode()
                img = io.BytesIO();Image.new('RGB',(100,70),'#568cab').save(img,format='PNG')
                png = 'data:image/png;base64,' + base64.b64encode(img.getvalue()).decode()
                engine = module_url((ROOT/'js/cid_image_ab_testing_engine.mjs').read_text())
                source = (ROOT/'js/cid_image_ab_testing.js').read_text()
                source = source.replace("import { app } from '../../scripts/app.js';", 'const app={registerExtension(){},graph:{links:{}}};')
                source = source.replace("import { api } from '../../scripts/api.js';", 'const api={apiURL:x=>x.includes("missing") ? "data:image/png;base64,INVALID" : '+json.dumps(png)+'};')
                source = source.replace("'./cid_image_ab_testing_engine.mjs'",json.dumps(engine))
                page = Path(profile)/'test.html'
                page.write_text(HTML.replace('/extensions/cid/cid_image_ab_testing.js',module_url(source)))
                url = page.as_uri()
            result = subprocess.run([sys.argv[1], '--headless', '--no-sandbox', '--disable-gpu',
                f'--user-data-dir={profile}', '--virtual-time-budget=20000', '--dump-dom',
                '--screenshot=/tmp/cid-ab-testing.png', '--window-size=600,800',
                url], capture_output=True, text=True, timeout=45)
            if 'data-test="PASS"' not in result.stdout:
                print(result.stdout);print(result.stderr);raise SystemExit(1)
            print('PASS headless browser: canvas, double-click guard, Undo, restore, early selection, confirmation, missing previews')
    finally:
        if server:
            server.shutdown();server.server_close()
