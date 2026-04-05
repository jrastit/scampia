// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

import {ScampiaVault} from "../contracts/ScampiaVault.sol";
import {ScampiaENSManager} from "../contracts/ScampiaENSManager.sol";
import {MockENSRegistry} from "./mocks/MockENSRegistry.sol";
import {MockENSResolver} from "./mocks/MockENSResolver.sol";
import {MockERC20} from "./mocks/MockERC20.sol";

contract ScampiaENSManagerTest is Test {
    MockERC20 internal token;
    ScampiaVault internal vault;
    ScampiaENSManager internal manager;
    MockENSRegistry internal registry;
    MockENSResolver internal resolver;

    address internal admin = address(0xA11CE);
    address internal owner = address(0xC0DE);
    address internal recoveryOwner = address(0xBEEF);

    function setUp() external {
        vm.startPrank(admin);
        token = new MockERC20();
        vault = new ScampiaVault(address(token), admin, admin, 500);
        manager = new ScampiaENSManager(admin, address(vault));
        registry = new MockENSRegistry();
        resolver = new MockENSResolver();
        vm.stopPrank();
    }

    function _createVault(uint16 ownerFeeBps) internal returns (uint256 vaultId) {
        vm.prank(owner);
        vaultId = vault.createVault(ownerFeeBps);
    }

    function _namehash(string memory name) internal pure returns (bytes32) {
        bytes32 node = bytes32(0);
        string[] memory labels = new string[](2);
        labels[0] = "eth";
        labels[1] = "scampia";
        if (bytes(name).length == 0) {
            return node;
        }
        for (uint256 i = labels.length; i > 0; --i) {
            node = keccak256(abi.encodePacked(node, keccak256(bytes(labels[i - 1]))));
        }
        return node;
    }

    function testRegisterVaultEnsUsesStableManagerOwner() external {
        uint256 vaultId = _createVault(500);
        bytes32 parentNode = _namehash("scampia.eth");

        vm.prank(admin);
        manager.setEnsConfig(address(registry), address(resolver), parentNode, address(vault));

        vm.prank(admin);
        bytes32 node = manager.registerVaultEns(vaultId, "agent-1");

        (bytes32 storedNode, string memory label) = manager.getVaultEnsRecord(vaultId);
        assertEq(storedNode, node);
        assertEq(label, "agent-1");
        assertEq(registry.owner(node), address(manager));
        assertEq(registry.resolver(node), address(resolver));
        assertEq(resolver.addr(node), address(vault));
    }

    function testSetVaultEnsTextsWritesPolicyMetadata() external {
        uint256 vaultId = _createVault(500);
        bytes32 parentNode = _namehash("scampia.eth");

        vm.startPrank(admin);
        manager.setEnsConfig(address(registry), address(resolver), parentNode, address(vault));
        bytes32 node = manager.registerVaultEns(vaultId, "agent-2");

        string[] memory keys = new string[](2);
        string[] memory values = new string[](2);
        keys[0] = "stop_loss_pct";
        values[0] = "30";
        keys[1] = "authorized_tokens";
        values[1] = "[\"ETH\",\"USDC\"]";
        manager.setVaultEnsTexts(vaultId, keys, values);
        vm.stopPrank();

        assertEq(resolver.text(node, "stop_loss_pct"), "30");
        assertEq(resolver.text(node, "authorized_tokens"), "[\"ETH\",\"USDC\"]");
    }

    function testAdminCanTransferParentNodeOwnership() external {
        bytes32 parentNode = _namehash("scampia.eth");

        vm.prank(admin);
        manager.setEnsConfig(address(registry), address(resolver), parentNode, address(vault));

        vm.prank(admin);
        manager.transferParentNodeOwnership(recoveryOwner);

        assertEq(registry.owner(parentNode), recoveryOwner);
    }
}
