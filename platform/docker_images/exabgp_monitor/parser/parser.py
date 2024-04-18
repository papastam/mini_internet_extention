#!/usr/bin/python
import json
import logging

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
    messages = []
    try:
        temp_message = json.loads(line)
        if temp_message['type'] == 'update':
            log.debug('message: {}'.format(temp_message))

            try:
                update_msg = temp_message['neighbor']['message']['update']
            except Exception:
                log.warning('Update message not found in the message, skipping message...')
                return None

            if 'announce' in update_msg:

                origins = []
                announce_msg = update_msg['announce']
                if 'ipv4 unicast' in announce_msg:
                    origins.append(announce_msg['ipv4 unicast'])
                if 'ipv6 unicast' in announce_msg:
                    origins.append(announce_msg['ipv6 unicast'])

                for origin in origins:
                    prefixes = list(origin.values())[0]
                    for prefix in prefixes:
                        if 'as-path' in update_msg['attribute']:
                            as_path = None
                            for path_num in range(len(update_msg['attribute']['as-path'])):
                                path = update_msg['attribute']['as-path'][str(path_num)]
                                if path["element"] == "as-sequence":
                                    as_path = path["value"]
                            messages.append({
                                'type': 'A',
                                'timestamp': temp_message['time'],
                                'peer_asn': temp_message['neighbor']['asn']['peer'],
                                'path': as_path if as_path is not None else [],
                                'prefix': list(prefix.values())[0]
                            })

            elif 'withdraw' in update_msg:
                
                origins = []
                withdraw_msg = update_msg['withdraw']
                if 'ipv4 unicast' in withdraw_msg:
                    origins.append(withdraw_msg['ipv4 unicast'])
                if 'ipv6 unicast' in withdraw_msg:
                    origins.append(withdraw_msg['ipv6 unicast'])

                for origin in origins:
                    prefixes = list(origin.values())[0]
                    for prefix in prefixes:
                        messages.append({
                            'type': 'W',
                            'timestamp': temp_message['time'],
                            'peer_asn': temp_message['neighbor']['asn']['peer'],
                            'prefix': list(prefix.values())[0]
                        })
                    
    except Exception:
        log.exception('message exception')

    # PREFIX | ORIGIN AS | PEER AS | PATH | COLLECTOR | PEER | MESSAGE TYPE | MESSAGE | TIMESTAMP
    formated_msg = []
    try:
        for message in messages:
            log.debug('message: {}'.format(message))
            if message["type"]=="A":
                path_str = ''
                for asn in message['path']:
                    path_str += str(asn) + ' '

                formated_msg.append(f"{message['prefix']}|{message['path'][-1]}|{message['peer_asn']}|{path_str}|exabgp|{message['peer_asn']}|{message['type']}|{update_msg}|{message['timestamp']}")
            elif message["type"]=="W":
                formated_msg.append(f"{message['prefix']}||{message['peer_asn']}||exabgp|{message['peer_asn']}|{message['type']}|{update_msg}|{message['timestamp']}")
    except Exception:
        log.exception('Exception while formatting message')
        log.debug('message: {}'.format(message))
        return None

    return formated_msg

if __name__ == '__main__':
    while True:
        update = input()
        paresed_msg = message_parser(update)
        for message in paresed_msg:
            csv_file.write(message)
            csv_file.write("\n")
            csv_file.flush()
            log.info('Message written to csv file')
