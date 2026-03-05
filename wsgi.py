import logging
from logging.handlers import RotatingFileHandler
from flask import request
from waitress import serve
from app import create_app 
from werkzeug.middleware.proxy_fix import ProxyFix

app = create_app()

# Apply ProxyFix middleware
# x_for=1 trusts the real client IP
# x_proto=1 trusts the original protocol (http or https)
# x_host=1 trusts the original domain name
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 1. Configure the log file settings
# 'app_log.txt' is the filename
# maxBytes=10000 ensures the file doesn't grow forever
# backupCount=3 keeps the last 3 log files
handler = RotatingFileHandler('app_log.txt', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)

# 2. Set the format (Timestamp - Level - Message)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 3. Add the handler to Flask's logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

@app.before_request
def log_request_info():
    app.logger.info("Requested: %s %s from %s", 
                    request.method, 
                    request.url, 
                    request.remote_addr)

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:5001")

    serve(app, host='0.0.0.0', port=5001)


