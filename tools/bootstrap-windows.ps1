[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$SkipGitHubLogin,
    [switch]$SkipClone,
    [string]$Destination = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'MCM')
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = @($machinePath, $userPath) -join ';'
}

function Test-CommandAvailable {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage {
    param(
        [string]$Command,
        [string]$PackageId,
        [string]$DisplayName
    )

    if (Test-CommandAvailable $Command) {
        Write-Host "[OK] $DisplayName already installed."
        return
    }

    if ($CheckOnly) {
        Write-Host "[MISSING] $DisplayName ($PackageId)"
        return
    }

    Write-Step "Installing $DisplayName"
    & winget install --id $PackageId --exact --source winget `
        --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed to install $DisplayName (exit code $LASTEXITCODE)."
    }

    Refresh-ProcessPath
    if (-not (Test-CommandAvailable $Command)) {
        throw "$DisplayName was installed, but '$Command' is not available in this terminal. Restart the terminal and rerun the script."
    }
}

if ($env:OS -ne 'Windows_NT') {
    throw 'This bootstrap script supports Windows only.'
}

Write-Step 'Checking Windows Package Manager'
if (-not (Test-CommandAvailable 'winget')) {
    throw 'winget is unavailable. Update App Installer from Microsoft Store, then rerun this script.'
}

Write-Step 'Checking required tools'
Install-WingetPackage -Command 'code' -PackageId 'Microsoft.VisualStudioCode' -DisplayName 'Visual Studio Code'
Install-WingetPackage -Command 'git' -PackageId 'Git.Git' -DisplayName 'Git'
Install-WingetPackage -Command 'gh' -PackageId 'GitHub.cli' -DisplayName 'GitHub CLI'

if ($CheckOnly) {
    Write-Host "`nCheck-only mode finished. No software was installed, no login was started, and no repository was cloned." -ForegroundColor Yellow
    exit 0
}

Write-Step 'Verifying installed commands'
& code --version | Select-Object -First 1
& git --version
& gh --version | Select-Object -First 1

if (-not $SkipGitHubLogin) {
    Write-Step 'Checking GitHub authentication'
    & gh auth status 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'A browser login will open. Complete authorization yourself; do not share tokens or verification codes.' -ForegroundColor Yellow
        & gh auth login --web --git-protocol https --hostname github.com
        if ($LASTEXITCODE -ne 0) {
            throw "GitHub authentication failed (exit code $LASTEXITCODE)."
        }
    }
}

if (-not $SkipClone) {
    Write-Step 'Preparing repository directory'
    $resolvedDestination = [System.IO.Path]::GetFullPath($Destination)
    $destinationParent = Split-Path -Parent $resolvedDestination

    if (Test-Path -LiteralPath $resolvedDestination) {
        $gitMarker = Join-Path $resolvedDestination '.git'
        if (-not (Test-Path -LiteralPath $gitMarker)) {
            throw "Destination already exists and is not a Git repository: $resolvedDestination"
        }
        Write-Host "[OK] Reusing existing Git repository: $resolvedDestination"
    } else {
        if (-not (Test-Path -LiteralPath $destinationParent)) {
            New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        }
        & gh repo clone 'Ash-Rise/MCM' $resolvedDestination
        if ($LASTEXITCODE -ne 0) {
            throw "Repository clone failed (exit code $LASTEXITCODE)."
        }
    }

    Write-Step 'Opening the complete repository in Visual Studio Code'
    & code $resolvedDestination
}

Write-Host "`nMCM bootstrap completed. The repository AI must now read AGENTS.md before making changes." -ForegroundColor Green

