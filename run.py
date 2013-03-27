# -*- coding: utf-8 -*-

from weibospread import create_app, HOST, PORT

app = create_app(debug=True)
app.debug = True
app.run(host=HOST, port=PORT)
