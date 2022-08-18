from typing import TYPE_CHECKING, Optional
from eth_account.account import Account as EthAccount
from cfx_address.utils import validate_network_id
from cfx_account.signers.local import LocalAccount
from eth_utils.decorators import (
    combomethod,
)
from eth_utils.crypto import (
    keccak,
)
from collections.abc import (
    Mapping,
)
from cytoolz import (
    dissoc, # type: ignore
)
from hexbytes import (
    HexBytes,
)
from eth_account.datastructures import (
    # SignedMessage,
    SignedTransaction,
)
from cfx_account._utils.signing import (
    sign_transaction_dict,
)
from cfx_account._utils.transactions import (
    Transaction,
    vrs_from,
)
from cfx_address import (
    Base32Address,
    eth_eoa_address_to_cfx_hex
)

if TYPE_CHECKING:
    from conflux_web3 import Web3

class Account(EthAccount):
    
    # _default_network_id: Optional[int]=None
    _w3: Optional["Web3"] = None 
    
    @combomethod
    def set_w3(self, w3: "Web3"):
        self._w3 = w3
    
    # def set_default_network_id(self, network_id: int):
    #     self._default_network_id = network_id

    @combomethod
    def from_key(self, private_key: str, network_id: Optional[int]=None) -> LocalAccount:
        """
        returns a LocalAccount object

        :param str private_key: the raw private key
        :param Optional[int] network_id: target network of the account, defaults to None
        :return LocalAccount: object with methods for signing and encrypting

        >>> acct = Account.from_key(
        ... 0xb25c7db31feed9122727bf0939dc769a96564b2de4c4726d035b36ecf1e5b364)
        >>> acct.address
        '0x1ce9454909639d2d17a3f753ce7d93fa0b9ab12e'
        >>> acct.key
        HexBytes('0xb25c7db31feed9122727bf0939dc769a96564b2de4c4726d035b36ecf1e5b364')

        # These methods are also available: sign_message(), sign_transaction(), encrypt()
        # They correspond to the same-named methods in Account.*
        # but without the private key argument
        """
        key = self._parsePrivateKey(private_key)
        if network_id is not None:
            validate_network_id(network_id)
            return LocalAccount(key, self, network_id)
        if self._w3:
            w3_network_id = self._w3.cfx.chain_id
            return LocalAccount(key, self, w3_network_id)
        return LocalAccount(key, self)

    @combomethod
    def sign_transaction(self, transaction_dict, private_key):
        """
        Sign a transaction using a local private key. Produces signature details
        and the hex-encoded transaction suitable for broadcast using
        :meth:`w3.eth.sendRawTransaction() <web3.eth.Eth.sendRawTransaction>`.

        Create the transaction dict for a contract method with
        `my_contract.functions.my_function().buildTransaction()
        <http://web3py.readthedocs.io/en/latest/contracts.html#methods>`_

        :param dict transaction_dict: the transaction with keys:
          nonce, chainId, to, data, value, gas, and gasPrice.
        :param private_key: the private key to sign the data with
        :type private_key: hex str, bytes, int or :class:`eth_keys.datatypes.PrivateKey`
        :returns: Various details about the signature - most
          importantly the fields: v, r, and s
        :rtype: AttributeDict

        .. code-block:: python

            >>> transaction = {
                    # Note that the address must be in checksum format or native bytes:
                    'to': '0xF0109fC8DF283027b6285cc889F5aA624EaC1F55',
                    'value': 1000000000,
                    'gas': 2000000,
                    'gasPrice': 234567897654321,
                    'nonce': 0,
                    'chainId': 1
                }
            >>> key = '0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318'
            >>> signed = Account.sign_transaction(transaction, key)
            {'hash': HexBytes('0x6893a6ee8df79b0f5d64a180cd1ef35d030f3e296a5361cf04d02ce720d32ec5'),
             'r': 4487286261793418179817841024889747115779324305375823110249149479905075174044,
             'rawTransaction': HexBytes('0xf86a8086d55698372431831e848094f0109fc8df283027b6285cc889f5aa624eac1f55843b9aca008025a009ebb6ca057a0535d6186462bc0b465b561c94a295bdb0621fc19208ab149a9ca0440ffd775ce91a833ab410777204d5341a6f9fa91216a6f3ee2c051fea6a0428'),  # noqa: E501
             's': 30785525769477805655994251009256770582792548537338581640010273753578382951464,
             'v': 37}
            >>> w3.eth.sendRawTransaction(signed.rawTransaction)
        """
        if not isinstance(transaction_dict, Mapping):
            raise TypeError("transaction_dict must be dict-like, got %r" % transaction_dict)

        account: LocalAccount = self.from_key(private_key)

        # allow from field, *only* if it matches the private key
        if 'from' in transaction_dict:
            if Base32Address(transaction_dict['from']).hex_address == account.hex_address:
                sanitized_transaction = dissoc(transaction_dict, 'from')
            else:
                raise ValueError("transaction[from] does match key's hex address: "
                    f"from's hex address is{Base32Address(transaction_dict['from']).hex_address}, "
                    f"key's hex address is {account.hex_address}")
                
        else:
            sanitized_transaction = transaction_dict

        # sign transaction
        (
            v,
            r,
            s,
            rlp_encoded,
        ) = sign_transaction_dict(account._key_obj, sanitized_transaction)

        transaction_hash = keccak(rlp_encoded)

        return SignedTransaction(
            rawTransaction=HexBytes(rlp_encoded),
            hash=HexBytes(transaction_hash),
            r=r,
            s=s,
            v=v,
        )

    @combomethod
    def recover_transaction(self, serialized_transaction):
        """
        Get the address of the account that signed this transaction.

        :param serialized_transaction: the complete signed transaction
        :type serialized_transaction: hex str, bytes or int
        :returns: address of signer, hex-encoded & checksummed
        :rtype: str

        .. doctest:: python

            >>> raw_transaction = '0xf86a8086d55698372431831e848094f0109fc8df283027b6285cc889f5aa624eac1f55843b9aca008025a009ebb6ca057a0535d6186462bc0b465b561c94a295bdb0621fc19208ab149a9ca0440ffd775ce91a833ab410777204d5341a6f9fa91216a6f3ee2c051fea6a0428'  # noqa: E501
            >>> Account.recover_transaction(raw_transaction)
            '0x1c7536e3605d9c16a7a3d7b1898e529396a65c23'
        """
        txn_bytes = HexBytes(serialized_transaction)
        txn = Transaction.from_bytes(txn_bytes)
        recovered_address = self._recover_hash(txn[0].hash(), vrs=vrs_from(txn)) # type: ignore
        return eth_eoa_address_to_cfx_hex(recovered_address)