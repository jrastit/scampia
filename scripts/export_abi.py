import json
from pathlib import Path

from solcx import compile_standard, install_solc

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FILE = ROOT / "contracts" / "ScampiaVault.sol"
ARTIFACT_DIR = ROOT / "contracts" / "artifacts"
ABI_FILE = ARTIFACT_DIR / "ScampiaVault.abi.json"
BYTECODE_FILE = ARTIFACT_DIR / "ScampiaVault.bytecode.txt"
SOLC_VERSION = "0.8.24"


def main() -> None:
    source = CONTRACT_FILE.read_text(encoding="utf-8")
    install_solc(SOLC_VERSION)

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "ScampiaVault.sol": {"content": source},
            },
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "viaIR": True,
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"],
                    }
                }
            },
        },
        solc_version=SOLC_VERSION,
    )

    artifact = compiled["contracts"]["ScampiaVault.sol"]["ScampiaVault"]
    abi = artifact["abi"]
    bytecode = artifact["evm"]["bytecode"]["object"]

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ABI_FILE.write_text(json.dumps(abi, indent=2), encoding="utf-8")
    BYTECODE_FILE.write_text(bytecode, encoding="utf-8")

    print(f"ABI exported to: {ABI_FILE}")
    print(f"Bytecode exported to: {BYTECODE_FILE}")


if __name__ == "__main__":
    main()
