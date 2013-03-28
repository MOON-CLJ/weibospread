from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from weibospread import create_app

if __name__ == '__main__':
    app = create_app()
    http_server = HTTPServer(WSGIContainer(app))
    http_server.bind(8080)
    http_server.start(0)
    IOLoop.instance().start()
