# Create lambda 
cd ..
rm -rf lambda/*
rm meetings_api.zip
mkdir -p lambda/utils
cp utils/meetings_api_lambda.py lambda
cp utils/__init__.py lambda/utils
cp utils/constants.py lambda/utils
cd lambda
7z a -tzip ../meetings_api.zip .
cd ../terraform_scripts