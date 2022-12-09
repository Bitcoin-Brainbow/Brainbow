import sys
import getpass
import nowallet

if __name__ == "__main__":
    print("\n\tBRAINBOW RECOVERY")
    print("\n\tWARNING: Entering your salt and passphrase will print your 'BIP-32 Root Master Private Key' on the screen.")
    print("")
    ok = input("Type 'ok' to continue: ")
    if ok != "ok":
        print("Okay, 'ok' was not 'ok'. Good bye.")
        sys.exit(1)
    chain = input("Which chain [BTC or TBTC]: ")  # type: str
    if chain.lower().strip() == "btc":
        chain = nowallet.BTC
    else:
        chain = nowallet.TBTC
    email = input("Enter salt: ")  # type: str

    passphrase = getpass.getpass("Enter passphrase: ")  # type: str
    confirm = getpass.getpass("Confirm your passphrase: ")  # type: str
    assert passphrase == confirm, "Passphrase and confirmation did not match"
    assert email and passphrase, "Email and/or passphrase were blank"
    wallet = nowallet.Wallet(email, passphrase, None, None, chain)
    print("\n")
    print("\t{}".format("*"*120))
    print("\n")
    print("\t    WARNING: KEEP THIS KEY SECRET!")
    print("\n")
    print("\t    BIP-32 Root Master Private Key for {}".format(wallet.fingerprint))
    print("\t    {}".format(wallet.private_BIP32_root_key))
    print("\t")
    print("\t{}".format("*"*120))
    print("\n")
