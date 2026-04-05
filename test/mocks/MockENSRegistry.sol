// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockENSRegistry {
    struct Record {
        address owner;
        address resolver;
        uint64 ttl;
    }

    mapping(bytes32 => Record) public records;

    function setSubnodeRecord(
        bytes32 node,
        bytes32 label,
        address recordOwner,
        address recordResolver,
        uint64 ttl
    ) external {
        bytes32 subnode = keccak256(abi.encodePacked(node, label));
        records[subnode] = Record({owner: recordOwner, resolver: recordResolver, ttl: ttl});
    }

    function setOwner(bytes32 node, address newOwner) external {
        records[node].owner = newOwner;
    }

    function owner(bytes32 node) external view returns (address) {
        return records[node].owner;
    }

    function resolver(bytes32 node) external view returns (address) {
        return records[node].resolver;
    }
}
