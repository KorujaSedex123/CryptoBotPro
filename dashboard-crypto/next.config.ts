import type { NextConfig } from "next";

const nextConfig: NextConfig = {
 experimental: {
        serverActions: {
            allowedOrigins: ["localhost:3000", "100.82.210.82:3000"] 
        }
    }
};

export default nextConfig;
