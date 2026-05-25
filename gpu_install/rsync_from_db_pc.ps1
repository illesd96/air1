# Run this on the WINDOWS DB PC to copy the project to the GPU PC.
# Requires: rsync installed on the Windows side (comes with Git for Windows).
#
# Usage:
#   .\gpu_install\rsync_from_db_pc.ps1 -GpuUser you -GpuHost gpu-pc.local
#
# The GPU PC needs sshd running:
#   sudo apt install -y openssh-server && sudo systemctl enable --now ssh

param(
    [Parameter(Mandatory=$true)] [string]$GpuUser,
    [Parameter(Mandatory=$true)] [string]$GpuHost,
    [string]$RemotePath = "~/aircraft/"
)

$src = "c:/Projects/fun/aircraft/"
$excludes = @(
    "--exclude=.venv",
    "--exclude=__pycache__",
    "--exclude=*.pyc",
    "--exclude=data/images",          # not needed on GPU PC
    "--exclude=data/exports",         # huge, GPU PC doesn't need it
    "--exclude=node_modules",
    "--exclude=renders",              # output dir, GPU PC will generate
    "--exclude=video_pipeline/workdir",
    "--exclude=.idea",
    "--exclude=.vscode"
)

$rsyncArgs = @("-av", "--delete-after") + $excludes + @($src, "${GpuUser}@${GpuHost}:${RemotePath}")

Write-Host "rsync $($rsyncArgs -join ' ')" -ForegroundColor Cyan
& rsync @rsyncArgs
