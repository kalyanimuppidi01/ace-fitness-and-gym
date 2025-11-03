from flask import Flask

def create_app():
    app = Flask(__name__)
    # register routes in blueprints or directly
    from . import routes
    app.register_blueprint(routes.bp)
    return app
