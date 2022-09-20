import logging
import asyncio
import json
from typing import Dict, List, Any

from .socks_http import urlopen


CURRENCIES = [
    "BTC", # This will disable some exchange rate logic if set.
    "USD", "CHF", "EUR", "GBP", "AUD",
    "CAD", "JPY", "CNY","RUB", "UAH",
]  # type: List[str]

CURRENCIES.sort()


async def fetch_from_api(base_url: str, chain_1209k: str, loop=None) -> Dict[str, Any]:
    fiats = ",".join(CURRENCIES)  # type: str
    url = base_url.format(chain_1209k.upper(), fiats)  # type: str
    logging.info("Fetching rates from URL: %s", url)
    return json.loads(await urlopen(url, loop=loop))


async def fetch_exchange_rates(chain_1209k: str = "btc", loop=None) -> Dict[str, Dict]:
    coingecko_url = ("https://api.coingecko.com/api/v3/simple/price" +
                "?ids=bitcoin%2C&vs_currencies=" +
                "%2C".join(CURRENCIES))  # type: str
    ccomp_url = ("https://min-api.cryptocompare.com/data/" +
                 "price?fsym={}&tsyms={}")  # type: str
    all_rates = {}  # type: Dict[str, Dict[str, Any]]
    coingecko_json = await fetch_from_api(coingecko_url, chain_1209k, loop=loop)  # type: Dict[str, Any]
    rates = {}
    for symbol, value in coingecko_json.get('bitcoin').items():
        if symbol.upper() in CURRENCIES:
            rates[symbol.upper()] = value
    all_rates["coingecko"] = rates

    ccomp_json = await fetch_from_api(
        ccomp_url, chain_1209k, loop=loop)  # type: Dict[str, Any]
    all_rates["ccomp"] = ccomp_json

    print("EXCHANGE RATES: {} {} ".format(all_rates, ""))

    return all_rates


def main():
    loop = asyncio.get_event_loop()  # type: asyncio.AbstractEventLoop
    result = loop.run_until_complete(
        fetch_exchange_rates())  # type: Dict[str, float]
    print(result)
    loop.close()


if __name__ == "__main__":
    main()
