class AIOHTTPRecipe(CythonRecipe):  # type: ignore # pylint: disable=R0903
    """Build AIOHTTP"""

    version = "v3.8.3"
    url = "https://github.com/aio-libs/aiohttp/archive/{version}.zip"
    name = "aiohttp"
