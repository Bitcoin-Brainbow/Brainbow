import logging
import asyncio
import json
from typing import Dict, List, Any

from socks_http import urlopen


async def fetch_from_api(url, loop=None) -> Dict[str, Any]:
    ans = json.loads(await urlopen(url, loop=loop))
    print(ans)
    return ans

async def fetch_fee_estimate(loop=None):
    mempool_endpoint = "http://mempoolhqx4isw62xs7abwphsq7ldayuidyx2v2oethdhhj6mlo2r6ad.onion/api/v1/fees/recommended"
    try:
        ans = await fetch_from_api(mempool_endpoint, loop=loop)
        print(ans)
        return ans
    except Exception as ex:
        logging.error("failed to get fee estimate from mempool with {}".format(ex), exc_info=True)
