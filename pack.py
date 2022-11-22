import time
from typing import List, Dict, Union, Tuple
import threading

from mcstatus import JavaServer
from mcstatus.pinger import PingResponse


def bulk_req_status(servers: List[str], thread_cap: int = 5) -> Dict[str, Tuple[bool, Union[PingResponse, str]]]:
    results = {}
    threads = []
    todos = servers.copy()

    def worker():
        while len(todos) > 0:
            server = todos.pop()
            parts = server.split(':')
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 25565
            # print('\rworker: {}\n'.format(server), end='')
            try:
                s = JavaServer(host, port)
                s.timeout = 1
                results[server] = (True, s.status())
            except Exception as e:
                results[server] = (False, str(e))

    for _ in range(thread_cap):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    while len(threads) > 0:
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        print('\r', end='', flush=True)
        print(f'running {len(threads)} / {thread_cap},'
              f' {len(todos) + len(threads)} to do,'
              f' {len(todos)} queued'.ljust(100), end='', flush=True)
        time.sleep(0.1)
    print('\rFinished', flush=True)
    return results


if __name__ == '__main__':
    # test = [
    #     '54.39.68.58:25465',
    #     '54.39.68.58:25565',
    #     '54.39.68.58:25570',
    #     '54.39.68.58:25571',
    #     '54.39.68.58:25574',
    #     '54.39.68.58:25575',
    #     '54.39.68.58:25580',
    #     '54.39.68.58:25585',
    #     '54.39.68.58:25586',
    #     '54.39.68.58:25587',
    #     '54.39.68.58:25589',
    #     '54.39.68.58:25591',
    #     '54.39.68.58:25601',
    #     '54.39.68.58:25602',
    #     '54.39.68.58:25612',
    #     '54.39.68.58:25613',
    #     '54.39.68.58:25616',
    #     '54.39.68.58:25617',
    #     '54.39.68.58:25620',
    #     '54.39.68.58:25622',
    #     '54.39.68.58:25624',
    #     '54.39.68.58:25627',
    #     '54.39.68.58:25630',
    #     '54.39.68.58:25648',
    #     '54.39.68.58:25652'
    # ]
    test = ['51.68.204.29:25606']
    results = bulk_req_status(test, 20)
    for addr, result in results.items():
        ok, res = result
        if ok:
            # print(f'{addr}: {res.players.online}/{res.players.max} on {res.version.name} {res.version.protocol}')
            print(f'{addr}: {res.description}')
        else:
            print(f'{addr}: [!] {res}')
