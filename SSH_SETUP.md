# SSH Setup Guide

Quick guide for setting up SSH access to your remote server.

## Current Situation

You have password access to `prabalshrestha@eng402924`. The sync scripts will now prompt you for the password when needed.

## Two Options

### Option 1: Use Password (Current - Works Now)

**What happens**: You'll be prompted for your password during sync.

**Usage**:
```bash
./quick_sync.sh
# Enter password when prompted
```

**Pros**: 
- Works immediately
- No setup needed

**Cons**:
- Must enter password each time
- Slower

### Option 2: Set Up SSH Keys (Recommended)

**What happens**: Password-less authentication using SSH keys.

**Setup** (One-time, ~2 minutes):

```bash
# 1. Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to accept defaults
# Optionally set a passphrase (or leave empty for no passphrase)

# 2. Copy your public key to the server
ssh-copy-id prabalshrestha@eng402924
# Enter your password when prompted (last time!)

# 3. Test the connection
ssh prabalshrestha@eng402924
# Should connect without password!
```

**Pros**:
- No password prompts
- Faster syncing
- More secure
- Industry standard

**Cons**:
- Requires one-time setup

## Detailed SSH Key Setup

### Step 1: Check if You Already Have SSH Keys

```bash
ls -la ~/.ssh/
```

If you see `id_ed25519` or `id_rsa`, you already have keys! Skip to Step 3.

### Step 2: Generate SSH Keys (If Needed)

```bash
# Generate new key pair
ssh-keygen -t ed25519 -C "prabalshrestha@eng402924"

# You'll see:
# Generating public/private ed25519 key pair.
# Enter file in which to save the key (/Users/your_username/.ssh/id_ed25519):
# → Press ENTER to accept default

# Enter passphrase (empty for no passphrase):
# → Press ENTER for no passphrase (easier)
# → Or enter a passphrase for extra security

# Your identification has been saved in /Users/your_username/.ssh/id_ed25519
# Your public key has been saved in /Users/your_username/.ssh/id_ed25519.pub
```

### Step 3: Copy Public Key to Server

```bash
# Copy your public key to the server
ssh-copy-id prabalshrestha@eng402924

# You'll see:
# /usr/bin/ssh-copy-id: INFO: attempting to log in with the new key(s)...
# prabalshrestha@eng402924's password:
# → ENTER YOUR PASSWORD (this is the last time!)

# Number of key(s) added: 1
# Now try logging into the machine with:
#   "ssh 'prabalshrestha@eng402924'"
```

**If `ssh-copy-id` is not available** (macOS sometimes):

```bash
# Manual method
cat ~/.ssh/id_ed25519.pub | ssh prabalshrestha@eng402924 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
# Enter password when prompted
```

### Step 4: Test Connection

```bash
# Test SSH connection
ssh prabalshrestha@eng402924

# Should connect WITHOUT password prompt!
# If it works, you're done! 🎉

# Exit the server
exit
```

### Step 5: Use Sync Scripts (No Password Needed)

```bash
# Now sync without password prompts
./quick_sync.sh

# Or full sync
./quick_sync.sh --all

# No password needed! 🚀
```

## Troubleshooting

### "Permission denied (publickey)"

Your key wasn't copied correctly. Try:

```bash
# Check if your key is in ssh-agent
ssh-add -l

# If not, add it
ssh-add ~/.ssh/id_ed25519

# Try connecting again
ssh prabalshrestha@eng402924
```

### Still Asking for Password

```bash
# Check if authorized_keys exists on server
ssh prabalshrestha@eng402924 "ls -la ~/.ssh/authorized_keys"

# Check permissions (should be 600)
ssh prabalshrestha@eng402924 "chmod 600 ~/.ssh/authorized_keys"

# Try again
ssh prabalshrestha@eng402924
```

### "Could not open a connection to your authentication agent"

```bash
# Start ssh-agent
eval "$(ssh-agent -s)"

# Add your key
ssh-add ~/.ssh/id_ed25519

# Try again
ssh prabalshrestha@eng402924
```

## Security Best Practices

### ✅ DO:
- Use SSH keys instead of passwords
- Set a passphrase on your SSH key for extra security
- Keep your private key (`id_ed25519`) secure
- Use `ssh-agent` to avoid entering passphrase repeatedly

### ❌ DON'T:
- Store passwords in scripts or environment variables
- Share your private key (`id_ed25519`)
- Use weak passwords
- Skip setting up SSH keys (it's worth the 2 minutes!)

## SSH Config (Optional - Advanced)

Make connecting even easier with SSH config:

```bash
# Edit SSH config
nano ~/.ssh/config

# Add this:
Host eng402924
    HostName eng402924
    User prabalshrestha
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Save and exit (Ctrl+X, Y, Enter)
```

Now you can use just:
```bash
ssh eng402924  # Instead of ssh prabalshrestha@eng402924
```

## Quick Reference

```bash
# Generate SSH key (one-time)
ssh-keygen -t ed25519

# Copy to server (one-time)
ssh-copy-id prabalshrestha@eng402924

# Test connection
ssh prabalshrestha@eng402924

# Use sync scripts (no password!)
./quick_sync.sh
./quick_sync.sh --all
```

## Current Sync Workflow

### With Password (Works Now)
```bash
./quick_sync.sh
# Enter password when prompted
```

### After SSH Key Setup (Recommended)
```bash
./quick_sync.sh
# No password prompt - just works! 🎉
```

## Next Steps

1. **For now**: Use `./quick_sync.sh` and enter password when prompted
2. **Recommended**: Set up SSH keys (5 minutes) for password-less access
3. **After setup**: Enjoy fast, secure, password-less syncing

## Help

If you're having trouble:

1. Test basic SSH: `ssh prabalshrestha@eng402924`
2. Check if server is reachable: `ping eng402924`
3. Verify username is correct: `prabalshrestha`
4. Follow SSH key setup steps above

---

**Bottom line**: The scripts work with passwords now. Set up SSH keys when you have 5 minutes for a better experience!

