from logger import logging

import asyncio
from typing import (
    Tuple, List, Any, Callable, Awaitable, Dict
)

from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo
from connectrum import ElectrumErrorResponse



class Connection:
    """ Connection object.
    Connects to an Electrum server, and handles all Stratum protocol messages.
    """
    #  pylint: disable=E1111
    def __init__(self,
                 loop: asyncio.AbstractEventLoop,
                 server: str,
                 port: int,
                 proto: str) -> None:
        """ Connection object constructor.

        :param loop: an asyncio event loop
        :param server: a string containing a hostname
        :param port: port number that the server listens on
        :returns: A new Connection object
        """
        logging.info("Connecting...")

        self.server_info = ServerInfo(server, hostname=server, ports=port)  # type: ServerInfo

        logging.info(str(self.server_info.get_port(proto)))

        self.client = StratumClient(loop)  # type: StratumClient
        self.connection = self.client.connect(
                self.server_info,
                proto_code=proto,
                use_tor=True,
                disable_cert_verify=(proto != "s")
            )  # type: asyncio.Future

        self.queue = None  # type: asyncio.Queue

        self.methods = {
            "get": "blockchain.transaction.get",
            "get_balance": "blockchain.scripthash.get_balance",
            "listunspent": "blockchain.scripthash.listunspent",
            "get_history": "blockchain.scripthash.get_history",
            "get_header": "blockchain.block.header", # was "get_header" previously, removed in favor of header in electrum
            "subscribe": "blockchain.scripthash.subscribe",
            "subscribe_headers": "blockchain.headers.subscribe",
            "estimatefee": "blockchain.estimatefee",
            "relayfee": "blockchain.relayfee", 
            "broadcast": "blockchain.transaction.broadcast"
        }  # type: Dict[str, str]

    async def do_connect(self) -> None:
        """ Coroutine. Establishes a persistent connection to an Electrum server.
        Awaits the connection because AFAIK an init method can't be async.
        """
        await self.connection
        logging.info("Connected to server")

    async def listen_rpc(self, method: str, args: List) -> Any:
        """ Coroutine. Sends a normal RPC message to the server and awaits response.

        :param method: The Electrum API method to use
        :param args: Params associated with current method
        :returns: Future. Response from server for this method(args)
        """
        res = None
        method = self.methods.get(method, method) # lookup shortcuts or use "method" instead
        try:
            res = await self.client.RPC(method, *args)
        except Exception as ex:
            print("listen_rpc Exception {}".format(ex))
            if method.endswith("broadcast"):
                return ex
        return res

    def listen_subscribe(self, method: str, args: List) -> None:
        """ Sends a "subscribe" message to the server and adds to the queue.
        Throws away the immediate future containing the "history" hash.

        :param method: The Electrum API method to use
        :param args: Params associated with current method
        """
        method = self.methods.get(method, method) # lookup shortcuts or use "method" instead

        t = self.client.subscribe(
            method, *args
        )  # type: Tuple[asyncio.Future, asyncio.Queue]
        future, queue = t

        self.queue = queue
        return future

    async def consume_queue(self, queue_func: Callable[[List[str]], Awaitable[None]]) -> None:
        """ Coroutine. Infinite loop that consumes the current subscription queue.
        :param queue_func: A function to call when new responses arrive
        """
        while True:
            logging.info("Awaiting queue..")
            result = await self.queue.get()  # type: List[str]
            await queue_func(result)
