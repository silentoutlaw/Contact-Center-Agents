"""Server-side WebSocket relay to OpenAI Realtime.

The browser connects only to this server (same origin, no API key). The server
opens the upstream WebSocket to OpenAI with the standing key and pipes text
frames both ways. This works when the browser's network cannot reach OpenAI but
the server can, and keeps the API key entirely server-side.
"""
import json
import threading

from flask import session as flask_session
from flask_sock import Sock
import websocket  # websocket-client (synchronous)

from . import openai_client as oc

sock = Sock()


def _err(ws, message):
    try:
        ws.send(json.dumps({"type": "error", "error": {"message": message}}))
    except Exception:
        pass


@sock.route("/ws/realtime")
def realtime_relay(ws):
    # Auth: the login gate also runs, but guard here too for WS clarity.
    if not flask_session.get("user"):
        _err(ws, "not authenticated")
        return

    key = oc.load_api_key()
    if not key:
        _err(ws, "OpenAI API key not configured")
        return

    url = f"wss://api.openai.com/v1/realtime?model={oc.REALTIME_MODEL}"
    try:
        upstream = websocket.create_connection(
            url,
            header=[f"Authorization: Bearer {key}"],
            enable_multithread=True,
            timeout=30,
        )
        upstream.settimeout(None)  # block on recv until data or close
    except Exception as e:
        _err(ws, f"upstream connect failed: {e}")
        return

    stop = threading.Event()

    def openai_to_browser():
        try:
            while not stop.is_set():
                data = upstream.recv()  # text frame -> str
                if data is None or data == "":
                    break
                ws.send(data)
        except Exception:
            pass
        finally:
            stop.set()

    pump = threading.Thread(target=openai_to_browser, daemon=True)
    pump.start()

    # Browser -> OpenAI in this handler thread.
    try:
        while not stop.is_set():
            msg = ws.receive(timeout=1)
            if msg is None:  # idle tick; check stop and continue
                continue
            upstream.send(msg)
    except Exception:
        pass
    finally:
        stop.set()
        try:
            upstream.close()
        except Exception:
            pass
        pump.join(timeout=2)
