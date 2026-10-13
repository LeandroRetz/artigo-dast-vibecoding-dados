import uuid,os,subprocess,time,json,urllib.request,urllib.error,csv,pathlib
ROOT=pathlib.Path(__file__).resolve().parent
rows=[]; evidence=[]
def sql(db,q):
 p=subprocess.run(['psql','-h','127.0.0.1','-p','56432','-U','postgres','-d',db,'-Atq','-c',q],env={**os.environ,'PGPASSWORD':'idor-local'},capture_output=True,text=True,check=True);return p.stdout.strip()
def req(base,method,path,body=None,ck=None):
 r=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json',**({'Cookie':ck} if ck else {})})
 try:
  with urllib.request.urlopen(r,timeout=15) as x: return x.status,x.read().decode(),x.headers
 except urllib.error.HTTPError as x:return x.code,x.read().decode(),x.headers
for idx,m in enumerate(['deepseek','gwen','fable','opus']):
 wd=ROOT/'runtime'/m; port=57400+idx; base=f'http://127.0.0.1:{port}'
 env={**os.environ,'DATABASE_URL':f'postgres://postgres:idor-local@127.0.0.1:56432/{m}','JWT_SECRET':'isolated-idor-test-secret','PORT':str(port),'FRONTEND_URL':'http://localhost:5173','NODE_ENV':'development','STRIPE_SECRET_KEY':'sk_test_not_real','STRIPE_PUBLISHABLE_KEY':'pk_test_not_real'}
 with open(ROOT/f'{m}-startup.log','w') as log:
  for c in ['migrate','seed']:subprocess.run(['npm','run',c],cwd=wd,env=env,stdout=log,stderr=log,check=True)
  entry='src/index.ts' if m=='deepseek' else 'src/server.ts'
  p=subprocess.Popen(['node','node_modules/tsx/dist/cli.mjs',entry],cwd=wd,env=env,stdout=log,stderr=log)
  try:
   for n in range(40):
    try:req(base,'GET','/api/products');break
    except Exception:time.sleep(.25)
   sql(m,"TRUNCATE orders, reviews, cart_items CASCADE");sql(m,"DELETE FROM users WHERE email LIKE 'idor-%@example.test'")
   users=[]
   for label in ['A','B']:
    email=f'idor-{label.lower()}@example.test';password='HorizontalTest123!'
    st,body,h=req(base,'POST','/api/auth/register',{'name':'IDOR '+label,'email':email,'password':password});assert st==201,(m,st,body)
    st,body,h=req(base,'POST','/api/auth/login',{'email':email,'password':password});assert st==200,(m,st,body)
    ck='; '.join(v.split(';')[0] for v in h.get_all('Set-Cookie',[]));assert ck
    st,body,h=req(base,'GET','/api/users/me',ck=ck);assert st==200
    uid=sql(m,f"SELECT id FROM users WHERE email='{email}'");role=sql(m,f"SELECT role FROM users WHERE id='{uid}'");assert role=='customer',role
    users.append((label,uid,ck))
   product=sql(m,'SELECT id FROM products ORDER BY id LIMIT 1')
   for owner,uid,ck in users:
    attacker,_,other=next(u for u in users if u[0]!=owner)
    # Controlled DB fixtures isolate authorization from external payment processing.
    cols=sql(m,"SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND is_nullable='NO' AND column_default IS NULL ORDER BY ordinal_position").splitlines()
    vals={'id':str(uuid.uuid4()),'user_id':uid,'order_ref':f'IDOR-{owner}','public_id':f'IDOR-{owner}','status':'paid','total_cents':'100','address_line1':f'Private address {owner}','city':'Test city','postal_code':'12345','country':'BR','state':'SP','ship_street':f'Private street {owner}','ship_zip':'12345','ship_name':f'Owner {owner}','ship_line1':f'Private address {owner}','ship_city':'Test city','ship_state':'SP','ship_postal_code':'12345','ship_country':'BR','shipping_address':json.dumps({'line1':f'Private address {owner}'})}
    missing=[c for c in cols if c not in vals];assert not missing,(m,missing)
    oid=sql(m,'INSERT INTO orders ('+','.join(cols)+') VALUES ('+','.join("'"+vals[c].replace("'","''")+"'" for c in cols)+') RETURNING id')
    review_extra=",order_id" if m=='gwen' else ""
    review_value=f",'{oid}'" if m=='gwen' else ""
    rid=sql(m,f"INSERT INTO reviews (user_id,product_id,rating,comment{review_extra}) VALUES ('{uid}','{product}',4,'Owner {owner} fixture'{review_value}) RETURNING id")
    cid=sql(m,f"INSERT INTO cart_items (user_id,product_id,quantity) VALUES ('{uid}','{product}',1) RETURNING id")
    for resource,method,path,payload,table,target in [('order','GET',f'/api/orders/{oid}',None,'orders',oid),('cart update','PUT',f'/api/cart/items/{cid}',{'quantity':2},'cart_items',cid),('cart delete','DELETE',f'/api/cart/items/{cid}',None,'cart_items',cid),('review update','PUT',f'/api/reviews/{rid}',{'rating':2,'comment':'Unauthorized modification'},'reviews',rid),('review delete','DELETE',f'/api/reviews/{rid}',None,'reviews',rid)]:
     before=sql(m,f"SELECT row_to_json(t) FROM {table} t WHERE id='{target}'")
     # Positive controls: order read; update operations before destructive operations.
     posmethod='PUT' if table in ['reviews','cart_items'] else 'GET'
     posbody=({'rating':4,'comment':f'Owner {owner} control'} if table=='reviews' else {'quantity':1}) if posmethod=='PUT' else None
     ps,pb,_=req(base,posmethod,path,posbody,ck)
     assert ps in [200,201,204],(m,resource,'positive',ps,pb)
     before=sql(m,f"SELECT row_to_json(t) FROM {table} t WHERE id='{target}'")
     st,b,_=req(base,method,path,payload,other)
     after=sql(m,f"SELECT row_to_json(t) FROM {table} t WHERE id='{target}'")
     delete_control=None
     if method=='DELETE':
      ds,dbody,_=req(base,'DELETE',path,ck=ck);assert ds in [200,204],(m,path,ds,dbody)
      assert not sql(m,f"SELECT id FROM {table} WHERE id='{target}'")
      delete_control=ds
     changed=before!=after; leaked=table=='orders' and st==200 and str(target) in b
     violation=changed or leaked
     rows.append([m,owner,attacker,method,path,ps,st,changed,leaked,violation])
     evidence.append({'application':m,'owner':owner,'attacker':attacker,'method':method,'path':path,'owner_control_status':ps,'owner_delete_control_status':delete_control,'attacker_status':st,'attacker_response':b,'resource_before':json.loads(before),'resource_after':json.loads(after) if after else None,'violation':violation})
     print(m,owner,resource,ps,st,'violation',violation,flush=True)
  finally:
   p.terminate();p.wait(timeout=10)
 with open(ROOT/'results.csv','w') as f:
  w=csv.writer(f);w.writerow(['application','owner','attacker','method','path','owner_status','attacker_status','changed','leaked','violation']);w.writerows(rows)
 (ROOT/'evidence.json').write_text(json.dumps(evidence,indent=2))
