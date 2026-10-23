import os

from dotenv import load_dotenv
from flask import Flask, make_response

from blueprints.admin import admin_bp
from blueprints.auth import auth_bp
from blueprints.parking_lots import parking_lots_bp
from blueprints.reservations import reservations_bp
from blueprints.sessions import sessions_bp

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    for blueprint in (auth_bp, parking_lots_bp, reservations_bp,
                      sessions_bp, admin_bp):
        app.register_blueprint(blueprint)

    # welcome route
    @app.route("/", methods=["GET"])
    def index():
        return make_response("<h1>Smart Parking Management System API</h1>", 200)


    #JSON error handlers
    @app.errorhandler(404)
    def not_found(e):
        return make_response({"error": "Resource not found"}, 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return make_response({"error": "Method not allowed"}, 405)

    @app.errorhandler(500)
    def server_error(e):
        return make_response({"error": "Internal server error"}, 500)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)