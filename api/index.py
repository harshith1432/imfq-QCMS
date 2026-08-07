import json

def handler(environ, start_response):
    body = b'{"status":"ok","message":"Vercel Python in api/index.py Working!"}'
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
    return [body]

app = handler
