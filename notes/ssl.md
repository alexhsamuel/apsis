### Server

To generate a passwordless, self-signed certificate:

```
openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=hostname" \
    -keyout hostname.key -out hostname.cert
```

**Note**: there's no way to set the SubjectAltName directly on the command line
without generating an ssl.conf file, until [OpenSSL
1.1.1](https://github.com/openssl/openssl/commit/bfa470a4f64313651a35571883e235d3335054eb)
is available.


### Client

To use with sanic:

```py
import ssl

context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain("hostname.cert", keyfile="hostname.key")
server = app.create_server(..., ssl=context)
```

From curl (hostname in cert must match hostname in URL):
```
curl https://hostname:port/path --cacert hostname.cert
```

or to disable server auth:
```
curl https://hostname:port/path -k
```

From Python,
```py
>>> import urllib3
>>> urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
>>> requests.get("https://0.0.0.0:12345/test", verify=False)
```


# Agent

Currently, the agent uses the same SSL cert/key for each instance, on any host.
Generated like this:
```
openssl req -new -newkey rsa:4096 -days 10000 -nodes -x509 -subj "/C=XX/ST=XX/L=XX/O=XX/CN=apsis-agent" -keyout agent.key -out agent.cert
```

Obviously, since the cert doesn't specify the real host name, server
authentication cannot be used.

One alternate design to improve this would be to use ssh always for interactions
with the agent initiated by the client, and to use a server running on the
_client_ (essentially, a webhook) for notifications initiated by the agent.


