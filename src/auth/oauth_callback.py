import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        logger.debug(f"OAuth callback: {format % args}")
    
    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            if parsed_url.path != '/callback':
                self.send_error(404, "Not Found")
                return
            
            code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('error', [None])[0]
            
            if error:
                logger.error(f"OAuth authorization error: {error}")
                self.server.authorization_code = None
                self.server.error = error
                self._send_error_page(error)
                return
            
            if state != self.server.expected_state:
                logger.error("OAuth state mismatch - possible CSRF attack")
                self.server.authorization_code = None
                self.server.error = "state_mismatch"
                self._send_error_page("Invalid state parameter")
                return
            
            if code:
                logger.info("Authorization code received successfully")
                self.server.authorization_code = code
                self.server.error = None
                self._send_success_page()
                
                threading.Thread(target=self._shutdown_server, daemon=True).start()
            else:
                logger.error("No authorization code in callback")
                self.server.authorization_code = None
                self.server.error = "no_code"
                self._send_error_page("No authorization code received")
        
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            self.server.authorization_code = None
            self.server.error = str(e)
            self._send_error_page(f"Server error: {str(e)}")
    
    def _shutdown_server(self):
        time.sleep(0.5)
        try:
            self.server.shutdown()
        except:
            pass
    
    def _send_success_page(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authentication Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 3rem;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }
                .success-icon {
                    font-size: 4rem;
                    color: #4CAF50;
                    margin-bottom: 1rem;
                    animation: checkmark 0.5s ease-in-out;
                }
                @keyframes checkmark {
                    0% { transform: scale(0); }
                    50% { transform: scale(1.2); }
                    100% { transform: scale(1); }
                }
                h1 {
                    color: #333;
                    margin-bottom: 1rem;
                }
                p {
                    color: #666;
                    font-size: 1.1rem;
                    line-height: 1.6;
                }
                .close-message {
                    margin-top: 2rem;
                    padding: 1.5rem;
                    background: #e8f5e9;
                    border-radius: 8px;
                    border-left: 4px solid #4CAF50;
                    color: #2e7d32;
                    font-weight: 500;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>Authentication Successful!</h1>
                <p>You have successfully signed in with Google.</p>
                <p>Your Mailbox app is now connected to your Gmail and Calendar.</p>
                <div class="close-message">
                    You can close this window and return to the terminal.
                </div>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _send_error_page(self, error_message: str):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authentication Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    text-align: center;
                    max-width: 500px;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #f44336;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #666;
                    font-size: 1.1rem;
                    line-height: 1.6;
                }}
                .error-details {{
                    margin-top: 1.5rem;
                    padding: 1rem;
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    border-radius: 5px;
                    text-align: left;
                    color: #856404;
                }}
                .close-message {{
                    margin-top: 2rem;
                    padding: 1rem;
                    background: #f5f5f5;
                    border-radius: 5px;
                    color: #555;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✗</div>
                <h1>Authentication Failed</h1>
                <p>There was a problem signing in with Google.</p>
                <div class="error-details">
                    <strong>Error:</strong> {error_message}
                </div>
                <div class="close-message">
                    Please close this window and try again from the terminal.
                </div>
            </div>
        </body>
        </html>
        """
        
        self.send_response(400)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))


class OAuthCallbackServer:
    
    def __init__(self, port: int = 8080, state: str = ""):
        self.port = port
        self.expected_state = state
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.authorization_code: Optional[str] = None
        self.error: Optional[str] = None
        self._running = False
    
    def start(self):
        try:
            self.server = HTTPServer(('localhost', self.port), OAuthCallbackHandler)
            
            self.server.timeout = 1.0
            
            self.server.expected_state = self.expected_state
            self.server.authorization_code = None
            self.server.error = None
            
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            self._running = True
            logger.info(f"OAuth callback server started on http://localhost:{self.port}")
        
        except Exception as e:
            logger.error(f"Failed to start OAuth callback server: {e}")
            raise
    
    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"OAuth callback server error: {e}")
    
    def wait_for_code(self, timeout: int = 300) -> Optional[str]:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.server and self.server.authorization_code:
                logger.info("Authorization code captured successfully")
                return self.server.authorization_code
            
            if self.server and self.server.error:
                logger.error(f"OAuth callback error: {self.server.error}")
                return None
            
            if not self._running:
                break
            
            time.sleep(0.5)
        
        if not self.server or not self.server.authorization_code:
            logger.error("OAuth callback timeout - user did not authorize in time")
        
        return None
    
    def stop(self):
        self._running = False
        
        if self.server:
            try:
                self.server.server_close()
                logger.info("OAuth callback server stopped")
            except Exception as e:
                logger.error(f"Error stopping OAuth callback server: {e}")
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1)
        
        self.server = None
        self.server_thread = None
