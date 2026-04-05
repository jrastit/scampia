// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IToken {
    function transfer(address to, uint256 value) external returns (bool);
}

contract MockTarget {
    function donate(address token, address to, uint256 amount) external {
        IToken(token).transfer(to, amount);
    }

    function donateNative(address payable to) external payable {
        (bool ok,) = to.call{value: msg.value}("");
        require(ok, "native send failed");
    }

    function donateNativeFromBalance(address payable to, uint256 amount) external {
        (bool ok,) = to.call{value: amount}("");
        require(ok, "native send failed");
    }

    receive() external payable {}
}
