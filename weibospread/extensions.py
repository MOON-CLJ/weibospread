# -*- coding: utf-8 -*-

from flask.ext.pymongo import PyMongo
import redis

__all__ = ['mongo', 'r']

mongo = PyMongo()

r = redis.Redis('localhost', 6379)
