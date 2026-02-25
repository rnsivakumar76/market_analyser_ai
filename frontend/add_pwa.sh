#!/bin/sh
echo "Installing dependencies..."
npm install
echo "Adding PWA..."
npx --yes @angular/cli@20.1.5 add @angular/pwa@20.1.5 --skip-confirmation
echo "Done!"
