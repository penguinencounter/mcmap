import json
from typing import Union, Tuple, Dict

from mcstatus.pinger import PingResponse

import formatting
import pack


with open('server_listing.html') as f:
    TEMPLATE = f.read()
with open('server_template.html') as f:
    BIG_TEMPLATE = f.read()


def build(results: Dict[str, Tuple[bool, Union[PingResponse, str]]], include_errs: bool = True):
    output = ''
    i = 0
    for server, result in results.items():
        i += 1
        if i % 20 == 0:
            print('\r', end='', flush=True)
            print(f'generate: {i} / {len(results)} | {len(output)} char so far'.ljust(100), end='', flush=True)
        if result[0]:
            ping = result[1]
            motd = formatting.process_formatted_string(ping.description)
            players = ping.players.online
            max_players = ping.players.max
            version_name = ping.version.name
            version_protocol = ping.version.protocol
            ip_fmt = ''
        else:
            motd = '<span class="fmt_c">Error: {}</span>'.format(result[1])
            players = '<span class="fmt_c">?</span>'
            max_players = '<span class="fmt_c">?</span>'
            version_name = '<span class="fmt_c">?</span>'
            version_protocol = '<span class="fmt_c">?</span>'
            ip_fmt = ' bad'
            if not include_errs:
                continue
        output += TEMPLATE \
            .replace('$current_players', str(players)) \
            .replace('$max_players', str(max_players)) \
            .replace('$version_name', version_name) \
            .replace('$protocol_ver', str(version_protocol)) \
            .replace('$motd_format', motd) \
            .replace('$ip', server) \
            .replace('$additional_ip_fmt', ip_fmt)
    print('generate done')
    return BIG_TEMPLATE.replace('$servers', output)


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
    #     # '54.39.68.58:25630',
    #     # '54.39.68.58:25648',
    #     '54.39.68.58:25652'
    # ]
    # print('loading data...', flush=True)
    # with open('all_addrs.json') as f:
    #     test = json.load(f)
    test = ['51.68.204.29:25606']
    results = pack.bulk_req_status(test, 1000)

    with open('results2.html', 'w', encoding='utf-8') as f:
        f.write(build(results, False))
