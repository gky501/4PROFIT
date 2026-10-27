import unittest, tempfile, threading, json, urllib.request, urllib.error, os, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import server
class Workflow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();server.DB=cls.tmp.name+'/test.db';server.PASSWORD='test-password';server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.url='http://127.0.0.1:'+str(cls.http.server_port);threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.cookie=''
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
 def call(self,path,body=None):
  req=urllib.request.Request(self.url+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','Cookie':self.cookie})
  with urllib.request.urlopen(req) as r:
   if r.headers.get('Set-Cookie'):self.cookie=r.headers['Set-Cookie'].split(';')[0]
   return json.load(r)
 def test_workflow(self):
  with self.assertRaises(urllib.error.HTTPError) as cm:self.call('admin')
  self.assertEqual(cm.exception.code,401)
  self.call('submit',{'kind':'provider','name':'Test EMS','parent':'Test Group','state':'Iowa','body':'A provider report with sufficient supporting detail.'})
  self.assertEqual(len(self.call('data')['providers']),3)
  self.call('login',{'password':'test-password'})
  row=self.call('admin')[0];self.call('moderate',{'id':row['id'],'status':'approved'});self.call('moderate',{'id':row['id'],'status':'approved'})
  self.assertEqual(len(self.call('data')['providers']),4)
  p=self.call('data')['providers'][-1]
  self.call('submit',{'kind':'review','provider_id':p['id'],'category':'Billing','rating':2,'body':'The bill did not explain the charge clearly.'})
  self.assertEqual(self.call('data')['reviews'],[])
  review=self.call('admin')[0];self.call('moderate',{'id':review['id'],'status':'approved'})
  self.assertEqual(len(self.call('data')['reviews']),1)
  self.call('moderate',{'id':review['id'],'status':'pending'});self.assertEqual(self.call('data')['reviews'],[])
  self.call('logout',{})
  with self.assertRaises(urllib.error.HTTPError):self.call('admin')
 def test_validation(self):
  with self.assertRaises(urllib.error.HTTPError):self.call('submit',{'kind':'review','body':'short'})
  with self.assertRaises(urllib.error.HTTPError):self.call('submit',{'kind':'provider','name':'x','parent':'x','state':'x','body':'Enough characters for a valid report','source':'javascript:alert(1)'})
if __name__=='__main__':unittest.main()
