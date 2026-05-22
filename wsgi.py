"""WSGI entrypoint for the Flask application.

Use this module with a production WSGI server such as Waitress on Windows
or Gunicorn on Linux.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)