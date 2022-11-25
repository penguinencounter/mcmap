# Scan the internets with masscan!
# masscan --rate=1000 -p1000-60000 <ip sub-block> -oJ <output file>
# Scan blocks, compress em, and keep a status file
import ipaddress
import json
import math
import multiprocessing
import os
import shlex
import subprocess
import time
import typing
from math import floor

from scanner.eta import ETA


def process_exclusions(subnet: ipaddress.IPv4Network, exclusions: typing.List[str]) -> typing.List[
        ipaddress.IPv4Network]:
    fragmented: typing.List[ipaddress.IPv4Network] = [subnet]
    for exclusion in exclusions:
        print('\r', end='', flush=True)
        print(f'Exclusions: {exclusion}; {len(fragmented)} net fragments', end='', flush=True)
        net = ipaddress.ip_network(exclusion, False)
        # find the correct block(s) that contains the exclusion
        for i, block in enumerate(fragmented):
            if net.subnet_of(block):
                # split the block into 2, and remove the original
                new_blocks = list(block.address_exclude(ipaddress.ip_network(exclusion)))
                fragmented.pop(i)
                # add the new blocks
                fragmented.extend(new_blocks)
                break
    return fragmented


def dump_block(block: typing.List[ipaddress.IPv4Address], filename: str):
    with open(filename, 'wb') as f:
        for addr in block:
            f.write(addr.packed + b' ')


def compress(block: typing.List[ipaddress.IPv4Network]) -> typing.List[ipaddress.IPv4Network]:
    subnets: typing.List[typing.Union[ipaddress.IPv4Network]] = block

    for mask in range(31, -1, -1):
        # sort the subnets by their first address
        subnets.sort(key=lambda x: x.network_address.packed)
        # merge subnets together if they are contiguous
        merged = []
        # take pairs
        for i in range(0, len(subnets), 2):
            # if the first subnet is contiguous with the next one, merge them
            if i + 1 < len(subnets) and subnets[i].broadcast_address + 1 == subnets[i + 1].network_address:
                merged.append(ipaddress.ip_network((subnets[i].network_address, mask), False))
            else:
                merged.append(subnets[i])
                if i + 1 < len(subnets):
                    merged.append(subnets[i + 1])
        subnets = merged
    return subnets


def split_block(subnets: typing.List[ipaddress.IPv4Network], target_mask: int = 24) -> typing.List[
        typing.List[ipaddress.IPv4Network]]:
    """Split a list of subnets into smaller blocks, based on the target mask"""
    addr_count = 2 ** (32 - target_mask)
    total_estimate = sum(net.num_addresses for net in subnets)
    estimated_steps = total_estimate / addr_count
    eta = ETA(64)
    total_done = 0
    blocks_done = 0
    print('sequential block splitter: {} addresses per block'.format(addr_count))
    print('sequential block splitter: {} estimated total blocks'.format(estimated_steps))
    print('sequential block splitter: on-demand ready')
    yield None
    while True:
        parts = []
        fill = 0
        while fill < addr_count:
            if len(subnets) == 0:
                yield parts
                return
            remaining = addr_count - fill
            next_block_up = subnets.pop(0)
            max_next_mask = 32 - floor(math.log2(remaining))
            if next_block_up.prefixlen >= max_next_mask:
                parts.append(next_block_up)
                fill += next_block_up.num_addresses
            else:
                # split the block into parts
                new_blocks = list(next_block_up.subnets(new_prefix=max_next_mask))
                if len(new_blocks) > 1:  # safety check
                    subnets = new_blocks[1:] + subnets
                parts.append(new_blocks[0])
                fill += new_blocks[0].num_addresses
        total_done += fill
        blocks_done += 1
        eta.step()
        yield parts


def load_config() -> dict:
    with open('masscan_in.json', 'r') as f:
        return json.load(f)


STRATEGIES = {
    'sequential': split_block
}


def write_progress_backup(data: int):
    with open('continue.bak', 'w') as f:
        f.write(str(data))


MASSCAN_PARAMS = shlex.split("-p 25565")
batch = []
stop = False
thread_state = {"main": "run"}
I_AM_A = os.getpid()


def runner(q: multiprocessing.Queue):
    score = 0
    print(f'[{I_AM_A}] Starting up...', flush=True)
    while True:
        work = q.get(True)
        if work == "STOP":
            print(f'\r[{I_AM_A}] ({score}) Stopping!'.ljust(100), end='', flush=True)
            break
        print(f'\r[{I_AM_A}] ({score}) Starting to work on job #{score + 1}'.ljust(100), end='', flush=True)
        compr = compress(work)
        write_task_file(compr)
        print(f'\r[{I_AM_A}] ({score}) Finished job #{score + 1}'.ljust(100), end='', flush=True)
        score += 1


def write_task_file(subnets: typing.List[ipaddress.IPv4Network]):
    idx = 0
    while os.path.exists(f'tasks/{idx}.masscan'):
        idx += 1
    with open(f'tasks/{idx}.masscan', 'wb') as f:
        f.write(
            subprocess.check_output(['masscan', '--echo'] + MASSCAN_PARAMS + list(map(lambda x: x.exploded, subnets))))


def read_progress_backup() -> int:
    if os.path.exists('tasks'):
        c = 0
        while os.path.exists(f'tasks/{c}.masscan'):
            c += 1
        return c
    return 0


def display_status():
    print('\r', end='', flush=True)
    for name, state in thread_state.items():
        print(f'{name}: {state}'.ljust(12), end='')
    print('', end='', flush=True)


def build_blocks(backup_between: int = 50, continuation: int = 0):
    global stop, batch
    conf = load_config()
    target = ipaddress.ip_network(conf['target'], False)
    block_mask = conf['block_mask']
    excl = conf['exclude']
    addrs_per_block = 2 ** (32 - block_mask)
    print(f'Current configuration: Scan {target} -> .../{block_mask} blocks [{addrs_per_block} addrs each]')
    print(f'Processing {len(excl)} exclusions')
    frags = process_exclusions(target, excl)
    print(f'    ... {len(frags)} fragments')
    strategy = STRATEGIES[conf['blocking_strategy']]
    print(f'Using strategy: {conf["blocking_strategy"]}')
    blocks = strategy(frags, block_mask)
    next(blocks)
    for i, v in enumerate(blocks):
        print(f'\r{i}, {sum(map(lambda x: x.num_addresses, v))}'.ljust(50), end='', flush=True)
    return
    if not os.path.exists('tasks'):
        os.mkdir('tasks')

    ctr = 0

    next(blocks)  # buffer
    if continuation > 0:
        print(f'fast-forward {continuation} blocks')
    for _ in range(continuation):
        next(blocks)  # and discard
        ctr += 1

    print(f'\nstarting...')
    THREAD_COUNT = 15
    procs = []
    work_pool = multiprocessing.Queue(50)  # specify max size to limit mem usage
    for _ in range(THREAD_COUNT):
        p = multiprocessing.Process(target=runner, args=(work_pool,))
        p.start()
        procs.append(p)

    try:
        for i, a in enumerate(blocks):
            ctr += 1
            if ctr % backup_between == 0:
                write_progress_backup(i)
            print(f'\r[{I_AM_A}] Job added...'.ljust(100), end='', flush=True)
            while work_pool.full():
                time.sleep(1)
            work_pool.put(a)
    finally:
        work_pool.put("STOP")
        t = 0
        TIMEOUT = 10
        last = time.time()
        while any(p.is_alive() for p in procs):
            t += (time.time() - last)
            last = time.time()
            time.sleep(0.01)
            print(f'\r[{I_AM_A}] Waiting for threads to stop...'.ljust(100), end='', flush=True)
            if t > TIMEOUT:
                print(f'\r[{I_AM_A}] Timeout waiting for threads to stop!'.ljust(100), end='', flush=True)
                for p in procs:
                    p.kill()
        print(f'\r[{I_AM_A}] Stopped.'.ljust(100), end='\n', flush=True)


if __name__ == '__main__':
    I_AM_A = f'{I_AM_A} (main)'
    prog = read_progress_backup()
    build_blocks(continuation=prog)
