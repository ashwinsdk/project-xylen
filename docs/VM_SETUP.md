# VM Setup Guide for Windows Hosts

This guide provides exact commands to create Ubuntu LTS VMs on Windows hosts using VirtualBox for running trading model servers.

## Prerequisites

Download and install VirtualBox 7.0 or later from https://www.virtualbox.org/wiki/Downloads

Download Ubuntu 22.04 LTS Server ISO from https://ubuntu.com/download/server

## Creating a VM Using VirtualBox GUI on Windows

### Step 1: Create New Virtual Machine

Open VirtualBox Manager and click New or run these PowerShell commands to create a VM:

```powershell
cd "C:\Program Files\Oracle\VirtualBox"
.\VBoxManage.exe createvm --name "TradingModelVM1" --ostype Ubuntu_64 --register
```

### Step 2: Configure VM Resources

Allocate 12 GB RAM and 2 CPUs:

```powershell
.\VBoxManage.exe modifyvm "TradingModelVM1" --memory 12288 --cpus 2
```

### Step 3: Create Virtual Hard Disk

Create a 120 GB dynamically allocated disk:

```powershell
.\VBoxManage.exe createhd --filename "C:\VirtualBox VMs\TradingModelVM1\TradingModelVM1.vdi" --size 122880
```

Attach the disk to the VM:

```powershell
.\VBoxManage.exe storagectl "TradingModelVM1" --name "SATA Controller" --add sata --controller IntelAhci
.\VBoxManage.exe storageattach "TradingModelVM1" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium "C:\VirtualBox VMs\TradingModelVM1\TradingModelVM1.vdi"
```

### Step 4: Attach Ubuntu ISO

```powershell
.\VBoxManage.exe storagectl "TradingModelVM1" --name "IDE Controller" --add ide
.\VBoxManage.exe storageattach "TradingModelVM1" --storagectl "IDE Controller" --port 0 --device 0 --type dvddrive --medium "C:\Users\YourUsername\Downloads\ubuntu-22.04-live-server-amd64.iso"
```

Replace the ISO path with your actual download location.

### Step 5: Configure Network

Set up bridged networking so the VM gets an IP on your local network:

```powershell
.\VBoxManage.exe modifyvm "TradingModelVM1" --nic1 bridged --bridgeadapter1 "Intel(R) Ethernet Connection"
```

Replace the adapter name with your actual network adapter. To list adapters:

```powershell
.\VBoxManage.exe list bridgedifs
```

### Step 6: Start VM and Install Ubuntu

Start the VM:

```powershell
.\VBoxManage.exe startvm "TradingModelVM1"
```

The Ubuntu installer will boot. Follow these steps in the installer:

1. Select language: English
2. Select keyboard layout: English US
3. Choose Ubuntu Server (minimized)
4. Configure network: Accept DHCP defaults
5. Configure proxy: Leave blank
6. Configure mirror: Accept defaults
7. Configure storage: Use entire disk, accept defaults
8. Profile setup:
   - Your name: ubuntu
   - Server name: tradingvm1
   - Username: ubuntu
   - Password: choose a strong password
9. SSH Setup: Check "Install OpenSSH server"
10. Featured Server Snaps: Skip all
11. Wait for installation to complete
12. Reboot when prompted

After reboot, remove the ISO:

```powershell
.\VBoxManage.exe storageattach "TradingModelVM1" --storagectl "IDE Controller" --port 0 --device 0 --type dvddrive --medium none
```

## Initial VM Configuration

### Step 1: Login and Update System

Login as ubuntu user and run:

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 2: Install Required Packages

```bash
sudo apt install -y python3.10 python3.10-venv python3-pip build-essential git curl net-tools
```

### Step 3: Find VM IP Address

```bash
ip addr show
```

Note the IP address assigned to your network interface (usually eth0 or enp0s3). This will be used in the Mac coordinator configuration.

### Step 4: Enable SSH Access

SSH should already be running. Test from your Mac:

```bash
ssh ubuntu@192.168.1.100
```

Replace the IP with your actual VM IP.

### Step 5: Create Model Server Directory

```bash
sudo mkdir -p /opt/trading_model
sudo chown ubuntu:ubuntu /opt/trading_model
cd /opt/trading_model
```

### Step 6: Transfer Model Server Code

From your Mac, transfer the model server code:

```bash
scp -r model_server_template/* ubuntu@192.168.1.100:/opt/trading_model/
```

### Step 7: Setup Python Virtual Environment

On the VM:

```bash
cd /opt/trading_model
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 8: Configure Environment Variables

```bash
cp models.env.example models.env
nano models.env
```

Edit the MODEL_PATH to point to your model file location. Save and exit (Ctrl+X, Y, Enter).

### Step 9: Create Placeholder Model Directory

```bash
mkdir -p /opt/trading_model/models
```

At this point you can copy your model file or the server will use placeholder predictions.

### Step 10: Test Model Server

```bash
source venv/bin/activate
python server.py
```

The server should start on port 8000. Test from another terminal:

```bash
curl http://localhost:8000/health
```

Stop the server with Ctrl+C.

### Step 11: Install Systemd Service

```bash
sudo cp model_server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable model_server
sudo systemctl start model_server
```

Check status:

```bash
sudo systemctl status model_server
```

View logs:

```bash
sudo journalctl -u model_server -f
```

## Configure VirtualBox Autostart on Windows

### Method 1: Using Task Scheduler

Open Task Scheduler and create a new task:

1. Open Task Scheduler (taskschd.msc)
2. Click "Create Task" in the right panel
3. General tab:
   - Name: Start TradingModelVM1
   - Run whether user is logged on or not
   - Run with highest privileges
4. Triggers tab:
   - New trigger
   - Begin the task: At startup
5. Actions tab:
   - New action
   - Program: C:\Program Files\Oracle\VirtualBox\VBoxManage.exe
   - Arguments: startvm "TradingModelVM1" --type headless
6. Click OK and enter your Windows password

### Method 2: Using PowerShell Script

Create a PowerShell script at C:\Scripts\start_trading_vms.ps1:

```powershell
Set-Location "C:\Program Files\Oracle\VirtualBox"
.\VBoxManage.exe startvm "TradingModelVM1" --type headless
Start-Sleep -Seconds 5
.\VBoxManage.exe startvm "TradingModelVM2" --type headless
```

Add this script to Windows startup folder:

```powershell
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\StartTradingVMs.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File C:\Scripts\start_trading_vms.ps1"
$Shortcut.Save()
```

## Creating Additional VMs

Repeat the process for up to 4 VMs. Use different names and ensure each VM gets a unique IP address:

- TradingModelVM1 (192.168.1.100)
- TradingModelVM2 (192.168.1.101)
- TradingModelVM3 (192.168.1.102)
- TradingModelVM4 (192.168.1.103)

Quick clone method:

```powershell
.\VBoxManage.exe clonevm "TradingModelVM1" --name "TradingModelVM2" --register
.\VBoxManage.exe modifyvm "TradingModelVM2" --memory 12288
```

After cloning, start the VM and change its hostname:

```bash
sudo hostnamectl set-hostname tradingvm2
```

## VM Management Commands

Start VM:
```powershell
.\VBoxManage.exe startvm "TradingModelVM1" --type headless
```

Stop VM gracefully:
```powershell
.\VBoxManage.exe controlvm "TradingModelVM1" acpipowerbutton
```

Force stop VM:
```powershell
.\VBoxManage.exe controlvm "TradingModelVM1" poweroff
```

List running VMs:
```powershell
.\VBoxManage.exe list runningvms
```

Check VM status:
```powershell
.\VBoxManage.exe showvminfo "TradingModelVM1" --machinereadable | findstr State
```

## Troubleshooting

### VM Cannot Access Network

Check that bridged networking is properly configured and your network adapter is active.

```powershell
.\VBoxManage.exe showvminfo "TradingModelVM1" | findstr NIC
```

### Cannot SSH to VM

Ensure SSH service is running on VM:

```bash
sudo systemctl status ssh
```

Check firewall (should be disabled by default on Ubuntu Server):

```bash
sudo ufw status
```

### Model Server Not Starting

Check logs:

```bash
sudo journalctl -u model_server -n 50
```

Check if port 8000 is already in use:

```bash
sudo netstat -tulpn | grep 8000
```

### Insufficient Memory

If the host has less than 16 GB RAM, reduce VM allocation:

```powershell
.\VBoxManage.exe modifyvm "TradingModelVM1" --memory 8192
```

Note that 12 GB is recommended for running models efficiently.

## Log Rotation Setup

Configure log rotation for the model server:

```bash
sudo nano /etc/logrotate.d/model_server
```

Add this configuration:

```
/var/log/model_server/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
```

## Backup and Restore

### Backup VM

Export VM to OVA file:

```powershell
.\VBoxManage.exe export "TradingModelVM1" -o "C:\Backups\TradingModelVM1.ova"
```

### Restore VM

Import OVA file:

```powershell
.\VBoxManage.exe import "C:\Backups\TradingModelVM1.ova"
```

### Backup Model and Data

From Mac, backup model files and training data:

```bash
ssh ubuntu@192.168.1.100 "cd /opt/trading_model && tar czf backup.tar.gz models/ training_data/"
scp ubuntu@192.168.1.100:/opt/trading_model/backup.tar.gz ./backups/vm1_backup_$(date +%Y%m%d).tar.gz
```

## Resource Monitoring

Monitor VM resource usage from host:

```powershell
.\VBoxManage.exe metrics query "TradingModelVM1"
```

Inside VM, monitor resources:

```bash
htop
free -h
df -h
```

Install htop if not present:

```bash
sudo apt install htop -y
```

## Security Notes

The model server runs without authentication as specified. To secure your setup:

1. Keep VMs on a private network isolated from the internet
2. Use firewall rules to restrict access to port 8000
3. Never expose VM ports directly to public networks
4. Keep Ubuntu and all packages updated
5. Use strong passwords for VM user accounts

## Next Steps

Once VMs are configured, proceed to DOCUMENTATION.md to set up the Mac coordinator and connect it to your model VMs.
