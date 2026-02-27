# Deploying the Frontend to Cloudflare Pages

This document outlines the steps to deploy the Burst.fm frontend to Cloudflare Pages.

## Prerequisites

- Node.js 20 or later
- npm 10 or later
- A Cloudflare account with Pages enabled

## Local Preparation

Before deploying to Cloudflare, ensure your dependencies are in sync:

```bash
# Run this script to prepare for deployment
./deploy.sh
```

This script will:
1. Sync your dependencies (package.json and package-lock.json)
2. Build the project
3. Ensure that SPA routing works by creating a _redirects file

## Cloudflare Pages Deployment

### Manual Deployment in Cloudflare Dashboard

1. Log in to your Cloudflare dashboard
2. Navigate to Pages
3. Click "Create a project"
4. Choose "Direct Upload" option
5. Drag and drop your `dist` folder or upload a ZIP of the contents
6. Click "Deploy site"

### GitHub Integration (Recommended)

1. Log in to your Cloudflare dashboard
2. Navigate to Pages
3. Click "Create a project"
4. Choose "Connect to Git"
5. Select your Git provider and authenticate
6. Select your repository
7. Configure your build settings:
   - Build command: `npm install && npm run pages:deploy`
   - Build output directory: `dist`
   - Root directory: Path to your frontend (e.g., `/frontend` if your repo has multiple directories)
   - Node.js version: 20 (or later)
8. Add environment variables if needed
9. Click "Save and Deploy"

## Cloudflare Pages Configuration

### Prerequisites

- Node.js v20 or later
- npm v10 or later
- A Cloudflare account with Pages enabled

### Local Preparation

Before deploying to Cloudflare Pages, prepare your project locally:

```bash
# Run the deploy script to prepare the project
./deploy.sh
```

This script will:
1. Install dependencies
2. Build the project using Vite
3. Ensure the `_redirects` file exists for proper SPA routing

### Cloudflare Pages Dashboard Configuration

In the Cloudflare Pages dashboard, configure your project with these settings:

#### Build Configuration

- **Build command**: `npm run build`
- **Deploy command**: `exit 0`
- **Build output directory**: `dist`
- **Root directory**: `/frontend` (or the appropriate path to your frontend directory)

#### Environment Variables

Add these environment variables to prevent Wrangler from being used:

- `CF_PAGES_DEPLOY_WRANGLER`: `false`
- `USE_WRANGLER`: `false`
- `DISABLE_WRANGLER`: `true`
- `CF_PAGES_DEPLOYMENT_TYPE`: `static`

### Important Files

- `.cloudflare/pages.toml`: Cloudflare Pages build configuration
- `pages.json`: Cloudflare Pages deployment configuration
- `public/_redirects`: SPA routing rule (copied to `dist/_redirects` during build)

### Troubleshooting

If you encounter deployment issues:

1. **Wrangler is still being used**: Ensure the deploy command is set to `exit 0` in the dashboard
2. **Missing routes/404 errors**: Verify `_redirects` file exists in the `dist` directory
3. **Build failures**: Check build logs for specific errors

### Manual Deployment (Alternative)

If automatic deployment continues to cause issues, you can manually deploy the `dist` directory:

```bash
# Install Wrangler CLI
npm install -g wrangler

# Deploy the dist directory directly
cd frontend
wrangler pages deploy dist --project-name=burst-fm-frontend
```

This bypasses the automatic build process and directly uploads your pre-built assets.

### Monitoring

After deployment, monitor your Cloudflare Pages application for:
- Successful page loads
- Correct routing behavior
- Performance metrics
- Error logs

## Important Configuration Files

- `.cloudflare/pages.toml`: Contains the build configuration for Cloudflare Pages
- `public/_redirects`: Ensures proper routing for single-page applications
- `pages.json`: Provides additional configuration for Cloudflare Pages

## Troubleshooting

### Common Issues:

1. **Missing dependencies**: 
   - Run `npm install` locally to update package-lock.json

2. **Build fails**: 
   - Check build logs in Cloudflare Dashboard
   - Ensure Node.js version is set to 20 or later

3. **Routes not working**: 
   - Verify the _redirects file exists in the dist directory
   - Check that the rule `/*    /index.html   200` is present

4. **Wrangler deployment errors**:
   - Ensure CF_PAGES_DEPLOY_WRANGLER is set to "false" in your pages.toml
   - Use the pages:deploy script instead of default build

## Maintenance

When updating the application:
1. Make code changes
2. Test locally with `npm run dev`
3. Run the deploy script (`./deploy.sh`)
4. Commit and push changes to trigger automatic deployment or deploy manually
