// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract ScampiaVault {
    IERC20 public immutable asset;
    address public owner;
    bool public paused;

    mapping(address => bool) public agents;
    mapping(address => bool) public allowedTargets;

    mapping(address => uint256) public shares;
    uint256 public totalShares;

    event Deposited(address indexed sender, address indexed receiver, uint256 assets, uint256 mintedShares);
    event Withdrawn(address indexed owner, address indexed receiver, uint256 assets, uint256 burnedShares);
    event AgentUpdated(address indexed agent, bool allowed);
    event TargetUpdated(address indexed target, bool allowed);
    event SwapExecuted(
        address indexed agent,
        address indexed target,
        address indexed tokenOut,
        uint256 tokenOutAmount,
        bytes data
    );
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event PauseUpdated(bool paused);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyAgent() {
        require(agents[msg.sender], "not agent");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "paused");
        _;
    }

    constructor(address assetToken, address initialOwner) {
        require(assetToken != address(0), "asset=0");
        require(initialOwner != address(0), "owner=0");
        asset = IERC20(assetToken);
        owner = initialOwner;
        emit OwnershipTransferred(address(0), initialOwner);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "owner=0");
        address previous = owner;
        owner = newOwner;
        emit OwnershipTransferred(previous, newOwner);
    }

    function setPaused(bool isPaused) external onlyOwner {
        paused = isPaused;
        emit PauseUpdated(isPaused);
    }

    function setAgent(address agent, bool allowed) external onlyOwner {
        require(agent != address(0), "agent=0");
        agents[agent] = allowed;
        emit AgentUpdated(agent, allowed);
    }

    function setAllowedTarget(address target, bool allowed) external onlyOwner {
        require(target != address(0), "target=0");
        allowedTargets[target] = allowed;
        emit TargetUpdated(target, allowed);
    }

    function deposit(uint256 assets, address receiver) external whenNotPaused returns (uint256 mintedShares) {
        require(receiver != address(0), "receiver=0");
        require(assets > 0, "assets=0");

        mintedShares = assets;
        require(asset.transferFrom(msg.sender, address(this), assets), "transferFrom failed");

        shares[receiver] += mintedShares;
        totalShares += mintedShares;

        emit Deposited(msg.sender, receiver, assets, mintedShares);
    }

    function withdraw(uint256 assets, address receiver) external whenNotPaused returns (uint256 burnedShares) {
        require(receiver != address(0), "receiver=0");
        require(assets > 0, "assets=0");

        burnedShares = assets;
        require(shares[msg.sender] >= burnedShares, "insufficient shares");

        shares[msg.sender] -= burnedShares;
        totalShares -= burnedShares;

        require(asset.transfer(receiver, assets), "transfer failed");

        emit Withdrawn(msg.sender, receiver, assets, burnedShares);
    }

    function executeSwap(
        address target,
        uint256 value,
        bytes calldata data,
        address tokenOut,
        uint256 minTokenOut
    ) external onlyAgent whenNotPaused returns (uint256 tokenOutAmount) {
        require(allowedTargets[target], "target not allowed");
        require(tokenOut != address(0), "tokenOut=0");

        uint256 beforeBal = IERC20(tokenOut).balanceOf(address(this));
        (bool ok,) = target.call{value: value}(data);
        require(ok, "swap failed");

        uint256 afterBal = IERC20(tokenOut).balanceOf(address(this));
        tokenOutAmount = afterBal - beforeBal;
        require(tokenOutAmount >= minTokenOut, "slippage");

        emit SwapExecuted(msg.sender, target, tokenOut, tokenOutAmount, data);
    }

    receive() external payable {}
}
