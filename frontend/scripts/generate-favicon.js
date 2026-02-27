const fs = require('fs');
const { createCanvas } = require('canvas');

// Create a 32x32 canvas for the favicon
const canvas = createCanvas(32, 32);
const ctx = canvas.getContext('2d');

// Set background to transparent
ctx.clearRect(0, 0, 32, 32);

// Draw the logo (simplified version of the SVG)
ctx.fillStyle = '#000000';

// Function to draw a rounded rectangle
function roundRect(x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
  ctx.fill();
}

// Scale down the SVG coordinates
roundRect(3, 12, 3, 6, 0.8);
roundRect(8, 9, 3, 12, 0.8);
roundRect(13, 6, 3, 18, 0.8);
roundRect(18, 3, 3, 24, 0.8);
roundRect(23, 9, 3, 12, 0.8);
roundRect(28, 12, 3, 6, 0.8);

// Convert canvas to PNG buffer
const buffer = canvas.toBuffer('image/png');

// Write the PNG file
fs.writeFileSync('public/favicon.png', buffer);

console.log('favicon.png has been generated');
