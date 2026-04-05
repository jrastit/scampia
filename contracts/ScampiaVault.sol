// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IENSRegistry {
    function setSubnodeRecord(bytes32 node, bytes32 label, address owner, address resolver, uint64 ttl) external;
}

interface IENSResolver {
    function setAddr(bytes32 node, address a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
}

contract ScampiaVault {
    IERC20 public immutable asset;
    address public admin;
    address public managerRecipient;
    bool public paused;
    uint16 public managerFeeBps;
    uint16 public constant MAX_BPS = 10_000;
    bytes32 private constant ZERO_NODE = bytes32(0);

    mapping(address => bool) public allowedTargets;
    uint256 public vaultCount;
    address public ensRegistry;
    address public ensResolver;
    bytes32 public ensParentNode;

    struct Vault {
        address owner;
        uint16 ownerFeeBps;
        uint256 totalShares;
        uint256 totalAssets;
        bool exists;
    }

    mapping(uint256 => Vault) public vaults;
    mapping(uint256 => mapping(address => uint256)) public userShares;
    mapping(uint256 => mapping(address => uint256)) public userPrincipal;
    mapping(uint256 => bytes32) public vaultEnsNode;
    mapping(uint256 => string) public vaultEnsLabel;
    mapping(bytes32 => uint256) public ensNodeVaultId;

    uint256 private _entered;

    event VaultCreated(uint256 indexed vaultId, address indexed owner, uint16 ownerFeeBps);
    event OwnerFeeUpdated(uint256 indexed vaultId, uint16 ownerFeeBps);
    event Deposited(
        uint256 indexed vaultId,
        address indexed sender,
        address indexed receiver,
        uint256 assets,
        uint256 mintedShares
    );
    event Withdrawn(
        uint256 indexed vaultId,
        address indexed user,
        address indexed receiver,
        uint256 grossAssets,
        uint256 userAssets,
        uint256 ownerFee,
        uint256 managerFee,
        uint256 burnedShares,
        uint256 realizedProfit
    );
    event TargetUpdated(address indexed target, bool allowed);
    event TradeExecuted(
        uint256 indexed vaultId,
        address indexed target,
        int256 assetDelta,
        uint256 beforeBalance,
        uint256 afterBalance,
        bytes data
    );
    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);
    event ManagerRecipientUpdated(address indexed previousRecipient, address indexed newRecipient);
    event ManagerFeeUpdated(uint16 managerFeeBps);
    event PauseUpdated(bool paused);
    event EnsConfigUpdated(address indexed registry, address indexed resolver, bytes32 indexed parentNode);
    event VaultEnsRegistered(uint256 indexed vaultId, bytes32 indexed node, string label);
    event VaultEnsTextUpdated(uint256 indexed vaultId, bytes32 indexed node, string key, string value);

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "paused");
        _;
    }

    modifier nonReentrant() {
        require(_entered == 0, "reentrant");
        _entered = 1;
        _;
        _entered = 0;
    }

    constructor(address assetToken, address initialAdmin, address initialManagerRecipient, uint16 initialManagerFeeBps) {
        require(assetToken != address(0), "asset=0");
        require(initialAdmin != address(0), "admin=0");
        require(initialManagerRecipient != address(0), "manager=0");
        require(initialManagerFeeBps <= MAX_BPS, "manager fee too high");
        asset = IERC20(assetToken);
        admin = initialAdmin;
        managerRecipient = initialManagerRecipient;
        managerFeeBps = initialManagerFeeBps;
        emit AdminTransferred(address(0), initialAdmin);
        emit ManagerRecipientUpdated(address(0), initialManagerRecipient);
        emit ManagerFeeUpdated(initialManagerFeeBps);
    }

    function transferAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "admin=0");
        address previous = admin;
        admin = newAdmin;
        emit AdminTransferred(previous, newAdmin);
    }

    function setManagerRecipient(address newManagerRecipient) external onlyAdmin {
        require(newManagerRecipient != address(0), "manager=0");
        address previous = managerRecipient;
        managerRecipient = newManagerRecipient;
        emit ManagerRecipientUpdated(previous, newManagerRecipient);
    }

    function setManagerFeeBps(uint16 newManagerFeeBps) external onlyAdmin {
        require(newManagerFeeBps <= MAX_BPS, "manager fee too high");
        managerFeeBps = newManagerFeeBps;
        emit ManagerFeeUpdated(newManagerFeeBps);
    }

    function setPaused(bool isPaused) external onlyAdmin {
        paused = isPaused;
        emit PauseUpdated(isPaused);
    }

    function setAllowedTarget(address target, bool allowed) external onlyAdmin {
        require(target != address(0), "target=0");
        allowedTargets[target] = allowed;
        emit TargetUpdated(target, allowed);
    }

    function setEnsConfig(address registry, address resolver, bytes32 parentNode) external onlyAdmin {
        require(registry != address(0), "registry=0");
        require(resolver != address(0), "resolver=0");
        require(parentNode != ZERO_NODE, "parentNode=0");
        ensRegistry = registry;
        ensResolver = resolver;
        ensParentNode = parentNode;
        emit EnsConfigUpdated(registry, resolver, parentNode);
    }

    function createVault(uint16 ownerFeeBps) external whenNotPaused returns (uint256 vaultId) {
        require(ownerFeeBps <= MAX_BPS, "owner fee too high");
        vaultId = ++vaultCount;
        vaults[vaultId] = Vault({
            owner: msg.sender,
            ownerFeeBps: ownerFeeBps,
            totalShares: 0,
            totalAssets: 0,
            exists: true
        });
        emit VaultCreated(vaultId, msg.sender, ownerFeeBps);
    }

    function setVaultOwnerFeeBps(uint256 vaultId, uint16 ownerFeeBps) external whenNotPaused {
        Vault storage v = _vault(vaultId);
        require(msg.sender == v.owner, "not vault owner");
        require(ownerFeeBps <= MAX_BPS, "owner fee too high");
        v.ownerFeeBps = ownerFeeBps;
        emit OwnerFeeUpdated(vaultId, ownerFeeBps);
    }

    function registerVaultEns(uint256 vaultId, string calldata label)
        external
        onlyAdmin
        whenNotPaused
        returns (bytes32 node)
    {
        _vault(vaultId);
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
        IENSResolver(ensResolver).setAddr(node, address(this));

        vaultEnsNode[vaultId] = node;
        vaultEnsLabel[vaultId] = label;
        ensNodeVaultId[node] = vaultId;

        emit VaultEnsRegistered(vaultId, node, label);
    }

    function setVaultEnsText(uint256 vaultId, string calldata key, string calldata value)
        external
        onlyAdmin
        whenNotPaused
    {
        bytes32 node = _vaultEnsNode(vaultId);
        _setVaultEnsText(vaultId, node, key, value);
    }

    function setVaultEnsTexts(
        uint256 vaultId,
        string[] calldata keys,
        string[] calldata values
    ) external onlyAdmin whenNotPaused {
        bytes32 node = _vaultEnsNode(vaultId);
        uint256 length = keys.length;
        require(length == values.length, "length mismatch");

        for (uint256 i = 0; i < length; ++i) {
            _setVaultEnsText(vaultId, node, keys[i], values[i]);
        }
    }

    function deposit(uint256 vaultId, uint256 assets, address receiver)
        external
        whenNotPaused
        nonReentrant
        returns (uint256 mintedShares)
    {
        Vault storage v = _vault(vaultId);
        require(receiver != address(0), "receiver=0");
        require(assets > 0, "assets=0");

        mintedShares = _assetsToShares(v, assets);
        require(mintedShares > 0, "zero shares");

        v.totalShares += mintedShares;
        v.totalAssets += assets;
        userShares[vaultId][receiver] += mintedShares;
        userPrincipal[vaultId][receiver] += assets;

        _safeTransferFrom(address(asset), msg.sender, address(this), assets);

        emit Deposited(vaultId, msg.sender, receiver, assets, mintedShares);
    }

    function withdraw(uint256 vaultId, uint256 burnedShares, address receiver)
        external
        whenNotPaused
        nonReentrant
        returns (uint256 userAssets)
    {
        Vault storage v = _vault(vaultId);
        require(receiver != address(0), "receiver=0");
        require(burnedShares > 0, "shares=0");

        uint256 sharesBefore = userShares[vaultId][msg.sender];
        require(sharesBefore >= burnedShares, "insufficient shares");

        uint256 grossAssets = _sharesToAssets(v, burnedShares);
        require(grossAssets > 0, "assets=0");
        require(v.totalAssets >= grossAssets, "insufficient vault assets");

        uint256 principalBefore = userPrincipal[vaultId][msg.sender];
        uint256 principalReleased = (principalBefore * burnedShares) / sharesBefore;

        userShares[vaultId][msg.sender] = sharesBefore - burnedShares;
        userPrincipal[vaultId][msg.sender] = principalBefore - principalReleased;
        v.totalShares -= burnedShares;
        v.totalAssets -= grossAssets;

        uint256 profit = grossAssets > principalReleased ? grossAssets - principalReleased : 0;
        uint256 ownerFee = 0;
        uint256 managerFee = 0;

        if (msg.sender != v.owner && profit > 0) {
            ownerFee = (profit * v.ownerFeeBps) / MAX_BPS;
            managerFee = (profit * managerFeeBps) / MAX_BPS;
            uint256 totalFee = ownerFee + managerFee;
            if (totalFee > profit) {
                totalFee = profit;
                if (ownerFee > totalFee) {
                    ownerFee = totalFee;
                    managerFee = 0;
                } else {
                    managerFee = totalFee - ownerFee;
                }
            }
        }

        userAssets = grossAssets - ownerFee - managerFee;

        if (ownerFee > 0) {
            _safeTransfer(address(asset), v.owner, ownerFee);
        }
        if (managerFee > 0) {
            _safeTransfer(address(asset), managerRecipient, managerFee);
        }
        _safeTransfer(address(asset), receiver, userAssets);

        emit Withdrawn(
            vaultId,
            msg.sender,
            receiver,
            grossAssets,
            userAssets,
            ownerFee,
            managerFee,
            burnedShares,
            profit
        );
    }

    function executeTrade(
        uint256 vaultId,
        address target,
        uint256 value,
        bytes calldata data,
        int256 minAssetDelta
    ) external onlyAdmin whenNotPaused nonReentrant returns (int256 assetDelta) {
        Vault storage v = _vault(vaultId);
        require(allowedTargets[target], "target not allowed");
        uint256 beforeBal = asset.balanceOf(address(this));
        (bool ok,) = target.call{value: value}(data);
        require(ok, "swap failed");
        uint256 afterBal = asset.balanceOf(address(this));

        if (afterBal >= beforeBal) {
            uint256 gain = afterBal - beforeBal;
            assetDelta = int256(gain);
            v.totalAssets += gain;
        } else {
            uint256 loss = beforeBal - afterBal;
            assetDelta = -int256(loss);
            require(v.totalAssets >= loss, "loss exceeds vault assets");
            v.totalAssets -= loss;
        }

        require(assetDelta >= minAssetDelta, "slippage");

        emit TradeExecuted(vaultId, target, assetDelta, beforeBal, afterBal, data);
    }

    function getUserPosition(uint256 vaultId, address user)
        external
        view
        returns (uint256 shares, uint256 principal, uint256 estimatedAssets)
    {
        Vault storage v = _vault(vaultId);
        shares = userShares[vaultId][user];
        principal = userPrincipal[vaultId][user];
        estimatedAssets = _sharesToAssets(v, shares);
    }

    function previewDeposit(uint256 vaultId, uint256 assets) external view returns (uint256) {
        Vault storage v = _vault(vaultId);
        return _assetsToShares(v, assets);
    }

    function previewWithdraw(uint256 vaultId, uint256 sharesAmount) external view returns (uint256) {
        Vault storage v = _vault(vaultId);
        return _sharesToAssets(v, sharesAmount);
    }

    function getVaultEnsRecord(uint256 vaultId) external view returns (bytes32 node, string memory label) {
        node = vaultEnsNode[vaultId];
        label = vaultEnsLabel[vaultId];
    }

    function _vault(uint256 vaultId) internal view returns (Vault storage v) {
        v = vaults[vaultId];
        require(v.exists, "vault not found");
    }

    function _vaultEnsNode(uint256 vaultId) internal view returns (bytes32 node) {
        _vault(vaultId);
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

    function _assetsToShares(Vault storage v, uint256 assets) internal view returns (uint256) {
        if (v.totalShares == 0 || v.totalAssets == 0) {
            return assets;
        }
        return (assets * v.totalShares) / v.totalAssets;
    }

    function _sharesToAssets(Vault storage v, uint256 sharesAmount) internal view returns (uint256) {
        if (v.totalShares == 0 || v.totalAssets == 0) {
            return sharesAmount;
        }
        return (sharesAmount * v.totalAssets) / v.totalShares;
    }

    function _safeTransfer(address token, address to, uint256 value) internal {
        (bool ok, bytes memory data) = token.call(abi.encodeWithSignature("transfer(address,uint256)", to, value));
        require(ok && (data.length == 0 || abi.decode(data, (bool))), "transfer failed");
    }

    function _safeTransferFrom(address token, address from, address to, uint256 value) internal {
        (bool ok, bytes memory data) = token.call(
            abi.encodeWithSignature("transferFrom(address,address,uint256)", from, to, value)
        );
        require(ok && (data.length == 0 || abi.decode(data, (bool))), "transferFrom failed");
    }

    receive() external payable {}
}
