#!/usr/bin/env pwsh
# Start MongoDB + Mongo Express via Docker Compose
docker compose up -d
Write-Host ""
Write-Host "Mongo:        mongodb://aircraft:aircraft@localhost:27017"
Write-Host "Mongo Express http://localhost:8081"
