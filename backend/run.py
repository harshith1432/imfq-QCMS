import os
import json

def app(environ, start_response):
    env_keys = dict(os.environ)
    for k in list(env_keys.keys()):
        if any(sec in k.upper() for sec in ['SECRET', 'KEY', 'PASS', 'URL', 'TOKEN', 'CONN']):
            env_keys[k] = '***MASKED***'
    body = json.dumps(env_keys, indent=2).encode('utf-8')
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
    return [body]
