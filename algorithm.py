import random
from _thread import start_new_thread
from sys import argv
from time import sleep

import rpyc

PROCESS_NOT_WANT_RANGE_START = 5
PROCESS_NOT_WANT_RANGE_END = 5
PROCESS_HOLD_RANGE_START = 10
PROCESS_HOLD_RANGE_END = 10

STATE_HELD = 'HELD'
STATE_WANTED = 'WANTED'
STATE_DO_NOT_WANT = 'DO NOT WANT'

MESSAGE_REQUEST = 'REQUEST'
MESSAGE_OK = 'OK'

PROCESS_IDS = set()


def get_port_from_id(id):
    return 1234 + id


class Process:
    def __init__(self, id):
        self.id = id
        self.time = random.randint(1, 4)
        self.state = STATE_DO_NOT_WANT
        self.permission_givers = set()

    def start(self):
        start_new_thread(self.manage_state, ())
        start_new_thread(self.listen, ())

    def manage_state(self):
        while True:

            if self.state == STATE_DO_NOT_WANT:
                sleep(random.uniform(PROCESS_NOT_WANT_RANGE_START,
                                     PROCESS_NOT_WANT_RANGE_END))
                self.state = STATE_WANTED

                for id in PROCESS_IDS:
                    if id == self.id:
                        continue
                    start_new_thread(self.request, (id,))

            elif self.state == STATE_WANTED:
                if self.permission_givers == PROCESS_IDS - {self.id}:
                    self.state = STATE_HELD
                    self.permission_givers = set()
                else:
                    sleep(0.5)

            else:
                sleep(random.uniform(PROCESS_HOLD_RANGE_START,
                                     PROCESS_HOLD_RANGE_END))
                self.state = STATE_DO_NOT_WANT

    def listen(self):
        rpyc.utils.server.ThreadedServer(
            listen_server_generator(self.handle_request),
            port=get_port_from_id(self.id)
        ).start()

    def request(self, id):
        conn = rpyc.connect('localhost', get_port_from_id(id), config={'sync_request_timeout': 300})
        response = conn.root.message(self.id, self.time, MESSAGE_REQUEST)
        assert response == MESSAGE_OK
        self.permission_givers.add(id)

    def handle_request(self, incoming_id, incoming_time):
        while True:
            if self.state == STATE_DO_NOT_WANT:
                return

            elif self.state == STATE_WANTED:
                if ((incoming_time < self.time or (incoming_time == self.time and incoming_id < self.id)) and
                        incoming_id not in self.permission_givers):
                    return
                else:
                    sleep(0.5)

            else:
                sleep(0.5)


def listen_server_generator(given_handler):
    class ListenServer(rpyc.Service):
        handler = given_handler

        def exposed_message(self, incoming_id, incoming_time, incoming_message):
            assert incoming_message == MESSAGE_REQUEST
            self.handler(incoming_id, incoming_time)
            return MESSAGE_OK

    return ListenServer


if __name__ == '__main__':
    n = int(argv[1])
    assert n > 0

    processes = []
    PROCESS_IDS = set()

    for i in range(n):
        process = Process(i)
        process.start()
        processes.append(process)
        PROCESS_IDS.add(i)

    print('Commands: quit, List, time-cs t, time-p t')

    while True:
        user_input = input().strip()

        if user_input == 'quit':
            break

        elif user_input == 'List':
            for process in processes:
                print(f'{process.id}, {process.state}')

        elif user_input[:7] == 'time-cs':
            t = int(user_input[7:].strip())
            PROCESS_HOLD_RANGE_END = max(10, t)

        elif user_input[:6] == 'time-p':
            t = int(user_input[6:].strip())
            PROCESS_NOT_WANT_RANGE_END = max(5, t)

        else:
            print('unknown input')
