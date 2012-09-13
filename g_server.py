from gevent.wsgi import WSGIServer
from simple import app

http_server = WSGIServer(('', 8080), app)
http_server.serve_forever()
