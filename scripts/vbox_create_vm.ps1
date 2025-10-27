# VirtualBox VM Creation Script for TradeProject
# Run this script on Windows hosts to create trading model VMs

param(
    [Parameter(Mandatory=$true)]
    [string]$VMName,
    
    [Parameter(Mandatory=$true)]
    [string]$ISOPath,
    
    [string]$VBoxPath = "C:\Program Files\Oracle\VirtualBox",
    [int]$MemoryMB = 12288,
    [int]$DiskSizeGB = 120,
    [int]$CPUCount = 2
)

Set-Location $VBoxPath

Write-Host "Creating VM: $VMName" -ForegroundColor Cyan

Write-Host "Step 1: Creating VM..." -ForegroundColor Yellow
.\VBoxManage.exe createvm --name $VMName --ostype Ubuntu_64 --register

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create VM" -ForegroundColor Red
    exit 1
}

Write-Host "Step 2: Configuring resources (RAM: $MemoryMB MB, CPUs: $CPUCount)..." -ForegroundColor Yellow
.\VBoxManage.exe modifyvm $VMName --memory $MemoryMB --cpus $CPUCount

Write-Host "Step 3: Creating virtual hard disk ($DiskSizeGB GB)..." -ForegroundColor Yellow
$VDIPath = "C:\VirtualBox VMs\$VMName\$VMName.vdi"
.\VBoxManage.exe createhd --filename $VDIPath --size ($DiskSizeGB * 1024)

Write-Host "Step 4: Adding storage controllers..." -ForegroundColor Yellow
.\VBoxManage.exe storagectl $VMName --name "SATA Controller" --add sata --controller IntelAhci
.\VBoxManage.exe storageattach $VMName --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium $VDIPath

.\VBoxManage.exe storagectl $VMName --name "IDE Controller" --add ide
.\VBoxManage.exe storageattach $VMName --storagectl "IDE Controller" --port 0 --device 0 --type dvddrive --medium $ISOPath

Write-Host "Step 5: Configuring network..." -ForegroundColor Yellow
$adapters = .\VBoxManage.exe list bridgedifs
$firstAdapter = ($adapters | Select-String "Name:" | Select-Object -First 1) -replace "Name:\s+", ""

if ($firstAdapter) {
    Write-Host "Using network adapter: $firstAdapter" -ForegroundColor Green
    .\VBoxManage.exe modifyvm $VMName --nic1 bridged --bridgeadapter1 $firstAdapter
} else {
    Write-Host "Warning: Could not detect network adapter. Please configure manually." -ForegroundColor Yellow
    .\VBoxManage.exe modifyvm $VMName --nic1 nat
}

Write-Host "Step 6: Additional settings..." -ForegroundColor Yellow
.\VBoxManage.exe modifyvm $VMName --vram 16
.\VBoxManage.exe modifyvm $VMName --graphicscontroller vmsvga
.\VBoxManage.exe modifyvm $VMName --boot1 dvd --boot2 disk --boot3 none --boot4 none

Write-Host "" -ForegroundColor Green
Write-Host "VM created successfully!" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start the VM: .\VBoxManage.exe startvm $VMName" -ForegroundColor White
Write-Host "2. Follow Ubuntu installation prompts" -ForegroundColor White
Write-Host "3. After installation, remove ISO: .\VBoxManage.exe storageattach $VMName --storagectl 'IDE Controller' --port 0 --device 0 --type dvddrive --medium none" -ForegroundColor White
Write-Host "4. Start in headless mode: .\VBoxManage.exe startvm $VMName --type headless" -ForegroundColor White
Write-Host "" -ForegroundColor Green

.\VBoxManage.exe showvminfo $VMName | Select-String "Name:|Memory|CPUs|Storage"

Write-Host "" -ForegroundColor Green
Write-Host "VM configuration summary saved above" -ForegroundColor Green
