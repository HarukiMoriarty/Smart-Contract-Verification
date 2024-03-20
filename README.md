# Formal verification of Smart Contract

*Proving the safety of smart contracts, using the Z3 Theorem Prover*

## Acknowledgement

This repo is based on Zellic weth (https://github.com/Zellic/weth), thanks for their brilliant work!

## Abstract

Smart contracts are self-executing contracts with the terms of the agreement directly written into code. They run on blockchain platforms. These contracts 	automatically execute, control, or document legally relevant events according to a contract or an agreement's terms. Like any software, smart contracts can contain vulnerabilities. These vulnerabilities can lead to significant financial losses, especially given blockchain's decentralized and immutable nature.

Using BMC in smart contract analysis aims to identify transaction sequences that could trigger vulnerabilities. This involves simulating various inputs and states the contract could encounter in the real world.

## Contents of this repository

### WETH 9

We prove two critical invariants: (1) correctness of accounting, and (2) solvency. For accounting, we prove that the total supply of WETH is always equal to its balance of native Ether. For solvency, we prove that, regardless of other users’ actions, a user is always able to unstake Wrapped ETH. In the process, we also identified a minor, harmless bug in the contract. Our work enables the community to continue using WETH with increased confidence in its correctness.

* horn.py: proof for invariant 1 (totalSupply never below total WETH issued)
* bmc.py: proof for invariant 2 (solvency)

### ERC20 - 11nrvbusd

Bug: 2021.6.22 Incorrect logic flow

```c++
function emergencyBurn() public {
    uint balan = balanceOf(msg.sender);
    uint avai = available();
    if(avai<balan) IMasterMind(mastermind).withdraw(nrvPid, (balan.sub(avai)));
    // vlunerable point: loss of 11nrvbusd _burn
    token.safeTransfer(msg.sender, balan);
    emit Withdrawn(msg.sender, balan, block.number);
}
```

We prove one critical invariants: the total balance of 11nrcbusd is always equal to the actual ERC20 token stored in the smart contract.

* emergencyBurn.py: totalBalanceOf11nrvbusd equal to ERC20 in smart contract

## License

See LICENSE.
