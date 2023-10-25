from xrpld_publisher.publisher import PublisherClient
from xrpld_publisher.utils import from_days_to_expiration, download_unl
import time


def main():
    try:
        unl_url = "https://vl.test.xahauexplorer.com/"
        manifest = "JAAAAAFxIe101ANsZZGkvfnFTO+jm5lqXc5fhtEf2hh0SBzp1aHNwXMh7TN9+b62cZqTngaFYU5tbGpYHC8oYuI3G3vwj9OW2Z9gdkAnUjfY5zOEkhq31tU4338jcyUpVA5/VTsANFce7unDo+JeVoEhfuOb/Y8WA3Diu9XzuOD4U/ikfgf9SZOlOGcBcBJAw44PLjH+HUtEnwX45lIRmo0x5aINFMvZsBpE9QteSDBXKwYzLdnSW4e1bs21o+IILJIiIKU/+1Uxx0FRpQbMDA=="
        pk = "CC9E8B118E8E927DA82A66B9D931E1AB6309BA32F057F8B216600B347C552006"
        download_unl(unl_url)
        add_list = [
            "JAAAAAFxIe3kW20uKHcjYwGFkZ7+Ax8FIorTwvHqmY8kvePtYG4nSHMhAjIn+/pQWK/OU9ln8Rux6wnQGY1yMFeaGR5gEcFSGxa1dkYwRAIgSAGa6gWCa2C9XxIMSoAB1qCZjjJMXGpl5Tb+81U5RDwCIG3GQHXPUjFkTMwEcuM8G6dwcWzEfB1nYa5MqxFAhOXscBJApcamLcUBNxmABeKigy+ZYTYLqMKuGtV9HgjXKA5oI9CNH0xA6R52NchP3rZyXWOWS0tan25o0rwQBNIY78k6Cg==",
        ]
        remove_list = [
            "EDE8FA88589CF8825334609E97EC8BFA1F56FF95D9D75BBD29996416D41319BF20",
        ]
        old_unl = PublisherClient("vl.json")
        validators = [
            validator
            for validator in old_unl.vl.blob.validators
            if validator["pk"] not in remove_list
        ]
        client = PublisherClient(manifest)
        for manifest in add_list + [validator.manifest for validator in validators]:
            client.add_validator(manifest)
        expiration = from_days_to_expiration(time.time(), 365)
        client.sign_unl(pk, "myvl.json", expiration)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
