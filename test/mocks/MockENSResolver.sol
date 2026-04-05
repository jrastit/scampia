// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockENSResolver {
    mapping(bytes32 => address) public addrRecords;
    mapping(bytes32 => mapping(string => string)) public textRecords;

    function setAddr(bytes32 node, address a) external {
        addrRecords[node] = a;
    }

    function setText(bytes32 node, string calldata key, string calldata value) external {
        textRecords[node][key] = value;
    }

    function addr(bytes32 node) external view returns (address) {
        return addrRecords[node];
    }

    function text(bytes32 node, string calldata key) external view returns (string memory) {
        return textRecords[node][key];
    }
}
