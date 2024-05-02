#!/usr/bin/env bash
set -euo pipefail

RETRODEEP_VERSION="v0.0.1"
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "OS: ${OS}, CPU Architecture: ${ARCH} detected."

# Function to display error messages
error() {
    echo -e "\033[0;31merror:\033[0m $1" >&2
    exit 1
}

# Function to display success messages
success() {
    echo -e "\033[0;32msuccess:\033[0m $1"
}

case "${OS}" in
Linux)
    case "${ARCH}" in
    x86_64 | amd64) RETRODEEP_URL="https://github.com/retrodeep-io/retrodeep-cli/releases/download/${RETRODEEP_VERSION}/retrodeep-linux-amd64" ;;
    aarch64) RETRODEEP_URL="https://github.com/retrodeep-io/retrodeep-cli/releases/download/${RETRODEEP_VERSION}/retrodeep-linux-arm64" ;;
    *)
        echo "Unsupported Architecture: ${ARCH}" >&2
        exit 1
        ;;
    esac
    ;;
Darwin)
    case "${ARCH}" in
    x86_64 | amd64 | i386) RETRODEEP_URL="https://github.com/retrodeep-io/retrodeep-cli/releases/download/${RETRODEEP_VERSION}/retrodeep-macos-x64" ;;
    arm64) RETRODEEP_URL="https://github.com/retrodeep-io/retrodeep-cli/releases/download/${RETRODEEP_VERSION}/retrodeep-macos-arm64" ;;
    *)
        echo "Unsupported Architecture: ${ARCH}" >&2
        exit 1
        ;;
    esac
    ;;
*)
    echo "Unsupported OS: ${OS}" >&2
    exit 1
    ;;
esac

INSTALL_DIR="$HOME/.retrodeep/bin"
mkdir -p "${INSTALL_DIR}"
RETRODEEP_BIN="${INSTALL_DIR}/retrodeep"

echo "Downloading RetroDeep from ${RETRODEEP_URL}..."
curl --fail --location --progress-bar --output "${RETRODEEP_BIN}" "${RETRODEEP_URL}" || error "Failed to download RetroDeep"

chmod +x "${RETRODEEP_BIN}" || error "Failed to set executable permissions on RetroDeep"

echo "Moving RetroDeep to /usr/local/bin..."
sudo mv "${RETRODEEP_BIN}" /usr/local/bin/retrodeep || error "Failed to move RetroDeep binary to /usr/local/bin/retrodeep"

echo 'Adding RetroDeep to PATH in .bashrc and .zshrc...'
{
    echo "# RetroDeep PATH"
    echo "export PATH=\"${INSTALL_DIR}:\$PATH\""
} >>"$HOME/.bashrc"

if [ -f "$HOME/.zshrc" ]; then
    {
        echo "# RetroDeep PATH"
        echo "export PATH=\"${INSTALL_DIR}:\$PATH\""
    } >>"$HOME/.zshrc"
fi

success "RetroDeep ${RETRODEEP_VERSION} was installed successfully to /usr/local/bin/retrodeep"
echo "You can restart your terminal or source the appropriate profile to update your PATH using 'source ~/.bashrc'"
