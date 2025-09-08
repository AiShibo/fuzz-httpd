# Build Fix Documentation

## Issue
The make build was failing with the error:
```
cc: error: no such file or directory: '/usr/local/lib/libcrypto.a'
```

## Root Cause
The Makefiles were configured to link against LibreSSL libraries in `/usr/local/lib/`, but the system has a mixed SSL library setup:
- System OpenSSL libraries (`libssl.a`, `libcrypto.a`) are located in `/usr/lib/`
- LibreSSL's `libtls.a` is available in `/usr/local/lib/` from the `libressl-libtls-4.1.0` package

## Changes Made

### 1. htpasswd Makefile (`src/usr.bin/htpasswd/Makefile`)
**Line 13:** Changed library path for libcrypto
```diff
- LDADD=		/usr/local/lib/libcrypto.a
+ LDADD=		/usr/lib/libcrypto.a
```

### 2. httpd Makefile (`src/usr.sbin/httpd/Makefile`)
**Lines 22-23:** Updated SSL library paths
```diff
  LDADD+= 	/usr/local/lib/libtls.a \
- 		/usr/local/lib/libssl.a \
- 		/usr/local/lib/libcrypto.a
+ 		/usr/lib/libssl.a \
+ 		/usr/lib/libcrypto.a
```

## Why This Works
- `libtls.a` remains in `/usr/local/lib/` (from LibreSSL package)
- `libssl.a` and `libcrypto.a` use the system OpenSSL libraries in `/usr/lib/`
- This mixed approach allows the build to find all required libraries without needing to install the full LibreSSL suite

## Verification
After making these changes, the build completes successfully with all tests passing.

# httpd Runtime Setup

## Prerequisites for Running httpd

After building httpd successfully, several setup steps are required to run the server:

### 1. Create Required Directories
```bash
# Create chroot directory and subdirectories
sudo mkdir -p /var/www/htdocs
sudo mkdir -p /var/www/acme
sudo mkdir -p /var/www/logs

# Create SSL certificate directories
sudo mkdir -p /etc/ssl/private
```

### 2. Generate SSL Certificates
For the example configuration that uses TLS, you need SSL certificates:
```bash
# Generate self-signed certificate for testing
sudo openssl req -x509 -newkey rsa:2048 \
    -keyout /etc/ssl/private/example.com.key \
    -out /etc/ssl/example.com.fullchain.pem \
    -days 365 -nodes \
    -subj "/C=US/ST=Test/L=Test/O=Test/CN=example.com"
```

### 3. Create Test Content
```bash
# Create a simple test page
echo "<h1>Test Page</h1>" | sudo tee /var/www/htdocs/index.html
```

### 4. Configuration Options

**Option A: Use the example config with SSL**
```bash
./httpd -d -f /home/share/httpd/src/etc/examples/httpd.conf
```
- Listens on port 80 (redirects to HTTPS) and port 443 (TLS)
- Requires SSL certificates (created in step 2)

**Option B: Use a minimal test config without SSL**
Create a simple config file:
```bash
# Minimal test configuration
chroot "/var/www"
access log off

server "localhost" {
    listen on * port 8080
    root "/htdocs"
    location * {
        directory auto index
    }
}
```

### 5. Running the Server
```bash
# Start httpd (requires root for chroot and binding to ports <1024)
sudo ./httpd -d -f <config-file>
```

### 6. Testing
```bash
# Test HTTP (example config)
curl -v http://localhost

# Test HTTPS (example config, ignore cert warnings)
curl -k -v https://localhost

# Test simple config
curl -v http://localhost:8080
```

## Common Issues
- **Permission errors**: httpd needs to run as root to chroot and bind to ports 80/443
- **Missing directories**: All chroot directories must exist before starting
- **SSL certificate errors**: Verify certificates exist at the paths specified in config
- **Port conflicts**: Make sure no other services are using the configured ports