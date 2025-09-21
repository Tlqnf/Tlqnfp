#!/bin/sh
set -e

# Check if tiles are already built (the file will exist on the mounted EFS volume)
if [ ! -f /data/valhalla.json ]; then
  echo ">>> Valhalla tiles not found in /data. Starting initial build process..."

  # Check if the S3_PBF_PATH environment variable is provided
  if [ -z "$S3_PBF_PATH" ]; then
    echo "FATAL: S3_PBF_PATH environment variable is not set. Cannot download PBF file."
    exit 1
  fi

  echo ">>> Downloading PBF file from S3 path: $S3_PBF_PATH"
  aws s3 cp "$S3_PBF_PATH" /data/osm.pbf

  echo ">>> Building Valhalla config..."
  valhalla_build_config --mjolnir-tile-dir /data/tiles --mjolnir-tile-extract /data/valhalla_tiles.tar --mjolnir-timezone /data/timezones.sqlite --mjolnir-admin /data/admins.sqlite > /data/valhalla.json

  echo ">>> Building Valhalla tiles from PBF file..."
  valhalla_build_tiles -c /data/valhalla.json /data/osm.pbf

  echo ">>> Building Valhalla admins..."
  valhalla_build_admins -c /data/valhalla.json /data/osm.pbf

  echo ">>> Building Valhalla timezones..."
  valhalla_build_timezones -c /data/valhalla.json

  echo ">>> Build complete. Cleaning up PBF file to save space on EFS..."
  rm /data/osm.pbf

  echo ">>> Archiving Valhalla tiles into valhalla_tiles.tar..."
  tar -cf /data/valhalla_tiles.tar -C /data tiles
else
  echo ">>> Found existing Valhalla tiles in /data. Skipping build process."
fi

echo ">>> Starting Valhalla service..."
# Use exec to make valhalla_service the main process (PID 1)
exec valhalla_service /data/valhalla.json 1
