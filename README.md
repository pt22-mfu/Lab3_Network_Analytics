# Lab 3 — Cisco Router SSH Web Console

## Student Information

- Name: Phyo Thant Kyaw
- Student ID: 6631501189
- Program: Computer Engineering
- University: Mae Fah Luang University

## Project Description

A Python web application that connects to a Cisco router through SSH
using Paramiko and executes a command entered in a web browser.

## Features

- Router IP address input
- Router commandline input
- Execute button
- Router output display
- Connection and command error messages
- Docker Compose deployment

## Technologies

- Frontend: HTML, CSS, JavaScript
- Backend: Python and Flask
- SSH connection: Paramiko
- Deployment: Docker and Docker Compose

## Project Files

| File | Purpose |
| --- | --- |
| backend/app.py | Flask backend and Paramiko SSH execution |
| backend/requirements.txt | Python dependencies |
| frontend/index.html | Web interface |
| Dockerfile | Builds the application container |
| docker-compose.yml | Starts the application with Docker Compose |
| .gitignore | Excludes local files from Git |
| .dockerignore | Excludes local files from the Docker build |

## How It Works

1. The user enters the router IP address and one IOS command.
2. JavaScript sends the inputs to the Flask API.
3. Paramiko opens an SSH session using the lab credentials.
4. The backend sends `terminal length 0` to disable pagination.
5. The requested command is sent to the router.
6. The backend reads the output until the router prompt returns.
7. The SSH connection closes and the browser displays the result.

## Cisco Router Configuration

Example configuration for the isolated university lab:

```text
enable
configure terminal
hostname R1
ip domain-name test.com
username admin privilege 15 password cisco

interface FastEthernet0/0
 ip address dhcp
 no shutdown
exit

crypto key generate rsa modulus 1024
ip ssh version 2

line vty 0 4
 login local
 transport input ssh
exit

end
write memory
```

The interface name and RSA command syntax depend on the IOS image.
DHCP requires a reachable DHCP server.
The example credentials and 1024-bit key are for the legacy lab only.

Check the router:

```text
show ip interface brief
show ip ssh
```

## Run on the Ubuntu Lab Computer

Requirements:

- Docker Engine and Docker Compose plugin
- Router configured for SSH
- Network connectivity from Ubuntu and the container to router TCP port 22

Download or clone the repository into the Ubuntu `python` folder.
Open a terminal in the repository folder containing `docker-compose.yml`.

Start the application:

```bash
docker compose up -d
```

### Open the Website

On the Ubuntu computer running Docker:

```text
http://localhost:5000
```

From another computer with network access to the Ubuntu computer:

```text
http://<UBUNTU_HOST_IP>:5000
```

The Ubuntu firewall must allow TCP port 5000 for remote access.

The browser URL uses the Ubuntu host IP.
The Router IP Address input uses the Cisco router IP.

### Example Commands

```text
show ip interface brief
show version
show running-config
```

Enter one command and click Execute.

## Lab Credentials

Default username: `admin`

Default password: `cisco`

These match the example router configuration.

To use different credentials, create a local `.env` file beside
`docker-compose.yml`:

```text
ROUTER_USER=admin
ROUTER_PASSWORD=cisco
```

Do not commit real credentials.

## Docker Commands

Check container status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs --tail=100
```

Rebuild after code changes:

```bash
docker compose up -d --build
```

Stop and remove this project's containers and network:

```bash
docker compose down
```

## Ubuntu Terminal SSH Compatibility

For manual OpenSSH connections to the legacy router, the lab may
require these settings in the connecting user's `~/.ssh/config`.
For the root user, that path is `/root/.ssh/config`.

```text
Host 192.168.138.*
    KexAlgorithms +diffie-hellman-group14-sha1,diffie-hellman-group1-sha1
    HostKeyAlgorithms +ssh-rsa
    Ciphers +aes128-cbc,3des-cbc
```

These settings apply to the OpenSSH command-line client.
Paramiko does not automatically read or apply them.
Paramiko compatibility depends on the algorithms supported by the
router and the installed library.

## Scope

- Intended for an isolated classroom lab, not a public web service.
- Accepts unknown SSH host keys for the lab demonstration.
- Runs one single-line command per request.
- Each request creates a new SSH session.
- Configuration mode does not persist between button clicks.
- Interactive commands requiring additional input are not supported.
- Commands that change the hostname or disconnect SSH may time out.

## Verification Status

Live execution against the university lab router has not yet been
verified.
