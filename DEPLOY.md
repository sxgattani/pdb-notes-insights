# Deploying Notes HQ to Fly.io

## Prerequisites

1. Install the Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Login to Fly: `fly auth login`

## First-Time Deployment

### 1. Create the app and volume

```bash
# Create the app (choose a unique name if notes-hq is taken)
fly apps create notes-hq

# Create a persistent volume for the database (1GB is plenty for SQLite)
fly volumes create notes_hq_data --size 1 --region sjc
```

### 2. Set secrets (environment variables)

```bash
# Required: ProductBoard API token
fly secrets set PRODUCTBOARD_API_TOKEN="your-token-here"

# Required: App login credentials (change these!)
fly secrets set AUTH_USERNAME="admin"
fly secrets set AUTH_PASSWORD="your-secure-password"

# Required: Session secret (generate a random string)
fly secrets set SESSION_SECRET="$(openssl rand -hex 32)"

# Optional: ProductBoard API URL (defaults to https://api.productboard.com)
fly secrets set PRODUCTBOARD_API_URL="https://api.productboard.com"
```

### 3. Deploy

```bash
fly deploy
```

### 4. Upload existing database (optional)

If you have an existing database to upload:

```bash
# SSH into the running machine
fly ssh console

# The data directory is at /data
# Exit the console, then use sftp to upload:
fly ssh sftp shell
put backend/pdb_insights.db /data/pdb_insights.db
```

Or trigger a sync from the app UI after deployment.

## Subsequent Deployments

Just run:

```bash
fly deploy
```

Your database on the persistent volume will be preserved.

## Useful Commands

```bash
# View logs
fly logs

# SSH into the machine
fly ssh console

# Check app status
fly status

# Open the app in browser
fly open
```

## Configuration

Edit `fly.toml` to change:
- `app`: App name
- `primary_region`: Deploy region (sjc = San Jose, see `fly platform regions`)
- `vm.size`: Machine size
- `vm.memory`: Memory allocation

## Costs

With the default configuration:
- Shared CPU, 512MB RAM
- 1GB persistent volume
- Estimated: ~$5-10/month (check fly.io pricing)
