"""Sport API R1 (usługa "sport"): identyfikatory API, stany FSM i budowanie żądań.

Źródło: unitree_sdk2 `include/unitree/robot/r1/loco/r1_loco_api.hpp` i `r1_loco_client.hpp`.
W ROS 2 to temat `/api/sport/request` (unitree_api/msg/Request), odpowiedź na `/api/sport/response`.
"""
import json
import time

REQUEST_TOPIC = '/api/sport/request'
RESPONSE_TOPIC = '/api/sport/response'

API_GET_FSM_ID = 7001
API_GET_FSM_MODE = 7002
API_SET_FSM_ID = 7101         # parameter {"data": fsm_id}
API_SET_VELOCITY = 7105       # parameter {"velocity": [vx, vy, wz], "duration": s}

FSM_ZERO_TORQUE = 0           # robot upada
FSM_DAMP = 1                  # tłumienie, robot upada
FSM_STAND = 4                 # stanie zablokowane (StandUp)
FSM_LIE_TO_STAND = 701
FSM_STAND_TO_LIE = 702
FSM_WALK = 811                # chód (Start) - tylko tu działa SetVelocity
FSM_ARM_BLOCKED = 816         # [SEC] arm_sdk w 811 -> 816, chód zablokowany (zgłoszenia społeczności)

FSM_NAMES = {
    FSM_ZERO_TORQUE: 'zero torque',
    FSM_DAMP: 'damping',
    FSM_STAND: 'stanie zablokowane',
    FSM_LIE_TO_STAND: 'wstawanie z leżenia',
    FSM_STAND_TO_LIE: 'kładzenie się',
    FSM_WALK: 'chód',
    FSM_ARM_BLOCKED: 'chód zablokowany przez arm_sdk',
}

# Kod 127 na SetVelocity: znany ze zgłoszeń społeczności (xr_teleoperate #319, unitree_sdk2_python #182).
# U części robotów w 811 robot i tak idzie, u autora #319 (ai_sport 1.0.2.154) nie ruszał z SDK.
# Unitree nie opisuje tego kodu. Logujemy, ale nie traktujemy jako twardy błąd.
CODE_127_REPORTED = 127

_last_id = 0


def next_request_id():
    """Rosnący identyfikator żądania (jak GetSystemUptimeInNanoseconds w unitree_ros2)."""
    global _last_id
    _last_id = max(time.monotonic_ns(), _last_id + 1)
    return _last_id


def velocity_parameter(vx, vy, wz, duration):
    """JSON dla SetVelocity 7105: {"velocity": [vx, vy, wz], "duration": duration}."""
    return json.dumps({'velocity': [round(float(vx), 4), round(float(vy), 4), round(float(wz), 4)],
                       'duration': round(float(duration), 3)})


def fsm_parameter(fsm_id):
    """JSON dla SetFsmId 7101: {"data": fsm_id}."""
    return json.dumps({'data': int(fsm_id)})


def make_request(api_id, parameter=''):
    """unitree_api/Request z nowym id (odpowiedź paruje się po header.identity.id)."""
    from unitree_api.msg import Request

    req = Request()
    req.header.identity.id = next_request_id()
    req.header.identity.api_id = int(api_id)
    req.parameter = parameter
    return req


def fsm_name(fsm_id):
    return FSM_NAMES.get(fsm_id, 'nieznany')
