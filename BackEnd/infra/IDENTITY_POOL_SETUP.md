# Cognito Identity Pool Setup Guide

This guide explains how to configure per-user S3 storage isolation using a Cognito Identity Pool.

---

## User Pool vs Identity Pool

| | User Pool | Identity Pool |
|---|---|---|
| **Purpose** | Authentication — verifies who the user is | Credential vending — gives the user temporary AWS credentials |
| **Output** | JWT tokens (id, access, refresh) | Temporary AWS credentials (access key, secret, session token) |
| **Used for** | Logging in, API authorisation | Direct S3/DynamoDB access from the client |

CloudGraph already uses a **User Pool** for API authentication. Adding an **Identity Pool** allows the frontend to upload directly to S3 using temporary scoped credentials, bypassing the API server entirely for large uploads.

---

## Step 1 — Create the Identity Pool

1. Open **AWS Cognito Console** → **Federated Identities** (or search "Identity Pools")
2. Click **Create new identity pool**
3. Give it a name: `cloudgraph-identity-pool`
4. Under **Authentication providers** → **Cognito**, enter:
   - **User Pool ID**: your existing User Pool ID
   - **App Client ID**: your existing App Client ID
5. Click **Create Pool**

---

## Step 2 — Attach the IAM Policy

AWS will create two IAM roles: an **Authenticated** role and an **Unauthenticated** role.

1. Open **IAM Console** → **Roles** → find the authenticated role (named something like `Cognito_cloudgraphidentitypoolAuth_Role`)
2. Click **Add permissions** → **Create inline policy**
3. Paste the contents of `cognito-identity-pool-policy.json` (replace `YOUR_BUCKET_NAME`)
4. Save the policy

The `${cognito-identity.amazonaws.com:sub}` variable in the policy is resolved by AWS at request time — it is replaced with the user's unique Identity Pool subject, making cross-user S3 access impossible at the infrastructure level.

---

## Step 3 — Frontend Integration

Use the AWS SDK to obtain temporary credentials from the Identity Pool and upload directly to S3:

```javascript
import { CognitoIdentityClient } from "@aws-sdk/client-cognito-identity";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-provider-cognito-identity";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

const credentials = fromCognitoIdentityPool({
  client: new CognitoIdentityClient({ region: "YOUR_REGION" }),
  identityPoolId: "YOUR_IDENTITY_POOL_ID",
  logins: {
    [`cognito-idp.YOUR_REGION.amazonaws.com/YOUR_USER_POOL_ID`]: idToken,
  },
});

const s3 = new S3Client({ region: "YOUR_REGION", credentials });
await s3.send(new PutObjectCommand({ Bucket: "YOUR_BUCKET_NAME", Key: `uploads/${sub}/file.jpg`, Body: file }));
```

This approach replaces the presigned PUT URL flow for clients that support the AWS SDK. It is more secure (no server-side involvement in uploads) and supports resumable uploads.
