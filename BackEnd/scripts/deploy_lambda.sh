#!/bin/bash
# Zips and deploys the lambda functions

# Install dependencies into a package directory
mkdir -p package
pip install -r requirements.txt -t package/

# List of lambda functions to deploy
LAMBDAS=("thumbnail_generator" "image_processor" "clustering_processor")

for LAMBDA_NAME in "${LAMBDAS[@]}"; do
    echo "Deploying $LAMBDA_NAME..."
    
    # Create deployment zip
    cd package
    zip -r ../${LAMBDA_NAME}.zip .
    cd ..
    
    # Add application code
    zip -g ${LAMBDA_NAME}.zip lambda/${LAMBDA_NAME}.py
    zip -g ${LAMBDA_NAME}.zip services/*.py
    zip -g ${LAMBDA_NAME}.zip utils/*.py
    zip -g ${LAMBDA_NAME}.zip config.py
    
    # Update AWS Lambda
    aws lambda update-function-code \
        --function-name ${LAMBDA_NAME} \
        --zip-file fileb://${LAMBDA_NAME}.zip
        
    echo "Successfully updated $LAMBDA_NAME"
    rm ${LAMBDA_NAME}.zip
done

# Cleanup
rm -rf package
echo "Deployment complete!"
