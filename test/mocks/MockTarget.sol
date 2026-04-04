// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IToken {
    function transfer(address to, uint256 value) external returns (bool);
}

contract MockTarget {
    function donate(address token, address to, uint256 amount) external {
        IToken(token).transfer(to, amount);
    }
}
