// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IENSRegistry {
    function setSubnodeRecord(bytes32 node, bytes32 label, address owner, address resolver, uint64 ttl) external;
    function owner(bytes32 node) external view returns (address);
}

interface IENSResolver {
    function setAddr(bytes32 node, address a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
}

interface IScampiaVault {
    function vaults(uint256 vaultId)
        external
        view
        returns (address owner, uint16 ownerFeeBps, uint256 totalShares, uint256 totalAssets, bool exists);
}

contract ScampiaENSManager {
    address public admin;
    address public vaultContract;
    address public ensRegistry;
    address public ensResolver;
    bytes32 public ensParentNode;
    bytes32 private constant ZERO_NODE = bytes32(0);

    mapping(uint256 => bytes32) public vaultEnsNode;
    mapping(uint256 => string) public vaultEnsLabel;
    mapping(bytes32 => uint256) public ensNodeVaultId;

    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);
    event VaultContractUpdated(address indexed previousVaultContract, address indexed newVaultContract);
    event EnsConfigUpdated(address indexed registry, address indexed resolver, bytes32 indexed parentNode);
    event VaultEnsRegistered(uint256 indexed vaultId, bytes32 indexed node, string label);
    event VaultEnsTextUpdated(uint256 indexed vaultId, bytes32 indexed node, string key, string value);

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    constructor(address initialAdmin, address initialVaultContract) {
        require(initialAdmin != address(0), "admin=0");
        require(initialVaultContract != address(0), "vault=0");
        admin = initialAdmin;
        vaultContract = initialVaultContract;
        emit AdminTransferred(address(0), initialAdmin);
        emit VaultContractUpdated(address(0), initialVaultContract);
    }

    function transferAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "admin=0");
        address previous = admin;
        admin = newAdmin;
        emit AdminTransferred(previous, newAdmin);
    }

    function setVaultContract(address newVaultContract) public onlyAdmin {
        require(newVaultContract != address(0), "vault=0");
        address previous = vaultContract;
        vaultContract = newVaultContract;
        emit VaultContractUpdated(previous, newVaultContract);
    }

    function setEnsConfig(address registry, address resolver, bytes32 parentNode, address newVaultContract) external onlyAdmin {
        require(registry != address(0), "registry=0");
        require(resolver != address(0), "resolver=0");
        require(parentNode != ZERO_NODE, "parentNode=0");
        ensRegistry = registry;
        ensResolver = resolver;
        ensParentNode = parentNode;
        if (newVaultContract != vaultContract) {
            setVaultContract(newVaultContract);
        } else {
            require(newVaultContract != address(0), "vault=0");
        }
        emit EnsConfigUpdated(registry, resolver, parentNode);
    }

    function registerVaultEns(uint256 vaultId, string calldata label) external onlyAdmin returns (bytes32 node) {
        _requireVaultExists(vaultId);
        _requireEnsConfig();
        require(bytes(label).length != 0, "label=0");
        require(vaultEnsNode[vaultId] == ZERO_NODE, "ens already set");

        bytes32 labelHash = keccak256(bytes(label));
        node = keccak256(abi.encodePacked(ensParentNode, labelHash));
        require(ensNodeVaultId[node] == 0, "ens label used");

        IENSRegistry(ensRegistry).setSubnodeRecord(
            ensParentNode,
            labelHash,
            address(this),
            ensResolver,
            0
        );
        IENSResolver(ensResolver).setAddr(node, vaultContract);

        vaultEnsNode[vaultId] = node;
        vaultEnsLabel[vaultId] = label;
        ensNodeVaultId[node] = vaultId;

        emit VaultEnsRegistered(vaultId, node, label);
    }

    function setVaultEnsText(uint256 vaultId, string calldata key, string calldata value) external onlyAdmin {
        bytes32 node = _vaultEnsNode(vaultId);
        _setVaultEnsText(vaultId, node, key, value);
    }

    function setVaultEnsTexts(
        uint256 vaultId,
        string[] calldata keys,
        string[] calldata values
    ) external onlyAdmin {
        bytes32 node = _vaultEnsNode(vaultId);
        uint256 length = keys.length;
        require(length == values.length, "length mismatch");

        for (uint256 i = 0; i < length; ++i) {
            _setVaultEnsText(vaultId, node, keys[i], values[i]);
        }
    }

    function getVaultEnsRecord(uint256 vaultId) external view returns (bytes32 node, string memory label) {
        node = vaultEnsNode[vaultId];
        label = vaultEnsLabel[vaultId];
    }

    function _requireVaultExists(uint256 vaultId) internal view {
        (, , , , bool exists) = IScampiaVault(vaultContract).vaults(vaultId);
        require(exists, "vault not found");
    }

    function _vaultEnsNode(uint256 vaultId) internal view returns (bytes32 node) {
        _requireVaultExists(vaultId);
        node = vaultEnsNode[vaultId];
        require(node != ZERO_NODE, "ens not set");
    }

    function _requireEnsConfig() internal view {
        require(ensRegistry != address(0), "ens registry=0");
        require(ensResolver != address(0), "ens resolver=0");
        require(ensParentNode != ZERO_NODE, "ens parent=0");
    }

    function _setVaultEnsText(uint256 vaultId, bytes32 node, string calldata key, string calldata value) internal {
        require(bytes(key).length != 0, "key=0");
        IENSResolver(ensResolver).setText(node, key, value);
        emit VaultEnsTextUpdated(vaultId, node, key, value);
    }
}
