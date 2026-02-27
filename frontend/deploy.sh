#!/bin/bash

# Script to prepare frontend for deployment to Cloudflare Pages

echo "Preparing frontend for deployment..."

# Ensure dependencies are in sync
echo "Syncing dependencies..."
npm install

# Build the project using the updated pages:deploy script
echo "Building project for Cloudflare Pages..."
npm run pages:deploy

# Verify the _redirects file exists in the dist directory
echo "Verifying Cloudflare Pages configuration..."
if [ ! -f "dist/_redirects" ]; then
  echo "Creating _redirects file..."
  echo "/*    /index.html   200" > dist/_redirects
fi

echo "Frontend is ready for deployment to Cloudflare Pages!"
echo "Make sure your Cloudflare Pages dashboard has:"
echo "1. Build command: npm run build"
echo "2. Deploy command: exit 0"
echo "3. Build output directory: dist"
