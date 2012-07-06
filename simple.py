# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request
from weibo import APIClient


app = Flask(__name__)
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:5000/callback'


@app.route('/')
def index():
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    url = client.get_authorize_url()
    return render_template('simple.html', url=url)


@app.route('/callback')
def callback():
    code = request.args.get('code', '')
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    r = client.request_access_token(code)
    access_token = r.access_token
    expires_in = r.expires_in
    # TODO: 在此可保存access token
    client.set_access_token(access_token, expires_in)
    return access_token


if __name__ == '__main__':
    app.debug = True
    app.run()
