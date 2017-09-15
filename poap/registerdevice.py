import os
import requests
import httplib
import base64
import string

nso_ip = "127.0.0.1"
nso_port = 8080
username = "admin"
password = "admin"
request_path = "/api/running/devices"
url = "http://" + nso_ip + ":" + str(nso_port) + request_path
#headers = {"Accept": "application/vnd.yang.data+xml"}
payload = """
<device>
  <name>test2</name>
  <address>127.0.0.1</address>
  <authgroup>default</authgroup>
  <device-type>
    <cli>
      <ned-id>cisco-nx</ned-id>
      <protocol>ssh</protocol>
    </cli>
  </device-type>
  <location>
    <name>DATACENTER</name>
  </location>
</device>
"""

os.environ['NO_PROXY'] = nso_ip
#r = requests.post(url, auth=(username, password), headers=headers, data=payload)
#print r.status_code
#print r.text

conn = httplib.HTTPConnection(host=nso_ip, port=nso_port)
auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
headers = {"Accept": "application/vnd.yang.data+xml", "Authorization": "Basic %s" % auth}
conn.request(method="POST", url=request_path, body=payload, headers=headers)
response = conn.getresponse()
print response.status, response.reason
print response.read()
