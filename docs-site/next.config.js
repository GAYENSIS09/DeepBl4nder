/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  basePath: '/DeepBl4nder',
  assetPrefix: '/DeepBl4nder/',
}
module.exports = nextConfig
