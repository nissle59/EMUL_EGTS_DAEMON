import base64
import json
import pickle
from EGTStrack import EGTStrack
from pydantic import BaseModel
import logging
LOGGER = logging.getLogger(__name__)


class Point(BaseModel):
    coordinatesId: int | float | None = None
    tid: int | None = None
    latitude: float
    longitude: float
    speed: int | None = 0
    angle: int = 0
    sleeper: bool = False
    sleep_time: int = 0
    timestamp: int | None = None
    regnumber: str | None = None

    def to_json(self):
        LOGGER = logging.getLogger(__name__ + ".Point--to_json")
        return json.dumps(self.to_dict())

    def to_dict(self):
        LOGGER = logging.getLogger(__name__ + ".Point--to_dict")
        d = {
            "coordinatesId": self.coordinatesId,
            "tid": self.tid,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "speed": self.speed,
            "angle": self.angle,
            "sleeper": self.sleeper,
            "sleep_time": self.sleep_time,
            "timestamp": self.timestamp
        }
        try:
            d['regnumber'] = self.regnumber
        except:
            d['regnumber'] = None
        return d

    def to_b64(self):
        LOGGER = logging.getLogger(__name__ + ".Point--to_b64")
        b_code = pickle.dumps(self)
        base64_bytes = base64.b64encode(b_code)
        base64_string = base64_bytes.decode('utf-8')
        return base64_string

    @classmethod
    def from_b64(cls, b64_string):
        LOGGER = logging.getLogger(__name__ + ".Point--from_b64")
        if isinstance(b64_string, str):
            base64_bytes = b64_string.encode('utf-8')
        else:
            base64_bytes = b64_string
        b_code = base64.b64decode(base64_bytes)
        obj = pickle.loads(b_code)
        return obj

    def to_egts_packet(self, egts_instance: EGTStrack, imei, imsi, msisdn, offset=None):
        LOGGER = logging.getLogger(__name__ + ".Point--to_egts_packet")
        #egts_instance = EGTStrack(deviceimei=imei, imsi=imsi, msisdn=msisdn)
        egts_instance.add_service(16,
                                  long=self.longitude,
                                  lat=self.latitude,
                                  speed=self.speed,
                                  angle=self.angle,
                                  offset=offset,
                                  ts=self.timestamp
                                  )
        message_b = egts_instance.new_message()
        return message_b

    @staticmethod
    def from_json_b(json_bstr):
        LOGGER = logging.getLogger(__name__ + ".Point--from_json_b")
        s = json.loads(json_bstr.decode('utf-8'))
        return Point(**s)

    def __repr__(self):
        LOGGER = logging.getLogger(__name__ + ".Point--repr")
        return f"Point(speed {self.speed}, angle {self.angle}, lat[{self.latitude}] long[{self.longitude}])"


class Segment(BaseModel):
    segmentId: int
    taskId: int
    jamsTime: float = 0.0
    length: float = 0.0
    sleep: int | None = None
    coordinates: list[Point]


class Route(BaseModel):
    ok: bool
    results: list[Segment] | None = None
    error: str | None = None

    def __repr__(self):
        LOGGER = logging.getLogger(__name__ + ".Route--repr")
        return json.dumps({ 'ok': self.ok, 'results': self.results, 'error': self.error })
