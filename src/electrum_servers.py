from logger import logging
import asyncio
import random
from socks_http import urlopen
import json
from typing import (List, Any)

async def get_random_server(loop: asyncio.AbstractEventLoop,
                            use_api: bool = False) -> List[Any]:
    """ Grabs a random Electrum server from a list that it
    gets from our REST api.

    :param chain: Our current chain info
    :param use_api: Should we try using the API to get servers?
    :returns: A server info list for a random Electrum server
    :raise: Raises a base Exception if there are no servers up on 1209k
    """
    servers = None
    if use_api:
        logging.info("Fetching server list from REST api.")
        with open("api_password_dev.txt", "r") as infile:
            api_password = infile.read().strip()
        bauth = ("nowallet", api_password)

        result = await urlopen(
            "http://y2yrbptubnrlraml.onion/servers",
            bauth_tuple=bauth, loop=loop
        )  # type: str
        if not result:
            logging.warning("Cannot get data from REST api.")
            result = json.dumps({"servers": []})
        servers = json.loads(result)["servers"]  # type: List[List[Any]]

    if not servers:
        logging.warning("No electrum servers found!")
        servers = load_servers_json()
    return random.choice(servers)


def load_servers_json() -> List[List[Any]]:
    """ Loads a list of Electrum servers from a local json file.
    :returns: A list of server info lists for all default Electrum servers
    """
    logging.info("Reading server list from file..")
    with open("servers.json", "r") as infile:
        return json.load(infile)
