import os
import sys
import subprocess
import re
import logging
import json
import argparse

# Create logger: https://docs.python.org/3/howto/logging.html#configuring-logging
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
logger.addHandler(ch)
formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)

# hit counter
hits = 0

# mode
transform = False
decode = False

# Prefix
prefix = os.getenv('PREFIX',"vault:fpe:")

# Encode command
encode_cmd = os.getenv('ENCODE_CMD',"vault write -format=json transform/encode/local value={0} transformation=azure")

# Decode command
decode_cmd = os.getenv('DECODE_CMD',"vault write -format=json transform/decode/local value={0} transformation=azure")

# search regex for Azure
regex = os.getenv('REGEX',default="([a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)")

def main():
    global logger
    global transform
    global decode
    
    # Process arguments
    parser = argparse.ArgumentParser(description='Encode or Decode using HashiCorp vault transform secrets engine.')
    parser.add_argument("-v", "--verbose", help="Enable verbose logging", action="store_true")
    parser.add_argument("-d", "--decode", help="Decodes previously tansformed input", action="store_true")
    parser.add_argument("-t", "--transform", help="Transforms from stdin", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.decode:
        decode = True
        logger.debug("Enabled decode")
    else:
        if args.transform:
            transform = True
            logger.debug("Enabled transform")
        else:
            logger.debug("Enabled masking")

    global hits
    input_str = sys.stdin.read()
    if not decode:
        s = re.sub(regex,encode_str,input_str) # Encode
        logger.debug("Encoded %d times" % hits)
    else:
        global prefix
        s1 = input_str.replace(prefix,'') # Remove prefix
        s = re.sub(regex,decode_str,s1) # Decode
        logger.debug("Decoded %d times" % hits)
            
    print(s)

def encode_str(m):
    global logger
    global hits
    global transform
    global prefix
    hits += 1

    # m.group(0) should contain the value to be encoded
    value = m.group(0)

    # Create masked value
    l = ['#' for i in range(len(value))]
    v = ''.join(l)

    if transform:
        cmd = encode_cmd.format(value)
        logger.debug(encode_cmd.format('{masked}'))
    
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = process.communicate()
        error = False;
    
        if process.returncode == 0:
            j = json.loads(stdout)
            if "data" in j and "encoded_value" in j["data"]:
                v = j["data"]["encoded_value"]
            else:
                error = True
                logger.error('Unexpected output from vault %s' % j)            
        else:
            error = True
            logger.error('Received errors from command %s: %s' % (cmd, stderr))

        if error:
            logger.warning('Defaulting to masking')


    v = '{}{}'.format(prefix,v)
    return v

def decode_str(m):
    global logger
    global hits
    global transform
    hits += 1

    # m.group(0) should contain the value to be decoded
    value = m.group(0)

    cmd = decode_cmd.format(value)
    logger.debug(decode_cmd.format(value))
    
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()
    error = False;
    
    if process.returncode == 0:
        j = json.loads(stdout)
        if "data" in j and "decoded_value" in j["data"]:
            v = j["data"]["decoded_value"]
        else:
            error = True
            logger.error('Unexpected output from vault %s' % j)            
    else:
        error = True
        logger.error('Received errors from command %s: %s' % (cmd, stderr))

            
    if error:
        logger.warning('Could not decode, returning original string')
        v = value

    return v


if __name__ == '__main__':
    main()
