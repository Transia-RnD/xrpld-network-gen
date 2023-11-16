## Deployment

1. Signup for pypi

https://pypi.org/account/register/

Account Settings -> Add Api Token

2. Get API Key

Account Settings -> Add Api Token

3. Configure Token

`poetry config pypi-token.pypi your-api-token`

4. Build Project

`poetry build`

5. Publish 

`poetry publish`