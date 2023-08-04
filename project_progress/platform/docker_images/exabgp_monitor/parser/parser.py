#!/usr/bin/python
import json
import logging
from threading import Lock

log = logging.getLogger('artemis')
log.setLevel(logging.DEBUG)
# create a file handler
handler = logging.FileHandler('/parser/parser.log')
handler.setLevel(logging.DEBUG)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(handler)

#Open output csv file
csv_file = open('/parser/output.csv', 'w')

def message_parser(line):
    message = None
    try:
        temp_message = json.loads(line)
        if temp_message['type'] == 'update':
            log.debug('message: {}'.format(temp_message))

            update_msg = temp_message['neighbor']['message']['update']

            if 'announce' in update_msg:
                announce_msg = update_msg['announce']
                v4_origins = {}
                if 'ipv4 unicast' in announce_msg:
                    v4_origins = announce_msg['ipv4 unicast']
                v6_origins = {}
                if 'ipv6 unicast' in announce_msg:
                    v6_origins = announce_msg['ipv6 unicast']
                for origin in set(v4_origins.keys()).union(set(v6_origins.keys())):
                    if 'as-path' in update_msg['attribute']:
                        as_path = None
                        for path_num in range(len(update_msg['attribute']['as-path'])):
                            path = update_msg['attribute']['as-path'][str(path_num)]
                            if path["element"] == "as-sequence":
                                as_path = path["value"]
                        message = {
                            'type': 'A',
                            'timestamp': temp_message['time'],
                            'peer_asn': temp_message['neighbor']['asn']['peer'],
                            'path': as_path if as_path is not None else [],
                            'prefix': []
                        }
                        prefixes = []
                        if origin in v4_origins:
                            prefixes.extend(v4_origins[origin])
                        if origin in v6_origins:
                            prefixes.extend(v6_origins[origin])
                        for prefix in prefixes:
                            message['prefix'].append(list(prefix.values())[0])

            elif 'withdraw' in update_msg:
                withdraw_msg = update_msg['withdraw']
                message = {
                    'type': 'W',
                    'timestamp': temp_message['time'],
                    'peer_asn': temp_message['neighbor']['asn']['peer'],
                    'prefix': []
                }
                prefixes = []
                if 'ipv4 unicast' in withdraw_msg:
                    prefixes.extend(withdraw_msg['ipv4 unicast'])
                if 'ipv6 unicast' in withdraw_msg:
                    prefixes.extend(withdraw_msg['ipv6 unicast'])
                for prefix in prefixes:
                    message['prefix'].append(prefix)
                    
    except Exception:
        log.exception('message exception')

    # PREFIX | ORIGIN AS | PEER AS | PATH | COLLECTOR | PEER | MESSAGE TYPE | MESSAGE | TIMESTAMP
    formated_msg = None
    try:
        if message is not None:
            log.debug('message: {}'.format(message))
            if message["type"]=="A":
                path_str = ''
                for asn in message['path']:
                    path_str += str(asn) + ' '

                formated_msg = f"{message['prefix'][0]}|{message['path'][-1]}|{message['peer_asn']}|{path_str}|exabgp|{message['peer_asn']}|{message['type']}|{update_msg}|{message['timestamp']}"
            elif message["type"]=="W":
                formated_msg = f"{message['prefix'][0]}||{message['peer_asn']}||exabgp|{message['peer_asn']}|{message['type']}|{update_msg}|{message['timestamp']}"
    except Exception:
        log.exception('Exception while formatting message')
        log.debug('message: {}'.format(message))
        return None

    return formated_msg

if __name__ == '__main__':
    while True:
        update = input()
        paresed_msg = message_parser(update)
        if paresed_msg is not None:
            csv_file.write(paresed_msg)
            csv_file.write("\n")
            csv_file.flush()
            log.info('Message written to csv file')
