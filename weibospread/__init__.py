# -*- coding: utf-8 -*-

# run this script for development use

from flask import Flask
from weibospread.extensions import mongo
import views

APP_NAME = 'simple'
HOST = '0.0.0.0'
PORT = 8080

MODULES = (
    (views.simple, ''),
    (views.search, '/search'),
    (views.suggest, '/suggest'),
    (views.graph, '/graph'),
    (views.show_graph, '/show_graph'),
)


def configure_modules(app, modules):
    for module, url_prefix in modules:
        app.register_blueprint(module, url_prefix=url_prefix)


def create_app(debug=False):
    app = Flask(APP_NAME)
    configure_modules(app, MODULES)

    app.config['MONGO_USERNAME'] = 'simple'
    app.config['MONGO_PASSWORD'] = 'simple'
    mongo.init_app(app)
    app.secret_key = 'youknowwhat,iamsocute'

    return app
