# Scan the internets with masscan!
# masscan --rate=1000 -p1000-60000 <ip sub-block> -oJ <output file>
# Scan blocks, compress em, and keep a status file
import ipaddress
import json
import os
import typing

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


def compress(block: typing.List[ipaddress.IPv4Address]) -> typing.List[ipaddress.IPv4Network]:
    print(f'\rconverting addresses to networks...'.ljust(100), end='', flush=True)
    subnets: typing.List[ipaddress.IPv4Network] = [ipaddress.ip_network((addr, 32), False) for addr in block]

    for mask in range(31, -1, -1):
        print(f'\rcompressing subnets ({32 - mask}/32)...'.ljust(100), end='', flush=True)

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
                typing.List[ipaddress.IPv4Address]]:
    """Split a list of subnets into smaller blocks, based on the target mask"""
    building = []
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
    for net in subnets:
        can_fill = addr_count - len(building)
        if can_fill > net.num_addresses:
            building.extend(net.hosts())
        else:
            iterable = net.hosts()
            for host in iterable:
                if len(building) == addr_count:
                    total_done += len(building)
                    eta.step()
                    blocks_done += 1
                    rem = estimated_steps - blocks_done
                    print(f'\rabout {round(total_done / total_estimate * 100, 2)}% done;'
                          f' Estimated {eta.get(rem)} remaining (done {blocks_done} -> {total_done}) (currently in {net})'.ljust(100),
                          end='', flush=True)
                    yield building
                    building = []
                building.append(host)
    print('sequential block splitter: done')
    yield building


def load_config() -> dict:
    with open('masscan_in.json', 'r') as f:
        return json.load(f)


STRATEGIES = {
    'sequential': split_block
}


def write_progress_backup(data: int):
    with open('continue.bak', 'w') as f:
        f.write(str(data))


def read_progress_backup() -> int:
    if os.path.exists('continue.bak'):
        with open('continue.bak', 'r') as f:
            return int(f.read())
    return 0


def build_blocks(backup_between: int = 50, continuation: int = 0):
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

    if not os.path.exists('blocks'):
        os.mkdir('blocks')

    ctr = 0

    next(blocks)  # buffer
    if continuation > 0:
        print(f'fast-forward {continuation} blocks')
    for _ in range(continuation):
        next(blocks)  # and discard
        ctr += 1

    print(f'\nstarting...')
    for i, a in enumerate(blocks):
        ctr += 1
        if ctr % backup_between == 0:
            write_progress_backup(i)
        print("\n", compress(a))


if __name__ == '__main__':
    prog = read_progress_backup()
    build_blocks(continuation=prog)
