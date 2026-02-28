# Terraform Setup Script for Windows
Write-Host "Setting up Terraform for local testing..."

# Check if Chocolatey is installed
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

# Install Terraform
Write-Host "Installing Terraform..."
choco install terraform -y

# Verify installation
terraform --version

Write-Host "Terraform setup complete!"
Write-Host "You can now run: cd infrastructure/terraform && terraform init && terraform plan"
