# THE VAULT

iPhone-first collectibles collection manager. This repository contains the recovered November 2026 single-file application and its installable web-app shell.

## Run

Serve this directory over HTTPS (or localhost). Open `index.html` through a local development server or a static hosting provider. On iPhone Safari choose Share → Add to Home Screen.

## Data safety

The existing app stores collection records in the browser under the localStorage key `the-vault-v1`. Do not clear browser/site storage or change the key without a tested migration. Export a JSON backup before switching deployments, browsers, or devices. This repository does not contain personal collections or API credentials.

## Catalog integration

The built-in search includes public catalog integrations; merchandise searches requiring a Cloudflare Worker and approved eBay API credentials will not work until configured. Never put secret credentials in browser code.

## Deployment

The existing Cloudflare Pages project is `the-vault-v123-test`. Deploy to that existing project, not a new one, after backing up user data and validating any Supabase synchronization. Pushing to GitHub does not automatically deploy unless the existing Pages project is configured to build from this repository.

## Status

Source imported and progressive web app shell added. Production verification, end-to-end testing, and Cloudflare deployment are not yet complete.

## eBay pricing

Discover can look up eBay catalog editions and show active US Buy It Now prices for a selected edition or search. Asking prices exclude shipping and tax. Sold listings open on eBay. These lookups do not change collection values.

Configure `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` as encrypted secrets in the existing Cloudflare Pages project. Use production keys with Browse access and the `commerce.catalog.readonly` scope for catalog lookup. To publish the built `website/` directory with its same-origin endpoint, run `npx wrangler pages deploy website --project-name the-vault-v123-test` from the repository root so Wrangler can find `functions/`. Keep the keys out of site files and GitHub.
