# NeonaMemo Cloudflare Worker

Dedicated Worker source for `neonamemo-api`, without any API secrets.

Cloudflare Worker Settings > Builds > Connect GitHub, choose this repository and set the root directory to `neonamemo-worker`. Build command: `npm run deploy`. If an install command is requested, use `npm install`.

After deployment create KV namespace and bind it as `DEVICES`. Create secrets `KAKAO_REST_API_KEY` and `OWNER_ADMIN_KEY` (24+ random characters). Never put these values into source control, APK, chat or screenshots.

Verify `/health` is JSON. `/admin` is the owner approval UI. Until the KV and secrets are configured, address lookup will be unavailable.

Note: This is address lookup and device approval only, not the shared work log database. Devices need an app version that performs register/status/address requests; old APKs will not automatically connect just from deploying the server.

## Cloudflare Git builds

The Worker is linked to GitHub on branch `main` with root directory `/neonamemo-worker`. This README change triggers an initial deployment build. This does not create the KV namespace or configure secrets; do those in the Cloudflare dashboard after checking the deployment logs.
