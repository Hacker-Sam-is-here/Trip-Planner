"""Local HTTP server proxying requests to Lambda handler for local testing."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from backend.lambda_function import handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local_api")


class LambdaHttpHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        event = {
            "httpMethod": "POST",
            "path": self.path,
            "body": body,
            "headers": {k: v for k, v in self.headers.items()},
        }
        res = handler(event, None)
        status_code = res.get("statusCode", 200)
        self.send_response(status_code)
        for h_key, h_val in res.get("headers", {}).items():
            self.send_header(h_key, h_val)
        self.end_headers()
        self.wfile.write(res.get("body", "{}").encode("utf-8"))

    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


def run_local_server(port: int = 5001) -> None:
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, LambdaHttpHandler)
    logger.info("Local API server running on http://127.0.0.1:%d", port)
    httpd.serve_forever()


if __name__ == "__main__":
    run_local_server()
