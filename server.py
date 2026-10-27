import os, json, sqlite3, secrets, hashlib, hmac, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
ROOT=Path(__file__).parent
DB=os.environ.get('DATABASE_PATH',str(ROOT/'data/site.db'))
Path(DB).parent.mkdir(parents=True,exist_ok=True)
PASSWORD=os.environ.get('ADMIN_PASSWORD','')
SESSIONS={}; ATTEMPTS={}
def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS providers(id INTEGER PRIMARY KEY,parent TEXT NOT NULL,name TEXT NOT NULL,state TEXT NOT NULL,ownership TEXT DEFAULT '',source TEXT DEFAULT '',demo INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,provider_id INTEGER,parent TEXT,name TEXT,state TEXT,category TEXT,rating INTEGER,body TEXT,source TEXT,status TEXT DEFAULT 'pending',created TEXT DEFAULT CURRENT_TIMESTAMP);''')
  if not c.execute('SELECT 1 FROM providers').fetchone():
   c.executemany('INSERT INTO providers(parent,name,state,ownership,demo) VALUES(?,?,?,?,1)', [('Example Response Group','Example County EMS','Texas','Fictional company for testing.'),('Example Response Group','Example Metro Ambulance','Illinois','Fictional company for testing.'),('Demo Medical Holdings','Demo Valley EMS','California','Fictional company for testing.')])
def clean(v,n=4000): return str(v or '').strip()[:n]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def reply(self,data,status=200):
  raw=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
 def admin(self):
  try:
   cookie=SimpleCookie(self.headers.get('Cookie','')); token=cookie['session'].value
   return SESSIONS.get(token,0)>time.time()
  except Exception:return False
 def do_GET(self):
  path=self.path.split('?')[0]
  if path=='/api/data':
   with connect() as c: self.reply({'providers':[dict(x) for x in c.execute('SELECT * FROM providers')],'reviews':[dict(x) for x in c.execute("SELECT id,kind,provider_id,category,rating,body,source,created FROM submissions WHERE status='approved' AND kind='review'")]})
  elif path=='/api/admin':
   if not self.admin():return self.reply({'error':'Sign in required'},401)
   with connect() as c:self.reply([dict(x) for x in c.execute('SELECT * FROM submissions ORDER BY id DESC')])
  else:
   files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
   if path not in files:return self.reply({'error':'Not found'},404)
   file=ROOT/'public'/files[path]; raw=file.read_bytes(); self.send_response(200); self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript','css':'text/css'}[file.suffix[1:]]); self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers();self.wfile.write(raw)
 def do_POST(self):
  origin=self.headers.get('Origin')
  if origin and origin.split('://')[-1]!=self.headers.get('Host'):return self.reply({'error':'Invalid origin'},403)
  try:
   length=int(self.headers.get('Content-Length',0))
   if length>20000:return self.reply({'error':'Request too large'},413)
   d=json.loads(self.rfile.read(length))
  except Exception:return self.reply({'error':'Invalid request'},400)
  if self.path=='/api/login':
   key=self.client_address[0]; attempts=[t for t in ATTEMPTS.get(key,[]) if t>time.time()-900]
   if len(attempts)>=10:return self.reply({'error':'Too many attempts. Try again in 15 minutes.'},429)
   if not PASSWORD:return self.reply({'error':'Set ADMIN_PASSWORD on the server to enable moderation.'},503)
   if not hmac.compare_digest(clean(d.get('password')),PASSWORD):
    ATTEMPTS[key]=attempts+[time.time()];return self.reply({'error':'Incorrect password'},401)
   token=secrets.token_urlsafe(32);SESSIONS[token]=time.time()+28800
   self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Set-Cookie',f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''));self.end_headers();self.wfile.write(b'{}');return
  if self.path=='/api/logout':
   try:SESSIONS.pop(SimpleCookie(self.headers.get('Cookie',''))['session'].value,None)
   except Exception:pass
   return self.reply({'ok':True})
  if self.path=='/api/moderate':
   if not self.admin():return self.reply({'error':'Sign in required'},401)
   if d.get('status') not in ['approved','rejected','pending']:return self.reply({'error':'Invalid status'},400)
   with connect() as c:
    row=c.execute('SELECT * FROM submissions WHERE id=?',(d.get('id'),)).fetchone()
    if not row:return self.reply({'error':'Submission not found'},404)
    if row['kind']=='provider' and d['status']=='approved' and not row['provider_id']:
     cursor=c.execute('INSERT INTO providers(parent,name,state,source) VALUES(?,?,?,?)',(row['parent'],row['name'],row['state'],row['source']));c.execute('UPDATE submissions SET provider_id=? WHERE id=?',(cursor.lastrowid,row['id']))
    c.execute('UPDATE submissions SET status=? WHERE id=?',(d['status'],row['id']))
   return self.reply({'ok':True})
  if self.path=='/api/submit':
   kind=d.get('kind'); body=clean(d.get('body')); source=clean(d.get('source'),1000)
   if kind not in ['review','provider'] or len(body)<20:return self.reply({'error':'Please provide at least 20 characters of detail.'},400)
   if source and not source.startswith(('https://','http://')):return self.reply({'error':'Source must be an http or https URL.'},400)
   with connect() as c:
    if kind=='review':
     if not c.execute('SELECT 1 FROM providers WHERE id=?',(d.get('provider_id'),)).fetchone():return self.reply({'error':'Choose a provider'},400)
     if d.get('category') not in ['Billing','No-haul billing','Other resident experience','Employee treatment','Profit sharing','Benefits and employee cost','Management connection','Ownership and assets']:return self.reply({'error':'Choose a category'},400)
     try:rating=int(d.get('rating'))
     except Exception:rating=0
     if not 1<=rating<=5:return self.reply({'error':'Choose a rating'},400)
    else:
     if not all(clean(d.get(k)) for k in ['parent','name','state']):return self.reply({'error':'Parent, company, and state are required. Use Unknown when ownership is unclear.'},400)
     rating=None
    c.execute('INSERT INTO submissions(kind,provider_id,parent,name,state,category,rating,body,source) VALUES(?,?,?,?,?,?,?,?,?)',(kind,d.get('provider_id') if kind=='review' else None,clean(d.get('parent'),150),clean(d.get('name'),150),clean(d.get('state'),80),clean(d.get('category'),100),rating,body,source))
   return self.reply({'ok':True},201)
  self.reply({'error':'Not found'},404)
if __name__=='__main__':
 init();port=int(os.environ.get('PORT',8080));print(f'ForProfitEMS running at http://localhost:{port}',flush=True);ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),port),Handler).serve_forever()
