import json
from pathlib import Path

from solcx import compile_standard, install_solc

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FILES = {
    "ScampiaVault": ROOT / "contracts" / "ScampiaVault.sol",
    "ScampiaENSManager": ROOT / "contracts" / "ScampiaENSManager.sol",
}
ARTIFACT_DIR = ROOT / "contracts" / "artifacts"
SOLC_VERSION = "0.8.24"


def _artifact_paths(contract_name: str) -> tuple[Path, Path]:
    return (
        ARTIFACT_DIR / f"{contract_name}.abi.json",
        ARTIFACT_DIR / f"{contract_name}.bytecode.txt",
    )


def main() -> None:
    sources = {
        path.name: {"content": path.read_text(encoding="utf-8")}
        for path in CONTRACT_FILES.values()
    }
    install_solc(SOLC_VERSION)

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": sources,
            "settings": {
                "optimizer": {"enabled": True, "runs": 200},
                "viaIR": True,
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"],
                    }
                },
            },
        },
        solc_version=SOLC_VERSION,
    )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for contract_name, source_path in CONTRACT_FILES.items():
        artifact = compiled["contracts"][source_path.name][contract_name]
        abi = artifact["abi"]
        bytecode = artifact["evm"]["bytecode"]["object"]
        abi_file, bytecode_file = _artifact_paths(contract_name)
        abi_file.write_text(json.dumps(abi, indent=2), encoding="utf-8")
        bytecode_file.write_text(bytecode, encoding="utf-8")
        print(f"ABI exported to: {abi_file}")
        print(f"Bytecode exported to: {bytecode_file}")


if __name__ == "__main__":
    main()
