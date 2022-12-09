import math
import re

def entropy_bits(passphrase):
    """
    Ref: https://www.omnicalculator.com/other/password-entropy
    Check: https://timcutting.co.uk/tools/password-entropy
    """
    pool_size = 0

    policies = {'Uppercase characters': 0,
                'Lowercase characters': 0,
                'Special characters': 0,
                'Numbers': 0}

    entropies = {'Uppercase characters': 26,
                 'Lowercase characters': 26,
                 'Special characters': 32, # or more ...
                 'Numbers': 10 }

    passphrase_len = len(passphrase)

    for char in passphrase:
        if re.match("[0-9]", char):
            policies["Numbers"] += 1
        elif re.match("[a-z]", char):
            policies["Lowercase characters"] += 1
        elif re.match("[A-Z]", char):
            policies["Uppercase characters"] += 1
        else: # elif re.match("[\[\] !\"#$%&'()*+,-./:;<=>?@\\^_`{|}~]", char): # This regex can be used, but everything else should be considered special char
            policies["Special characters"] += 1
    del passphrase # Remove passphrase from memory

    for policy in policies.keys():
        if policies[policy] > 0:
            pool_size += entropies[policy]
    return math.log2(math.pow(pool_size, passphrase_len))
