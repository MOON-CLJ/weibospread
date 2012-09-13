from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from simple import app

if __name__ == "__main__":
    http_server = HTTPServer(WSGIContainer(app))
    http_server.bind(8080)
    http_server.start(0)
    IOLoop.instance().start()
