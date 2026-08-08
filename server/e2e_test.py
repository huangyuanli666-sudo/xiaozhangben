import json, urllib.request, urllib.error

BASE = 'http://127.0.0.1:8765'
def req(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body else None
    hdrs = {'Content-Type': 'application/json'}
    if token: hdrs['Authorization'] = 'Bearer ' + token
    r = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=5)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        raise Exception(err.get('detail','??'))

# 1) register
reg = req('POST','/api/register',{'username':'e2e_test','password':'test1234','nickname':'E2E'})
assert reg['user']['username'] == 'e2e_test'
t = reg['token']
print('1. register OK')

# 2) sync (simulate first login with local data)
sync = req('POST','/api/sync',{'items':[
  {'type':'expense','amount':8800,'category':'餐饮','note':'拉面','date':'2026-08-12','createdAt':1},
  {'type':'income','amount':300000,'category':'工资','note':'','date':'2026-08-10','createdAt':2},
]}, t)
assert sync['imported'] == 2
print(f'2. sync OK, imported={sync["imported"]}, total={len(sync["bills"])}')

# 3) add bill
b = req('POST','/api/bills',{'type':'expense','amount':1500,'category':'交通','note':'地铁','date':'2026-08-13'}, t)
assert b['amount'] == 1500
print(f'3. add OK, id={b["id"]}')

# 4) edit bill
b2 = req('PUT',f'/api/bills/{b["id"]}',{'amount':2000,'note':'打车'}, t)
assert b2['amount'] == 2000
print(f'4. edit OK, amount->{b2["amount"]}')

# 5) delete bill
req('DELETE',f'/api/bills/{b["id"]}',token=t)
bills = req('GET','/api/bills?month=2026-08',token=t)
assert len(bills) == 2
print(f'5. delete OK, remaining {len(bills)}')

# 6) admin dashboard
a = req('POST','/api/login',{'username':'admin','password':'admin123'})
at = a['token']
summ = req('GET','/api/admin/summary',token=at)
assert summ['totalUsers'] >= 2
users = [u['username'] for u in req('GET','/api/admin/users',token=at)]
assert 'e2e_test' in users and 'admin' in users
print(f'6. admin OK, users={users}, summary={summ}')

print('=== ALL E2E CHECKS PASSED ===')
