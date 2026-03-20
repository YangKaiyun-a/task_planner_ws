# -*- coding:utf-8 -*-

import base64
import hashlib
import hmac
import json
import ssl
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from threading import Thread, Event, Lock

import websocket


STATUS_FIRST_FRAME = 0
STATUS_CONTINUE_FRAME = 1
STATUS_LAST_FRAME = 2


class WsParam:
    def __init__(self, app_id: str, api_key: str, api_secret: str, audio_file: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.audio_file = audio_file

        self.common_args = {"app_id": self.app_id}
        self.business_args = {
            "domain": "iat",
            "language": "zh_cn",
            "accent": "mandarin",
            "vinfo": 1,
            "vad_eos": 10000
        }

    def create_url(self) -> str:
        url = "wss://ws-api.xfyun.cn/v2/iat"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: ws-api.xfyun.cn\n"
        signature_origin += f"date: {date}\n"
        signature_origin += "GET /v2/iat HTTP/1.1"

        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        signature_sha = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_sha}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        params = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }

        return url + "?" + urlencode(params)


class XFYunASRClient:
    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret

        self._result_text = ""
        self._error = None
        self._finished = Event()
        self._lock = Lock()

    def transcribe_pcm(self, audio_file: str, timeout: float = 30.0) -> str | None:
        """
        识别 16k / mono / s16le 的 PCM 裸流文件
        """
        self._result_text = ""
        self._error = None
        self._finished.clear()

        ws_param = WsParam(
            app_id=self.app_id,
            api_key=self.api_key,
            api_secret=self.api_secret,
            audio_file=audio_file
        )

        def on_message(ws, message):
            try:
                msg = json.loads(message)
                code = msg.get("code", 0)

                if code != 0:
                    err_msg = msg.get("message", "")
                    self._error = f"讯飞识别失败: {err_msg} (code={code})"
                    self._finished.set()
                    return

                data = msg.get("data", {}).get("result", {}).get("ws", [])
                segment_text = ""

                for item in data:
                    for word in item.get("cw", []):
                        segment_text += word.get("w", "")

                with self._lock:
                    self._result_text += segment_text

                # 讯飞返回 status=2 时表示最后结果
                status = msg.get("data", {}).get("status", None)
                if status == 2:
                    self._finished.set()

            except Exception as e:
                self._error = f"解析讯飞返回消息异常: {e}"
                self._finished.set()

        def on_error(ws, error):
            self._error = f"WebSocket error: {error}"
            self._finished.set()

        def on_close(ws, close_status_code, close_msg):
            self._finished.set()

        def on_open(ws):
            def run():
                frame_size = 8000
                interval = 0.04
                status = STATUS_FIRST_FRAME

                try:
                    with open(ws_param.audio_file, "rb") as fp:
                        while True:
                            buf = fp.read(frame_size)
                            if not buf:
                                status = STATUS_LAST_FRAME

                            if status == STATUS_FIRST_FRAME:
                                data = {
                                    "common": ws_param.common_args,
                                    "business": ws_param.business_args,
                                    "data": {
                                        "status": 0,
                                        "format": "audio/L16;rate=16000",
                                        "audio": base64.b64encode(buf).decode("utf-8"),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(data))
                                status = STATUS_CONTINUE_FRAME

                            elif status == STATUS_CONTINUE_FRAME:
                                data = {
                                    "data": {
                                        "status": 1,
                                        "format": "audio/L16;rate=16000",
                                        "audio": base64.b64encode(buf).decode("utf-8"),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(data))

                            elif status == STATUS_LAST_FRAME:
                                data = {
                                    "data": {
                                        "status": 2,
                                        "format": "audio/L16;rate=16000",
                                        "audio": base64.b64encode(buf).decode("utf-8"),
                                        "encoding": "raw"
                                    }
                                }
                                ws.send(json.dumps(data))
                                time.sleep(1)
                                break

                            time.sleep(interval)

                except Exception as e:
                    self._error = f"发送音频数据失败: {e}"
                    self._finished.set()
                finally:
                    try:
                        ws.close()
                    except Exception:
                        pass

            Thread(target=run, daemon=True).start()

        ws_url = ws_param.create_url()
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.on_open = on_open

        def run_ws():
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        ws_thread = Thread(target=run_ws, daemon=True)
        ws_thread.start()

        finished = self._finished.wait(timeout=timeout)

        if not finished:
            self._error = "讯飞识别超时"
            try:
                ws.close()
            except Exception:
                pass
            return None

        if self._error:
            return None

        return self._result_text.strip()

    def get_last_error(self) -> str | None:
        return self._error