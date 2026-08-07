def app(environ, start_response):
    body = b'{"status":"ok","message":"Hello from Vercel Python Serverless"}'
    start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
    return [body]
