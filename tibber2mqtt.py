import argparse
import json
import logging
import logging.config
import os
import requests
import time

from collections.abc import MutableMapping
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from paho.mqtt import client as mqtt_client
from pathlib import Path

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

first_reconnect_delay = 1
reconnect_rate = 2
max_reconnect_count = 12
max_reconnect_delay = 60
mqttclient = None
mqttcache = {}


def get_token(tibber_email, tibber_password, token_file='token', force_new=False):
    token = ''

    token_file_path = "config/" + Path(token_file).name

    if not force_new and Path(token_file_path).is_file():
        with open(token_file_path, 'r') as file:
            token = file.readline()
            if token: logging.debug("Token locally found")

    if force_new or not token:
        logging.debug('Create new Token')
        url = 'https://app.tibber.com/login.credentials'
        tibber_credentials = {'email': tibber_email, 'password': tibber_password}
        headers = {'Content-type': 'application/json'}
        x = requests.post(url, json=tibber_credentials, headers=headers)
        token_data = json.loads(x.text)

        with open(token_file_path, 'w+') as file:
            logging.debug('write new token')
            file.write(token_data['token'])
            token = token_data['token']
    return token


def request_tibber_data(token, query_file):
    logging.debug('Requesting Data')
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(url='https://app.tibber.com/v4/gql', headers={'Authorization': 'Bearer ' + token})

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(get_gql(query_file))
    return client.execute(query)


def get_gql(query_file):
    query_file_name = Path(query_file).name

    if Path("config/" + query_file_name).is_file():
        return Path("config/" + query_file_name).read_text()
    else:
        return '''
          query {
            me {
              homes {
                bubbles {
                  id
                  type
                  title
                  context {
                    key
                      value
                  }
                }
              }
            }
          }
        '''


def connect_mqtt(broker, port, client_id, username=None, password=None):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_disconnect(client, userdata, rc):
        logging.info("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, first_reconnect_delay
        while reconnect_count < max_reconnect_count:
            logging.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= reconnect_rate
            reconnect_delay = min(reconnect_delay, max_reconnect_delay)
            reconnect_count += 1
        logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker, port)
    return client


def get_args():
    ap = argparse.ArgumentParser(prog="Tibber2MQTT", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    global_group = ap.add_argument_group("Global")
    global_group.add_argument('-d',
                              action='store_true',
                              default=os.environ.get(key='TIBBER2MQTT_DEBUG') or False,
                              dest='debug',
                              help='Enable Debug Mode'
                              )
    global_group.add_argument('-v',
                              action='store_true',
                              default=os.environ.get(key='TIBBER2MQTT_VERBOSE') or False,
                              dest='verbose',
                              help='(Verbose) Talk to me baby'
                              )

    tibber_group = ap.add_argument_group("Tibber")
    tibber_group.add_argument('--tibber-email',
                              default=os.environ.get(key='TIBBER2MQTT_TIBBER_EMAIL') or argparse.SUPPRESS,
                              dest='tibber_email',
                              help='Tibber email',
                              required=not os.environ.get(key='TIBBER2MQTT_TIBBER_EMAIL'),
                              )
    tibber_group.add_argument('--tibber-password',
                              default=os.environ.get(key='TIBBER2MQTT_TIBBER_PASS') or argparse.SUPPRESS,
                              dest='tibber_password',
                              help='Tibber password',
                              required=not os.environ.get(key='TIBBER2MQTT_TIBBER_PASS')
                              )
    tibber_group.add_argument('--token-filename',
                              default=os.environ.get(key='TIBBER2MQTT_TOKEN_FILENAME') or "token",
                              dest='token_filename',
                              help='Filename of the File where the Token will be read from',
                              required=False
                              )
    tibber_group.add_argument('--query-filename',
                              default=os.environ.get(key='TIBBER2MQTT_QUERY_FILENAME') or "tibber_bubbles",
                              dest='tibber_query_filename',
                              help='Filename of the File where the gql query will be saved into',
                              required=False
                              )
    tibber_group.add_argument('-i', '--request-interval',
                              default=os.environ.get(key='TIBBER2MQTT_REQUEST_INTERVAL') or 60,
                              dest='request_interval',
                              help='The request interval',
                              type=int
                              )

    mqtt_group = ap.add_argument_group("MQTT", "Information needed for the MQTT Connection")
    mqtt_group.add_argument('-s', '--mqtt-single',
                            action='store_true',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_SINGLE') or False,
                            dest='mqtt_single',
                            help='Send each value individually to the MQTT Broker'
                            )
    mqtt_group.add_argument('-c', '--cache',
                            action='store_true',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_CACHE') or False,
                            dest='mqtt_cache',
                            help='Cache the send values (works best in single (-s) mode)'
                            )
    mqtt_group.add_argument('--mqtt-host',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_HOST') or 'localhost',
                            dest='mqtt_host',
                            help='MQTT Host to connect to'
                            )
    mqtt_group.add_argument('--mqtt-port',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_PORT') or '1883',
                            dest='mqtt_port',
                            help='MQTT port to connect to',
                            type=int
                            )
    mqtt_group.add_argument('--mqtt-topic',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_TOPIC') or 'tibber2mqtt',
                            dest='mqtt_topic',
                            help='MQTT Topic to publish to',
                            required=False)
    mqtt_group.add_argument('--mqtt-client-id',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_CLIENT_ID') or 'tibber2mqtt',
                            dest='mqtt_client_id',
                            help='MQTT Client-ID',
                            required=False
                            )
    mqtt_group.add_argument('--mqtt-user',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_USER') or None,
                            dest='mqtt_user',
                            help='MQTT user to connect to',
                            required=False,
                            )
    mqtt_group.add_argument('--mqtt-password',
                            default=os.environ.get(key='TIBBER2MQTT_MQTT_PASS') or None,
                            dest='mqtt_password',
                            help='MQTT password to connect to',
                            required=False,
                            )

    args = ap.parse_args()
    print(args)
    return args


def flatten(d: MutableMapping, parent_key: str = '', sep: str = '.') -> MutableMapping:
    items = []
    if isinstance(d, MutableMapping):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, (MutableMapping, list)):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
    elif isinstance(d, list):
        index = 0
        for v in d:
            new_key = parent_key + sep + str(index) if parent_key else str(index)
            if isinstance(v, (MutableMapping, list)):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
    return dict(items)


def send_data(topic, data_to_send, mqtt_cache, mqtt_single):
    global mqttcache
    logging.debug("Cache %s", mqttcache)
    if mqtt_single:
        data_to_send = flatten(data_to_send, sep="_")
        for k, v in data_to_send.items():
            if not mqtt_cache or (mqtt_cache and (k not in mqttcache or mqttcache[k] != v)):
                logging.info("Send %s -> %s", str(k), str(v))
                mqttclient.publish(topic + "/" + k, v)
                mqttcache[k] = v
            else:
                logging.debug("Found %s in cache, skip!", str(k))
    else:
        logging.debug(data_to_send)
        mqttclient.publish(topic, json.dumps(data_to_send))


if __name__ == '__main__':
    args = get_args()
    loglevel = logging.WARNING
    if not args.debug and args.verbose:
        print('Verbose mode enabled')
        loglevel = logging.INFO
    if args.debug:
        print('Debug mode enabled')
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=loglevel)

    Path("config").mkdir(exist_ok=True)

    mqttclient = connect_mqtt(args.mqtt_host, args.mqtt_port, args.mqtt_client_id, args.mqtt_user, args.mqtt_password)
    logging.info("Connected successfully to %s:%s", args.mqtt_host, args.mqtt_port)
    logging.info("MQTT Topic is: %s", args.mqtt_topic)

    token = get_token(args.tibber_email, args.tibber_password, args.token_filename)

    start_time = time.monotonic()
    token_renew_counter = 0
    while True:
        try:
            tibber_data = request_tibber_data(token, args.tibber_query_filename)
            token_renew_counter = 0
            send_data(args.mqtt_topic, tibber_data, mqtt_cache=args.mqtt_cache, mqtt_single=args.mqtt_single)
        except TransportQueryError as e:
            logging.error('Failed to send Request: %s', e.errors)
            if token_renew_counter >= 10:
                logging.error(
                    'Retried 10 times to get a new and valid token but could not execute the Request. -> EXIT!')
                exit()
            token_renew_counter = token_renew_counter + 1
            logging.info('Error happened - requesting new Token! Retry counter: ' + str(token_renew_counter))
            token = get_token(args.tibber_email, args.tibber_password, args.token_file, force_new=True)
        time.sleep(args.request_interval - ((time.monotonic() - start_time) % args.request_interval))
