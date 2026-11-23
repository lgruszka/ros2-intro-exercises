#!/usr/bin/env python3
"""sport_cli - jednorazowe komendy sport API R1 z terminala (wysyła żądanie, czeka na odpowiedź).

Użycie:
    ros2 run r1_basics sport_cli get_fsm   # 7001 GetFsmId
    ros2 run r1_basics sport_cli stand     # 7101 SetFsmId 4   (stanie zablokowane)
    ros2 run r1_basics sport_cli start     # 7101 SetFsmId 811 (chód) - tylko z FSM 4 i z robotem w ramie
    ros2 run r1_basics sport_cli stop      # 7105 SetVelocity [0, 0, 0] (StopMove)
"""
import argparse
import json
import sys
import time

from r1_basics.sport_api import (API_GET_FSM_ID, API_SET_FSM_ID, API_SET_VELOCITY, fsm_name, fsm_parameter,
                                 FSM_STAND, FSM_WALK, make_request, REQUEST_TOPIC, RESPONSE_TOPIC,
                                 velocity_parameter)
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from unitree_api.msg import Request, Response

COMMANDS = {
    'get_fsm': (API_GET_FSM_ID, '', 'odczyt stanu FSM (7001 GetFsmId)'),
    'stand': (API_SET_FSM_ID, fsm_parameter(FSM_STAND), 'stanie zablokowane (7101, FSM 4)'),
    'start': (API_SET_FSM_ID, fsm_parameter(FSM_WALK), 'tryb chodu (7101, FSM 811)'),
    'stop': (API_SET_VELOCITY, velocity_parameter(0, 0, 0, 1.0), 'StopMove (7105, prędkość 0)'),
}

EPILOG = """\
Celowo BRAK komend Damp (FSM 1) i ZeroTorque (FSM 0): nogi tracą sztywność i robot się przewraca.
Do zatrzymania awaryjnego używaj pilota (L2+B przytrzymane > 5 s = damping, robot upadnie,
więc tylko na stojaku/w ramie) albo czerwonego przycisku E-Stop.
`start` i `stand` zmieniają stan robota - pilot w ręku, wolna strefa wokół robota.
`start` (FSM 811): przykład Unitree w Pythonie wymaga robota zawieszonego w ramie i w stanie
zablokowanym (FSM 4). `stand` = FSM 4 BEZ kontroli równowagi (dokumentacja Unitree): robot
stojący swobodnie może upaść.
"""


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='sport_cli', description='Jednorazowe komendy sport API Unitree R1 (usługa "sport").',
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=sorted(COMMANDS),
                        help='; '.join(f'{k}: {v[2]}' for k, v in sorted(COMMANDS.items())))
    parser.add_argument('--timeout', type=float, default=3.0, help='ile sekund czekać (domyślnie 3)')
    return parser.parse_args(argv)


def main(args=None):
    opts = parse_args(remove_ros_args(sys.argv)[1:])
    api_id, parameter, label = COMMANDS[opts.command]

    rclpy.init(args=args)
    node = Node('sport_cli')
    pub = node.create_publisher(Request, REQUEST_TOPIC, 10)
    replies = []
    node.create_subscription(Response, RESPONSE_TOPIC, replies.append, qos_profile_sensor_data)
    log = node.get_logger()
    code = 1
    try:
        # Poczekaj na odkrycie robota (DDS): wiadomość wysłana przed dopasowaniem przepada.
        deadline = time.monotonic() + opts.timeout
        while pub.get_subscription_count() == 0 and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if pub.get_subscription_count() == 0:
            log.error(f'nikt nie subskrybuje {REQUEST_TOPIC} - robot (albo r1_mock) niewidoczny. '
                      'Sprawdź sieć, RMW_IMPLEMENTATION, CYCLONEDDS_URI i ROS_DOMAIN_ID.')
            return 2
        rclpy.spin_once(node, timeout_sec=0.3)    # chwila na dopasowanie subskrypcji odpowiedzi

        req = make_request(api_id, parameter)
        req_id = req.header.identity.id
        log.info(f'{opts.command}: {label}, parameter={parameter!r}')
        pub.publish(req)

        deadline = time.monotonic() + opts.timeout
        reply = None
        while reply is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            reply = next((r for r in replies if r.header.identity.id == req_id), None)
        if reply is None:
            log.error(f'brak odpowiedzi w {opts.timeout} s (robot mógł wykonać komendę mimo to - patrz na robota)')
            return 1

        status = reply.header.status.code
        if opts.command == 'get_fsm' and status == 0:
            fsm = json.loads(reply.data).get('data')
            log.info(f'FSM = {fsm} ({fsm_name(fsm)})')
        elif status == 0:
            log.info('OK (kod 0)')
        else:
            log.warning(f'kod odpowiedzi {status}, data={reply.data!r}'
                        + (' (127 na 7105 znany ze zgłoszeń społeczności - patrz, czy robot się rusza)'
                           if status == 127 and api_id == API_SET_VELOCITY else '')
                        + (' (1001 na 7101: w zgłoszeniach tak odpowiada robot już będący w tym stanie '
                           'albo zablokowany w FSM 816)' if status == 1001 and api_id == API_SET_FSM_ID else ''))
        code = 0 if status in (0, 127) else 1
        return code
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
