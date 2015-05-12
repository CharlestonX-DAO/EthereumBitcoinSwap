from ethereum import tester

from bitcoin import *


import pytest
slow = pytest.mark.slow

class TestEthBtcSwap(object):

    CONTRACT = 'ethBtcSwap.py'
    CONTRACT_GAS = 55000

    ETHER = 10 ** 18

    # tx is fff2525b8931402dd09222c50775608f75787bd2b87e56995a7bdd30f79702c4
    # from block100K
    TX_STR = '0100000001032e38e9c0a84c6046d687d10556dcacc41d275ec55fc00779ac88fdf357a187000000008c493046022100c352d3dd993a981beba4a63ad15c209275ca9470abfcd57da93b58e4eb5dce82022100840792bc1f456062819f15d33ee7055cf7b5ee1af1ebcc6028d9cdb1c3af7748014104f46db5e9d61a9dc27b8d64ad23e7383a4e6ca164593c2527c038c0857eb67ee8e825dca65046b82c9331586c82e0fd1f633f25f87c161bc6f8a630121df2b3d3ffffffff0200e32321000000001976a914c398efa9c392ba6013c5e04ee729755ef7f58b3288ac000fe208010000001976a914948c765a6914d43f2a7ac177da2c2f6b52de3d7c88ac00000000'
    TX_HASH = int(dbl_sha256(TX_STR.decode('hex')), 16)


    def setup_class(cls):
        tester.gas_limit = int(2e6)
        cls.s = tester.state()
        cls.c = cls.s.abi_contract(cls.CONTRACT)
        cls.snapshot = cls.s.snapshot()
        cls.seed = tester.seed

    def setup_method(self, method):
        self.s.revert(self.snapshot)
        tester.seed = self.seed


    def testClaimerFee(self):
        # block 300k
        txBlockHash = 0x000000000000000082ccf8f1557c5d40b21edabb18d2d691cfbf87118bac7254
        txStr = '0100000002a0419f78a1ef9441b1d91a5cb3e198d4a1ef8b382cd942de98a58a5f968d073f000000006a473044022032a0332c1afb753afc1bb44555c9ccefa83709ca5e1e62a608024b9cf4c087c002201a506f2c8442c390590769d5cdefc6e4e0e1f8517a060365ec527cc9b749068c012102caa12ebb756b4a3a90c8779d2ec75d7082f9c2897f0715989840f16bf3aa7adfffffffff55ad24bbc9541d9848ad64546ab4a6f4b96cb15043ddeea52fbeb3cc70987340000000008a47304402203d4cb993d6e73979c3aae2d1c4752f6b4c501c4b64fc19f212efaa54a7ba199f02204ba50d8764532c2157f7438cf2eee6e975853975eb3803823f9de4a1c1f230e30141040a424c356d3adfdc6ba29cf41474105434d01a7ad5be3ae6938f8af92da215bdb0e21bd2ad6301f43be02f1ce796229a8c00873356e11a056c8c65f731304a7fffffffff0280ba8c01000000001976a914956bfc5575c0a7134c7effef268e51d887ba701588ac4a480f00000000001976a914587488c119f40666b4a0c807b0d7a1acfe3b691788ac00000000'
        txHash = 0x141e4ea2fa3c9bf9984d03ff081d21555f8ccc7a528326cea96221ca6d476566
        txIndex = 190
        sibling = [0x09636b32593267f1aec7cf7ac36b6a51b8ef158f5648d1d27882492b7908ca2e, 0xe081237dd6f75f2a0b174ac8a8f138fffd4c05ad05c0c12cc1c69a203eec79ae, 0x0c23978510ed856b5e17cba4b4feba7e8596581d604cce84f50b6ea180fd91a4, 0x1f4deef9f140251f6dc011d3b9db88586a2a313de813f803626dcdac4e1e3127, 0x266f31fc4cdca488ecf0f9cbf56e4b25aa5e49154ae192bc6982fc28827cc62b, 0xd394350ece3e0cb705c99c1db14f29d1db0e1a3dcbd3094baf695e297bea0f6b, 0x3a2e3e81c6ef3a3ff65ec6e62ead8eb5c2f8bb950ba2422038fa573a6d638812, 0xaec0b4d49d190f9ac61d0e32443ade724274de466eed4acb0498207664832d84]
        satoshiOutputOne = int(0.26e8)
        satoshiOutputTwo = int(0.01001546e8)

        btcAddr = 0x956bfc5575c0a7134c7effef268e51d887ba7015
        numWei = self.ETHER
        weiPerSatoshi = satoshiOutputOne / numWei  # from tx1  5*10**8 / numWei
        ethAddr = 0x587488c119f40666b4a0c807b0d7a1acfe3b6917

        depositRequired = numWei / 20

        MOCK_VERIFY_TX_ONE = self.s.abi_contract('./test/mockVerifyTxReturnsOne.py')
        self.c.setTrustedBtcRelay(MOCK_VERIFY_TX_ONE.address)

        ticketId = self.c.createTicket(btcAddr, numWei, weiPerSatoshi, value=numWei)
        assert ticketId == 0

        assert 1 == self.c.reserveTicket(ticketId, txHash, value=depositRequired, sender=tester.k1)


        eventArr = []
        self.s.block.log_listeners.append(lambda x: eventArr.append(self.c._translator.listen(x)))


        assert 1 == self.c.claimTicket(ticketId, txStr, txHash, txIndex, sibling, txBlockHash, sender=tester.k1)

        assert eventArr == [{'_event_type': 'claimSuccess', 'numSatoshi': satoshiOutputOne,
            'btcAddr': btcAddr,
            'ethAddr': ethAddr,
            'satoshiIn2ndOutput': satoshiOutputTwo
            }]
        eventArr.pop()


        claimerFeePercent = (satoshiOutputTwo % 10000) / 10000.0
        claimerBalance = self.s.block.get_balance(tester.a1)
        # assert claimerBalance == claimerFeePercent * numWei incorrect since claimer has used up some ether by requesting and claiming ticket

        indexOfBtcAddr = txStr.find(format(btcAddr, 'x'))
        ethAddrBin = txStr[indexOfBtcAddr+68:indexOfBtcAddr+108].decode('hex') # assumes ether addr is after btcAddr
        buyerEthBalance = self.s.block.get_balance(ethAddrBin)
        assert buyerEthBalance == (1 - claimerFeePercent) * numWei



    def testHappy(self):
        btcAddr = 0xc398efa9c392ba6013c5e04ee729755ef7f58b32
        numWei = self.ETHER
        weiPerSatoshi = 2*10**10  # from tx1  5*10**8 / numWei
        depositRequired = numWei / 20

        MOCK_VERIFY_TX_ONE = self.s.abi_contract('./test/mockVerifyTxReturnsOne.py')
        self.c.setTrustedBtcRelay(MOCK_VERIFY_TX_ONE.address)

        ticketId = self.c.createTicket(btcAddr, numWei, weiPerSatoshi, value=numWei)
        assert ticketId == 0

        assert 1 == self.c.reserveTicket(ticketId, self.TX_HASH, value=depositRequired)


        eventArr = []
        self.s.block.log_listeners.append(lambda x: eventArr.append(self.c._translator.listen(x)))


        txIndex = 1
        sibling = [0x8c14f0db3df150123e6f3dbbf30f8b955a8249b62ac1d1ff16284aefa3d06d87, 0x8e30899078ca1813be036a073bbf80b86cdddde1c96e9e9c99e9e3782df4ae49]
        txBlockHash = 0x000000000003ba27aa200b1cecaad478d2b00432346c3f1f3986da1afd33e506

        assert 1 == self.c.claimTicket(ticketId, self.TX_STR, self.TX_HASH, txIndex, sibling, txBlockHash)

        assert eventArr == [{'_event_type': 'claimSuccess', 'numSatoshi': int(5.56e8),
            'btcAddr': btcAddr,
            'ethAddr': 0x948c765a6914d43f2a7ac177da2c2f6b52de3d7c,
            'satoshiIn2ndOutput': int(44.44e8)
            }]
        eventArr.pop()

        MOCK_VERIFY_TX_ZERO = self.s.abi_contract('./test/mockVerifyTxReturnsZero.py')
        self.c.setTrustedBtcRelay(MOCK_VERIFY_TX_ZERO.address)
        assert 0 == self.c.claimTicket(ticketId, self.TX_STR, self.TX_HASH, txIndex, sibling, txBlockHash)


        # print(eventArr)



    def testCreateTicket(self):
        btcAddr = 9
        numWei = self.ETHER
        weiPerSatoshi = 8
        assert -1 == self.c.createTicket(btcAddr, numWei, weiPerSatoshi)

        assert 0 == self.c.createTicket(btcAddr, numWei, weiPerSatoshi, value=numWei)
        assert numWei == self.s.block.get_balance(self.c.address)

        assert 1 == self.c.createTicket(btcAddr, numWei, weiPerSatoshi, value=numWei)
        assert 2*numWei == self.s.block.get_balance(self.c.address)

        txHash = 7
        depositRequired = numWei / 20

        # no deposit
        assert 0 == self.c.reserveTicket(0, txHash)
        assert 0 == self.c.reserveTicket(1, txHash)

        # deposit < required
        assert 0 == self.c.reserveTicket(1, txHash, value=depositRequired - 1)

        # deposit == required
        assert 1 == self.c.reserveTicket(1, txHash, value=depositRequired)

        # deposit > required, need to use unclaimed ticketId0
        assert 1 == self.c.reserveTicket(0, txHash, value=depositRequired + 1)

        # deposit > required, but ticketId1 still reserved
        assert 0 == self.c.reserveTicket(1, txHash, value=depositRequired + 1)

        # deposit == required and previous ticketId1 reservation has expired
        self.s.block.timestamp += 3600 * 5
        assert 1 == self.c.reserveTicket(1, txHash, value=depositRequired)

        # close but not yet expired
        self.s.block.timestamp += 3600 * 4
        assert 0 == self.c.reserveTicket(1, txHash, value=depositRequired)

        # expired reservation can now be reserved
        self.s.block.timestamp += 100
        assert 1 == self.c.reserveTicket(1, txHash, value=depositRequired)


    # testClaimTicketZero
