import logging
import asyncio
import json
from typing import Dict, List, Any
import numpy as np
from socks_http import urlopen
import requests

CURRENCIES = [
    "BTC", # This will disable some exchange rate logic if set.
    "USD", "CHF", "EUR", "GBP", "AUD",
    "CAD", "JPY", "CNY","RUB", "UAH",
]  # type: List[str]

CURRENCIES.sort()


def reject_outliers(data, m=2.):
    """ """
    data = np.array(data)
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.)
    return data[s < m].tolist()

async def fetch_from_api(base_url: str, chain_1209k: str, loop=None) -> Dict[str, Any]:
    fiats = ",".join(CURRENCIES)  # type: str
    url = base_url.format(chain_1209k.upper(), fiats)  # type: str
    logging.info("Fetching rates from URL: %s", url)
    return json.loads(await urlopen(url, loop=loop))

async def fetch_single_from_api(base_url: str, loop=None) -> Dict[str, Any]:
    logging.info("Fetching rates from URL: %s", base_url)
    response = requests.get(base_url, timeout=2.5)
    return response.json()

async def fetch_exchange_rates(chain_1209k: str = "btc", loop=None) -> Dict[str, Dict]:
    """ """
    all_rates = {}

    coingecko_url = ("https://api.coingecko.com/api/v3/simple/price" +
                "?ids=bitcoin%2C&vs_currencies=" +
                "%2C".join(CURRENCIES))  # type: str
    try:
        coingecko_json = await fetch_from_api(coingecko_url, chain_1209k, loop=loop)
        rates = {}
        for symbol, value in coingecko_json.get('bitcoin').items():
            if symbol.upper() in CURRENCIES:
                rates[symbol.upper()] = value
        all_rates["coingecko"] = rates
        print (rates)
    except Exception as ex:
        logging.error("coingecko_url call failed with {}".format(ex), exc_info=True)

    ccomp_url = ("https://min-api.cryptocompare.com/data/price?fsym={}&tsyms={}")  # type: str
    try:
        ccomp_json = await fetch_from_api(
            ccomp_url, chain_1209k, loop=loop)
        all_rates["ccomp"] = ccomp_json
    except Exception as ex:
        logging.error("coingecko_url call failed with {}".format(ex), exc_info=True)

    coinbase_url = ("https://api.coinbase.com/v2/exchange-rates?currency=BTC")  # type: str
    try:
        coinbase_json = await fetch_single_from_api(coinbase_url, loop=loop)
        all_rates["coinbase"] = coinbase_json
    except Exception as ex:
        logging.error("coinbase call failed with {}".format(ex), exc_info=True)

    bitstamp_url = "https://www.bitstamp.net/api/v2/ticker/"
    try:
        bitstamp_json = await fetch_single_from_api(bitstamp_url, loop=loop)
        all_rates["bitstamp"] = bitstamp_json
    except Exception as ex:
        logging.error("bitstamp call failed with {}".format(ex), exc_info=True)

    res_with_avg_rate = {}
    for SYMBOL in CURRENCIES:
        try:
            all_symbol_rates = []
            try:
                coingecko_rate = all_rates.get("coingecko", {}).get(SYMBOL, None)
                if coingecko_rate:
                    all_symbol_rates.append(float(coingecko_rate))
            except Exception as ex:
                print(ex)
                pass
            try:
                ccomp_rate = all_rates.get("ccomp", {}).get(SYMBOL, None)
                if ccomp_rate:
                    all_symbol_rates.append(float(ccomp_rate))
            except Exception as ex:
                print(ex)
                pass
            try:
                coinbase_rate = all_rates.get("coinbase", {}).get("data", {}).get("rates", {}).get(SYMBOL, None)
                if coinbase_rate:
                    all_symbol_rates.append(float(coinbase_rate))
            except Exception as ex:
                print(ex)
                pass
            try:
                for bitsamp_rate in all_rates.get("bitstamp", []):
                    if bitsamp_rate.get('pair', "") == "BTC/"+SYMBOL:
                        _bitsamp_rate = bitsamp_rate.get('last', None)
                        if _bitsamp_rate:
                            all_symbol_rates.append(float(_bitsamp_rate))
                            break
            except Exception as ex:
                print(ex)
                pass
            avg_rate = 1
            if len(all_symbol_rates):
                try:
                    ans = reject_outliers(all_symbol_rates)
                    avg_rate = sum(ans)/float(len(ans))
                    res_with_avg_rate[SYMBOL] = avg_rate
                except Exception as ex:
                    print(ex)
        except Exception as ex:
            print(ex)
            pass
    return res_with_avg_rate
