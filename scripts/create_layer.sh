#!/bin/bash

# Create layer for API
rm -rf layer/*
rm layer.zip
mkdir -p layer/python/lib/python3.12/site-packages
pip install -r requirements_lambda.txt -t layer/python/lib/python3.12/site-packages
cd layer
7z a -tzip ../layer.zip .
cd ..