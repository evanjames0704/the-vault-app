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
