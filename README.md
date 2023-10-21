# Tibber2MQTT
<base target="_blank">

This is a little helper Tool, that requests the Data from tibber and publishes the result in the MQTT Broker
## Description

Tibber offers a pretty decent api which can be used to request a lot of data. You can request information from Tibber itself or connect your devices to Tibber and request even that information.

For example, I have a Fronius Inverter and after adding the Inverter to my App, I can request the id of the "bubbles" (icons shown in the App) and add my inverter to the request query.

The Queries are made through a build GraphQL query. Which is simply a JSON structure to select the fields you want. 

## Getting Started

### TL:DR
```
docker run -d --restart=always \
    -e TIBBER2MQTT_TIBBER_EMAIL="your-mail@example.com" \
    -e TIBBER2MQTT_TIBBER_PASS="..." \
    -e TIBBER2MQTT_MQTT_CACHE=1 \
    -e TIBBER2MQTT_MQTT_SINGLE=1 \
    -e TIBBER2MQTT_MQTT_HOST=192.168.0.3 \
    -e TIBBER2MQTT_QUERY_FILENAME="your_file_name" \
    --name tibber2mqtt freakern/tibber2mqt
```

### Build your Query

The key to request the Values from Tibber is to get a working query.

A quick example
1. Go to the [Tibber login](https://app.tibber.com/login) and log in to your account
2. Go to the [Query Playground](https://app.tibber.com/v4/gql) of Tibber
3. Paste the [tibber_bubbles](config/tibber_bubbles) content into the left pane
4. Press the Play Button

This will show you all your bubbles in the app. 
Navigate through the `DOCS` Menu to the right in the [Query Playground](https://app.tibber.com/v4/gql) to create a query that fits your needs

### Install and Start

Let's start with the [tibber_bubbles](config/tibber_bubbles) (don't define the query-filename)

```shell 
git clone https://github.com/FreakErn/Tibber2MQTT.git
cd Tibber2MQTT
python -m pip install -r requirements.txt
python tibber2mqtt.py --tibber-email your-mail@example.com --tibber-password your-password --mqtt-host 192.168.0.3 --debug --cache --mqtt-single  
```
When you have your query ready, place the textfile with the Query in the config folder and add the parameter:
> --query-filename "your_file_name"

### Docker

```Docker
docker run -d --restart=always \
  -e TIBBER2MQTT_TIBBER_EMAIL="your-email@example.com" \
  -e TIBBER2MQTT_TIBBER_PASS="your-password" \
  -e TIBBER2MQTT_MQTT_HOST=192.168.0.3 \
  -e TIBBER2MQTT_DEBUG=1 
  -e TIBBER2MQTT_MQTT_CACHE=1 \
  -e TIBBER2MQTT_MQTT_SINGLE=1 \
  freakern/tibber2mqtt
```
> Cache is a simple "Do not publish the same value again" and the Single Parameter is to send each value individually else it would publish the entire json each time (if it's not cached)


When you have your query ready, place the textfile with the Query in the config folder and add the ENV Variable (before the last line):
```bash
-v ${PWD}/config:/app/config \
-e TIBBER2MQTT_QUERY_FILENAME="your_file_name" \
```

## Help

#### Shell Parameter
```shell
usage: Tibber2MQTT [-h] [-d] [-v] --tibber-email TIBBER_EMAIL --tibber-password TIBBER_PASSWORD [--token-filename TOKEN_FILENAME] [--query-filename TIBBER_QUERY_FILENAME] [-i REQUEST_INTERVAL] [-s] [-c]
                   [--mqtt-host MQTT_HOST] [--mqtt-port MQTT_PORT] [--mqtt-topic MQTT_TOPIC] [--mqtt-client-id MQTT_CLIENT_ID] [--mqtt-user MQTT_USER] [--mqtt-password MQTT_PASSWORD]

options:
  -h, --help            show this help message and exit

Global:
  -d                    Enable Debug Mode (default: False)
  -v                    (Verbose) Talk to me baby (default: False)

Tibber:
  --tibber-email TIBBER_EMAIL
                        Tibber email
  --tibber-password TIBBER_PASSWORD
                        Tibber password
  --token-filename TOKEN_FILENAME
                        Filename of the File where the Token will be read from (default: token)
  --query-filename TIBBER_QUERY_FILENAME
                        Filename of the File where the gql query will be saved into (default: tibber_bubbles)
  -i REQUEST_INTERVAL, --request-interval REQUEST_INTERVAL
                        The request interval (default: 60)

MQTT:
  Information needed for the MQTT Connection

  -s, --mqtt-single     Send each value individually to the MQTT Broker (default: False)
  -c, --cache           Cache the send values (works best in single (-s) mode) (default: False)
  --mqtt-host MQTT_HOST
                        MQTT Host to connect to (default: localhost)
  --mqtt-port MQTT_PORT
                        MQTT port to connect to (default: 1883)
  --mqtt-topic MQTT_TOPIC
                        MQTT Topic to publish to (default: tibber2mqtt)
  --mqtt-client-id MQTT_CLIENT_ID
                        MQTT Client-ID (default: tibber2mqtt)
  --mqtt-user MQTT_USER
                        MQTT user to connect to (default: None)
  --mqtt-password MQTT_PASSWORD
                        MQTT password to connect to (default: None)

```

#### Docker ENV Vars
| ENV Variable Name                 | Description                                                                                               | Default        | Required |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------|----------------|----------|
| TIBBER2MQTT_DEBUG                 | Enable Debug Mode                                                                                         | False          | False    |
| TIBBER2MQTT_VERBOSE               | Enable Verbose Mode                                                                                       | False          | False    |
| TIBBER2MQTT_TIBBER_EMAIL          | Tibber email                                                                                              |                | True     |
| TIBBER2MQTT_TIBBER_PASS           | Tibber Password                                                                                           |                | True     |
| TIBBER2MQTT_TOKEN_FILENAME        | Filename of the File where the Token will be read from and write into                                     | token          | False    |
| TIBBER2MQTT_QUERY_FILENAME        | Filename of the File where the gql query will be saved into (must be located in the config folder)        | tibber_bubbles | False    |
| TIBBER2MQTT_REQUEST_INTERVAL      | The request interval                                                                                      |                | False    |
| TIBBER2MQTT_MQTT_SINGLE           | Send each value individually to the MQTT Broker                                                           | False          | False    |
| TIBBER2MQTT_MQTT_SINGLE_SEPARATOR | Separator for the single (-s) parameter. If it is a slash, you\'ll be able to subscripe just to subtopics | /              | False    |
| TIBBER2MQTT_MQTT_CACHE            | Cache the send values (works best in single (-s) mode)                                                    | False          | False    |
| TIBBER2MQTT_MQTT_HOST             | MQTT Host to connect to                                                                                   | localhost      | False    |
| TIBBER2MQTT_MQTT_PORT             | MQTT port to connect to                                                                                   | 1883           | False    |
| TIBBER2MQTT_MQTT_TOPIC            | MQTT Topic to publish to                                                                                  | tibber2mqtt    | False    |
| TIBBER2MQTT_MQTT_CLIENT_ID        | MQTT Client-ID                                                                                            | tibber2mqtt    | False    |
| TIBBER2MQTT_MQTT_USER             | MQTT user to connect to                                                                                   |                | False    |
| TIBBER2MQTT_MQTT_PASS             | MQTT password to connect to                                                                               |                | False    |

## Disclaimer & I need your help

I do not have a Tibber Contract, I am just using the account to connect to my Polestar 2. So I can't really help if it is about the data related to a running contract.

That out of the way, if you have a good working Tibber Query and you want to share it. Please create a Pull-Request with your running query in the config folder. 
I would suggest you replace the ID's and put some comments with a `#` Symbol in front of it 


## License

This project is licensed under the Apache 2.0 License - see the LICENSE.md file for details