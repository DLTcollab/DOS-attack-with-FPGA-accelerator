# -*- coding: utf-8 -*-
import subprocess
import json
import time

import iota
from iota import Iota, Address, TryteString, Transaction
from iota.crypto.signing import SignatureFragmentGenerator
from iota.crypto.kerl.conv import convertToBytes, convertToTrits, \
    trits_to_trytes, trytes_to_trits

from config import *
from PoW import *

DCURL_PATH = "./dcurl/build/libdcurl.so"
TXN_SECURITY_LEVEL = 2
DEPTH = 7
MWM = 14

api = Iota(node[0], seed=SEED)


def insert_to_trytes(index_start, index_end, str_insert, trytes):
    trytes = trytes[:index_start] + str_insert + trytes[index_end:]

    return trytes





def send_transfer(tag, messages, address, values, dict_tips, debug=0):
    # Initialize PoW Library
    PoWlib = PoW_load_library(DCURL_PATH)
    PoW_interface_init(PoWlib)

    # Set output transaction
    print("Start to transfer ... ")
    time_start_send = time.time()

    propose_bundle = iota.ProposedBundle()

    print("Setting output transaction ...")
    txn_output = iota.ProposedTransaction(
        address=iota.Address(address),
        value=values,
        tag=iota.Tag(tag),
        message=TryteString.from_string(messages)
    )

    propose_bundle.add_transaction(txn_output)

    # Get input address
    if int(values) > 0:
        print("DEBUG values = %s" % (str(values)))

        print("Checking input balance ...")

        dict_inputs = api.get_inputs()
        if int(dict_inputs['totalBalance']) < int(values):
            print("Balance not enough")
            return 0

    # Setting intput transaction
    if int(values) > 0:
        print("Setting input transaction ...")
        value_input = 0
        index_input = 0
        while (int(value_input) < int(values)):
            addy = iota.Address(dict_inputs['inputs'][index_input])
            addy.balance = dict_inputs['inputs'][index_input].balance
            addy.key_index = 1
            addy.security_level = TXN_SECURITY_LEVEL

            propose_bundle.add_inputs([addy])
            value_input = value_input + int(dict_inputs['inputs'][0].balance)

        # Send unspent inputs to
        print("Setting unspent input to a new address ...")
        unspent = iota.Address(generate_address()['addresses'][0])
        propose_bundle.send_unspent_inputs_to(unspent)

    # This will get the bundle hash
    print("Bundle finalize ...")

    time_start_bundle_finz = time.time()
    propose_bundle.finalize()
    time_end_bundle_finz = time.time()
    elapsed_bundle_finz = time_end_bundle_finz - time_start_bundle_finz

    # Signing
    # If the transaction need sign, it will then sign-up the transaction
    # to fill up signature fragements
    if int(values) > 0:
        print("Signing...")
        propose_bundle.sign_inputs(iota.crypto.signing.KeyGenerator(SEED))

    trytes = propose_bundle.as_tryte_strings()

    # Get tips by getTransactionsToApprove
    trunk_hash = dict_tips['branchTransaction']
    branch_hash = dict_tips['trunkTransaction']

    # Do PoW (attach to tangle)
    elapsed_pow = 0
    time_start_pow = time.time()
    for tx_tryte in trytes:
        # TODO: Timestamp
        # timestamp = None
        # timestamp_lower_bound = None
        # timestamp_upper_bound = None

        # Tips insert - trunk
        tx_tryte = insert_to_trytes(2430, 2511, str(trunk_hash), tx_tryte)
        # Tips insert - branch
        tx_tryte = insert_to_trytes(2511, 2592, str(branch_hash), tx_tryte)

        # Do PoW for this transaction
        print("Do POW for this transaction ...")

        nonce = PoW_interface_search(PoWlib, tx_tryte, MWM)
        tx_tryte = insert_to_trytes(2646, 2673, str(nonce), tx_tryte)

        time_end_pow = time.time()
        elapsed_pow = elapsed_pow + (time_end_pow - time_start_pow)

        print("Prepare to broadcast ...")
        try:
            api.broadcast_transactions([tx_tryte[0:2673]])
        except Exception as e:
            print("Error: %s" % (str(e.context)))

    time_end_send = time.time()
    elapsed_send = time_end_send - time_start_send

    if debug == 1:
        data = [{'platform': 'pi3', 'total_time': str(elapsed_send), 'elapsed_pow': str(
            elapsed_pow), 'elqpsed_bundle_finished': str(elapsed_bundle_finz)}]
        json_data = json.dumps(data)
        print(json_data)

#        attach_debug_message_to_tangle(json_data)
    obj_txn = api.find_transactions(bundles=[propose_bundle.hash])
    return 0



def find_transactions_by_tag(data):

    try:
        list_result = api.find_transactions(tags=[data])
    except BaseException:
        return []

    return list_result


def get_txn_msg(data):
    message = ""
    list_txn = []

    try:
        list_txn = api.get_trytes([data])
    except BaseException:
        return ""

    trytes_txn = str(list_txn['trytes'][0])
    txn = Transaction.from_tryte_string(trytes_txn)

    try:
        message = TryteString(txn.signature_message_fragment).as_string()
    except BaseException:
        return ""

    return message


def getReferenceTips(node,currentList):

    """

    """

    tipSet = []

    while currentList != []:


        for transactionHash in currentList:

            print("transactionHash:")
            print(transactionHash)

            checkResult = node.find_transactions(approvees=[transactionHash])



            if checkResult['hashes'] == []:

                tipSet.append(transactionHash)

        currentList = node.find_transactions(approvees=currentList)['hashes']

    return tipSet
