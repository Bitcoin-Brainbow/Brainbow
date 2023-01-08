import json
import ssl
import time
from nostr.event import Event
from nostr.relay_manager import RelayManager
from nostr.message_type import ClientMessageType
from nostr.key import PrivateKey

def pub_addr(addr):
    """ nostr1 : test """
    relay_manager = RelayManager()
    relay_manager.add_relay("wss://nostr-pub.wellorder.net")
    relay_manager.add_relay("wss://relay.damus.io")
    relay_manager.add_relay("wss://brb.io")
    relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE}) # NOTE: This disables ssl certificate verification
    time.sleep(1.25) # allow the connections to open

    private_key = PrivateKey()
    public_key = private_key.public_key

    print(f"Private key: {private_key.bech32()}")
    print(f"Public key: {public_key.bech32()}")


    event = Event(private_key.public_key.hex(), "Hello Nostr, my (testnet) address is: {}\n\nSend me some testnet sats if you see this message. Thanks.".format(addr))
    event.sign(private_key.hex())

    message = json.dumps([ClientMessageType.EVENT, event.to_json_object()])
    relay_manager.publish_message(message)
    time.sleep(1) # allow the messages to send

    relay_manager.close_connections()
