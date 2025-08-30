from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(err):  # type: ignore[override]
        return jsonify({"errors": [{"status": 400, "title": "Bad Request", "detail": str(err)}]}), 400

    @app.errorhandler(404)
    def not_found(err):  # type: ignore[override]
        return jsonify({"errors": [{"status": 404, "title": "Not Found", "detail": str(err)}]}), 404

    @app.errorhandler(500)
    def server_error(err):  # type: ignore[override]
        app.logger.exception("Unhandled server error")
        return jsonify({"errors": [{"status": 500, "title": "Internal Server Error"}]}), 500

