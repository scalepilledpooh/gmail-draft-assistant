# Gmail Draft Assistant

An intelligent email management tool that automatically processes your Gmail inbox, filters relevant emails, and generates AI-powered reply drafts.

## Features

- 🤖 **AI-Powered Email Processing** - Uses local LMStudio for intelligent email filtering and response generation
- 📧 **Smart Email Classification** - Automatically identifies which emails are relevant and need responses
- ✍️ **Draft Generation** - Creates personalized reply drafts using AI or fallback templates
- 🗂️ **Auto-Archiving** - Archives non-relevant emails to keep your inbox clean
- 🔒 **Privacy-First** - Runs entirely on your local machine with your own AI models
- ⚙️ **Fully Customizable** - Easy configuration for personal details and preferences

## Setup

### 1. Install Dependencies

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib openai
```

### 2. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API
4. Create OAuth2 credentials (Desktop application)
5. Download the credentials and save as `credentials.json`

### 3. Personal Configuration

```bash
cp config_example.py config.py
```

Edit `config.py` with your personal details:
- Replace `"Your Full Name"` with your actual name
- Replace `"Your Phone Number"` with your phone number
- Customize filtering criteria and prompts as needed

### 4. Set Up LMStudio (Optional but Recommended)

Install [LMStudio](https://lmstudio.ai/) and load a model like `gemma-3n-e4b`:

```bash
# Start LMStudio server
lm-cli serve --model-path ~/.lmstudio/models/lmstudio-community/gemma-3n-E4B-it-text-GGUF/gemma-3n-E4B-it-Q4_K_M.gguf --api --host 127.0.0.1 --port 1234
```

## Usage

### Basic Usage
```bash
python3 gmail_drafts.py --days 1 --max 10
```

### With AI Features
```bash
python3 gmail_drafts.py --days 1 --max 10 --auto-draft --archive
```

### Command Line Options

- `--credentials` - Path to OAuth2 credentials JSON file (default: credentials.json)
- `--token` - Path to OAuth2 token file (default: token.json)
- `--days` - Look back this many days (default: 1)
- `--max` - Maximum messages to process (default: 5)
- `--lm-url` - LMStudio API URL (default: http://localhost:1234/v1)
- `--lm-model` - Model name to use (default: google/gemma-3n-e4b)
- `--auto-draft` - Automatically create drafts for emails needing responses
- `--archive` - Archive non-relevant emails
- `--no-filter` - Disable AI filtering and process all emails

## How It Works

1. **Fetches Recent Emails** - Retrieves emails from your Gmail inbox within the specified timeframe
2. **Relevance Classification** - Uses AI to determine which emails are important to you
3. **Response Analysis** - Identifies emails that require a response
4. **Draft Generation** - Creates personalized reply drafts using AI or templates
5. **Smart Organization** - Archives irrelevant emails and keeps important ones in inbox

## Privacy & Security

- All processing happens locally on your machine
- No data is sent to external services (except Gmail API for email access)
- Uses your own local AI models via LMStudio
- OAuth2 authentication with Google for secure Gmail access

## Automation

For daily email management, you can set up a cron job:

```bash
# Add to crontab for daily 9 AM execution
0 9 * * * /usr/bin/python3 /path/to/gmail_drafts.py --auto-draft --archive --days 1
```

## Contributing

Feel free to submit issues and pull requests to improve the functionality!

## License

MIT License - feel free to use and modify as needed.