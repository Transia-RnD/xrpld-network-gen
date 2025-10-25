from xrpld_netgen.utils.deploy_kit import download_binary
from xrpld_netgen.cli import XAHAU_RELEASE

build_server: str = "https://build.xahau.tech"
build_version: str = XAHAU_RELEASE
save_path: str = "./xrpld_netgen/cideploy/xahaud"
url: str = f"{build_server}/{build_version}"
download_binary(url, save_path)
