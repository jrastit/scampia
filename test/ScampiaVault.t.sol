// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

import {ScampiaVault} from "../contracts/ScampiaVault.sol";
import {MockERC20} from "./mocks/MockERC20.sol";
import {MockENSRegistry} from "./mocks/MockENSRegistry.sol";
import {MockENSResolver} from "./mocks/MockENSResolver.sol";
import {MockTarget} from "./mocks/MockTarget.sol";

contract ScampiaVaultTest is Test {
    MockERC20 internal token;
    ScampiaVault internal vault;
    MockTarget internal target;
    MockENSRegistry internal registry;
    MockENSResolver internal resolver;

    address internal admin = address(0xA11CE);
    address internal manager = address(0xB0B);
    address internal owner = address(0xC0DE);
    address internal alice = address(0xD00D);

    function setUp() external {
        vm.startPrank(admin);
        token = new MockERC20();
        vault = new ScampiaVault(address(token), admin, manager, 500); // 5%
        target = new MockTarget();
        registry = new MockENSRegistry();
        resolver = new MockENSResolver();
        vault.setAllowedTarget(address(target), true);
        vm.stopPrank();

        token.mint(owner, 1_000_000e18);
        token.mint(alice, 1_000_000e18);
        token.mint(address(target), 1_000_000e18);
    }

    function _createVault(uint16 ownerFeeBps) internal returns (uint256 vaultId) {
        vm.prank(owner);
        vaultId = vault.createVault(ownerFeeBps);
    }

    function _namehash(string memory parent, string memory label) internal pure returns (bytes32) {
        bytes32 parentNode = keccak256(abi.encodePacked(bytes32(0), keccak256(bytes(parent))));
        return keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
    }

    function testCreateDepositWithdrawOwnerNoFee() external {
        uint256 vaultId = _createVault(2000); // 20%

        vm.startPrank(owner);
        token.approve(address(vault), 1000e18);
        vault.deposit(vaultId, 1000e18, owner);
        uint256 ownerBalBefore = token.balanceOf(owner);
        vault.withdraw(vaultId, 1000e18, owner);
        uint256 ownerBalAfter = token.balanceOf(owner);
        vm.stopPrank();

        assertEq(ownerBalAfter - ownerBalBefore, 1000e18);
    }

    function testNonOwnerWithdrawPaysOwnerAndManagerFeesOnProfit() external {
        uint256 vaultId = _createVault(2000); // owner 20% on profit

        vm.startPrank(alice);
        token.approve(address(vault), 1000e18);
        vault.deposit(vaultId, 1000e18, alice);
        vm.stopPrank();

        // Simulate vault profit of +500 assets using the admin trading path.
        bytes memory data = abi.encodeWithSelector(
            MockTarget.donate.selector,
            address(token),
            address(vault),
            500e18
        );
        vm.prank(admin);
        vault.executeTrade(vaultId, address(target), 0, data, 0);

        uint256 ownerBefore = token.balanceOf(owner);
        uint256 managerBefore = token.balanceOf(manager);
        uint256 aliceBefore = token.balanceOf(alice);

        vm.prank(alice);
        vault.withdraw(vaultId, 1000e18, alice);

        uint256 ownerDelta = token.balanceOf(owner) - ownerBefore;
        uint256 managerDelta = token.balanceOf(manager) - managerBefore;
        uint256 aliceDelta = token.balanceOf(alice) - aliceBefore;

        // Profit = 500; owner fee 20% => 100; manager fee 5% => 25.
        assertEq(ownerDelta, 100e18);
        assertEq(managerDelta, 25e18);
        assertEq(aliceDelta, 1375e18);
    }

    function testOnlyAdminCanExecuteTrade() external {
        uint256 vaultId = _createVault(500);
        bytes memory data = abi.encodeWithSelector(
            MockTarget.donate.selector,
            address(token),
            address(vault),
            1e18
        );

        vm.expectRevert("not admin");
        vm.prank(alice);
        vault.executeTrade(vaultId, address(target), 0, data, 0);
    }

    function testRegisterVaultEnsSetsContractOwnedProfile() external {
        uint256 vaultId = _createVault(500);
        bytes32 parentNode = _namehash("eth", "scampia");

        vm.prank(admin);
        vault.setEnsConfig(address(registry), address(resolver), parentNode);

        vm.prank(admin);
        bytes32 node = vault.registerVaultEns(vaultId, "agent-1");

        (bytes32 storedNode, string memory label) = vault.getVaultEnsRecord(vaultId);

        assertEq(storedNode, node);
        assertEq(label, "agent-1");
        assertEq(registry.owner(node), address(vault));
        assertEq(registry.resolver(node), address(resolver));
        assertEq(resolver.addr(node), address(vault));
    }

    function testSetVaultEnsTextsWritesPolicyMetadata() external {
        uint256 vaultId = _createVault(500);
        bytes32 parentNode = _namehash("eth", "scampia");

        vm.startPrank(admin);
        vault.setEnsConfig(address(registry), address(resolver), parentNode);
        bytes32 node = vault.registerVaultEns(vaultId, "agent-2");

        string[] memory keys = new string[](2);
        string[] memory values = new string[](2);
        keys[0] = "stop_loss_pct";
        values[0] = "30";
        keys[1] = "authorized_tokens";
        values[1] = "[\"ETH\",\"USDC\"]";
        vault.setVaultEnsTexts(vaultId, keys, values);
        vm.stopPrank();

        assertEq(resolver.text(node, "stop_loss_pct"), "30");
        assertEq(resolver.text(node, "authorized_tokens"), "[\"ETH\",\"USDC\"]");
    }
}
